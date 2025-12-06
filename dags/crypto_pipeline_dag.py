"""
DAG: Crypto Price Monitoring Pipeline
======================================

Mục đích:
    - Thu thập giá crypto từ CoinGecko API theo định kỳ
    - Lưu trữ vào PostgreSQL database
    - Phân tích và gửi cảnh báo qua Telegram khi có biến động lớn

Schedule: Mỗi 4 giờ (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)

Flow:
    Setup DB → Extract → Validate → Transform → Load → Analyze → Branch
                                                                    ↓
                                                    Alert Notification (nếu có alert)
                                                    Summary Notification (nếu không có alert)
                                                                    ↓
                                                            Pipeline Complete
"""

from airflow.decorators import dag, task
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta
from typing import List, Dict
import sys

# ============================================================================
# IMPORT HELPER FUNCTIONS
# ============================================================================
# Thêm include folder vào Python path để import được helper modules
sys.path.insert(0, '/usr/local/airflow/include')

from db_utils import create_table, insert_crypto_data
from api_utils import (
    fetch_crypto_prices,
    validate_crypto_data,
    transform_crypto_data,
    analyze_for_alerts
)
from notification_utils import (
    send_telegram_message,
    format_crypto_summary,
    format_alert_message
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default arguments áp dụng cho TẤT CẢ tasks trong DAG
default_args = {
    'owner': 'airflow',  # Owner của DAG (hiển thị trong UI)
    'depends_on_past': False,  # Task không phụ thuộc vào run trước đó
    'email_on_failure': False,  # Không gửi email khi fail
    'email_on_retry': False,  # Không gửi email khi retry
    'retries': 3,  # Số lần retry khi task fail
    'retry_delay': timedelta(minutes=2),  # Đợi 2 phút giữa mỗi lần retry
    'execution_timeout': timedelta(minutes=10),  # Timeout task sau 10 phút
}

# Danh sách crypto coins cần theo dõi (theo CoinGecko ID)
COIN_IDS = ['bitcoin', 'ethereum', 'binancecoin', 'cardano', 'solana', 'ripple', 'polkadot', 'dogecoin', 'shiba-inu', 'avalanche-2', 'terra-luna', 'litecoin']

# Ngưỡng % thay đổi giá để trigger alert
ALERT_THRESHOLD = 5.0  # Cảnh báo nếu giá thay đổi > ±5% trong 24h


# ============================================================================
# DAG DEFINITION
# ============================================================================

@dag(
    dag_id='crypto_price_pipeline',
    default_args=default_args,
    description='Pipeline to fetch crypto prices and send Telegram notifications',
    schedule='0 */4 * * *',  # Cron: chạy mỗi 4 giờ vào phút 0
    start_date=datetime(2024, 12, 1),  # Ngày bắt đầu (có thể backfill từ đây)
    catchup=False,  # Không tự động backfill khi enable DAG
    tags=['crypto', 'telegram', 'monitoring'],  # Tags để filter trong UI
    max_active_runs=1,  # Chỉ cho phép 1 DAG run cùng lúc
)
def crypto_price_pipeline():
    """
    Main DAG function sử dụng TaskFlow API

    TaskFlow API benefits:
        - Code gọn gàng hơn, ít boilerplate
        - Tự động handle XCom (truyền data giữa tasks)
        - Type hints để IDE autocomplete tốt hơn
    """

    # ========================================================================
    # TASK 1: SETUP DATABASE
    # ========================================================================
    @task(
        task_id='setup_database',
        retries=1,  # Ít retry vì DB setup thường không fail
    )
    def setup_database_task():
        """
        Tạo table trong PostgreSQL nếu chưa tồn tại

        Returns:
            str: Status message

        Notes:
            - Idempotent: Chạy nhiều lần không gây lỗi
            - Sử dụng CREATE TABLE IF NOT EXISTS
        """
        print("🔧 Setting up database...")
        create_table()
        return "Database ready"

    # ========================================================================
    # TASK 2: EXTRACT DATA
    # ========================================================================
    @task(
        task_id='extract_crypto_data',
        retries=3,  # Nhiều retry vì API có thể unstable
        retry_delay=timedelta(minutes=1),  # Retry nhanh hơn default
    )
    def extract_data_task():
        """
        Lấy dữ liệu giá crypto từ CoinGecko API

        Returns:
            List[Dict]: Raw data từ API

        Raises:
            ValueError: Nếu API không trả về data
            requests.exceptions.RequestException: Nếu API call fail

        Notes:
            - CoinGecko free API có rate limit: ~10-30 calls/phút
            - Timeout 30s để tránh task bị hang
        """
        print(f"📡 Extracting crypto data for: {', '.join(COIN_IDS)}")
        data = fetch_crypto_prices(coin_ids=COIN_IDS, timeout=30)

        # Validate có data trước khi return
        if not data:
            raise ValueError("No data returned from API")

        print(f"✅ Successfully extracted {len(data)} coins")
        return data

    # ========================================================================
    # TASK 3: VALIDATE DATA
    # ========================================================================
    @task(
        task_id='validate_data',
        retries=0,  # Không retry vì data sai thì retry cũng vô ích
    )
    def validate_data_task(crypto_data: List[Dict]):
        """
        Kiểm tra chất lượng data (Data Quality Check)

        Args:
            crypto_data: Raw data từ extract task (auto pull từ XCom)

        Returns:
            List[Dict]: Validated data (pass-through)

        Raises:
            ValueError: Nếu data không hợp lệ (missing fields, invalid values)

        Notes:
            - Fail fast: Stop pipeline ngay nếu data lỗi
            - Không retry vì retry sẽ lấy lại data lỗi như cũ
        """
        print("🔍 Validating crypto data...")

        is_valid = validate_crypto_data(crypto_data)

        if not is_valid:
            raise ValueError("Data validation failed - stopping pipeline")

        print("✅ Data validation passed")
        return crypto_data

    # ========================================================================
    # TASK 4: TRANSFORM DATA
    # ========================================================================
    @task(
        task_id='transform_data',
    )
    def transform_data_task(crypto_data: List[Dict]):
        """
        Transform và clean data

        Args:
            crypto_data: Validated data từ previous task

        Returns:
            List[Dict]: Transformed data ready cho database

        Transformations:
            - Parse ISO datetime string → datetime object
            - Handle None/null values (set defaults)
            - Extract only necessary fields
        """
        print("⚙️ Transforming crypto data...")
        transformed_data = transform_crypto_data(crypto_data)
        print(f"✅ Transformed {len(transformed_data)} records")
        return transformed_data

    # ========================================================================
    # TASK 5: LOAD TO DATABASE
    # ========================================================================
    @task(
        task_id='load_to_database',
    )
    def load_data_task(transformed_data: List[Dict], **context):
        """
        Insert/Update data vào PostgreSQL

        Args:
            transformed_data: Cleaned data từ transform task
            **context: Airflow context variables

        Returns:
            str: Status message

        Notes:
            - Sử dụng execution_date (logical_date) làm partition key
            - ON CONFLICT DO UPDATE: Idempotent, không duplicate khi backfill
            - execution_date vs current time:
                * execution_date: Thời gian logic (dùng cho business logic)
                * current time: Thời gian thực tế chạy task
        """
        # Lấy logical_date từ context (Airflow 3.x đổi tên từ execution_date)
        execution_date = context['logical_date']

        print(f"💾 Loading data to database...")
        print(f"   Execution date: {execution_date}")

        insert_crypto_data(transformed_data, execution_date)

        return f"Loaded {len(transformed_data)} records"

    # ========================================================================
    # TASK 6: ANALYZE FOR ALERTS
    # ========================================================================
    @task(
        task_id='analyze_for_alerts',
    )
    def analyze_task(transformed_data: List[Dict]):
        """
        Phân tích data để xác định có cần gửi alert không

        Args:
            transformed_data: Data từ transform task

        Returns:
            Dict: {
                'has_alert': bool,
                'alert_data': Dict hoặc None,
                'summary_data': List[Dict]
            }

        Logic:
            - Check price_change_percentage_24h của mỗi coin
            - Nếu |change| >= ALERT_THRESHOLD → có alert
            - Sort alerts theo độ lớn của % change
        """
        print(f"📊 Analyzing data (threshold: ±{ALERT_THRESHOLD}%)...")

        alert_info = analyze_for_alerts(transformed_data, threshold=ALERT_THRESHOLD)

        result = {
            'has_alert': alert_info is not None,
            'alert_data': alert_info,
            'summary_data': transformed_data
        }

        if result['has_alert']:
            print(f"⚠️ Alert detected: {len(alert_info['alerts'])} coin(s) exceed threshold")
        else:
            print("ℹ️ No alerts detected")

        return result

    # ========================================================================
    # TASK 7: BRANCHING LOGIC
    # ========================================================================
    @task.branch(
        task_id='check_alert_condition',
    )
    def branch_on_alert(analysis_result: Dict):
        """
        Conditional branching: Quyết định gửi alert hay summary

        Args:
            analysis_result: Result từ analyze task

        Returns:
            str: Task ID để execute tiếp
                - 'send_alert_notification' nếu có alert
                - 'send_summary_notification' nếu không có alert

        Notes:
            - @task.branch: Special task decorator cho conditional logic
            - Tasks không được chọn sẽ có state "skipped"
            - Phải return task_id dạng string, không phải task object
        """
        has_alert = analysis_result['has_alert']

        if has_alert:
            print("⚠️ Alert condition met → routing to alert notification")
            return 'send_alert_notification'
        else:
            print("ℹ️ No alert → routing to summary notification")
            return 'send_summary_notification'

    # ========================================================================
    # TASK 8A: SEND ALERT NOTIFICATION
    # ========================================================================
    @task(
        task_id='send_alert_notification',
    )
    def send_alert_task(analysis_result: Dict, **context):
        """
        Gửi alert notification qua Telegram (khi có biến động lớn)

        Args:
            analysis_result: Data từ analyze task
            **context: Airflow context

        Returns:
            str: Status message

        Raises:
            Exception: Nếu gửi Telegram message fail

        Notes:
            - Task này chỉ chạy khi branch chọn nó (có alert)
            - Format message với thông tin chi tiết về alert
            - Include: coin, price, % change, direction
        """
        execution_date = context['logical_date']
        alert_data = analysis_result['alert_data']

        print("📤 Sending alert notification to Telegram...")

        # Format message với alert details
        message = format_alert_message(alert_data, execution_date)

        # Gửi qua Telegram
        success = send_telegram_message(message)

        if not success:
            raise Exception("Failed to send Telegram alert - check credentials")

        print("✅ Alert notification sent successfully")
        return "Alert sent"

    # ========================================================================
    # TASK 8B: SEND SUMMARY NOTIFICATION
    # ========================================================================
    @task(
        task_id='send_summary_notification',
    )
    def send_summary_task(analysis_result: Dict, **context):
        """
        Gửi summary notification qua Telegram (khi không có alert)

        Args:
            analysis_result: Data từ analyze task
            **context: Airflow context

        Returns:
            str: Status message

        Raises:
            Exception: Nếu gửi Telegram message fail

        Notes:
            - Task này chỉ chạy khi branch chọn nó (không có alert)
            - Format message với thông tin tổng hợp về tất cả coins
            - Include: prices, % changes, total volume
        """
        execution_date = context['logical_date']
        summary_data = analysis_result['summary_data']

        print("📤 Sending summary notification to Telegram...")

        # Format message với summary
        message = format_crypto_summary(summary_data, execution_date)

        # Gửi qua Telegram
        success = send_telegram_message(message)

        if not success:
            raise Exception("Failed to send Telegram summary - check credentials")

        print("✅ Summary notification sent successfully")
        return "Summary sent"

    # ========================================================================
    # TASK 9: END TASK (MERGE BRANCHES)
    # ========================================================================
    # EmptyOperator: Không làm gì, chỉ để merge branches
    end_task = EmptyOperator(
        task_id='pipeline_complete',
        trigger_rule='none_failed_min_one_success'
        # Trigger rule giải thích:
        #   - none_failed: Không có upstream task nào failed
        #   - min_one_success: Ít nhất 1 upstream task success
        #   - Kết hợp: Chạy nếu (alert HOẶC summary) success VÀ không có task failed
    )

    # ========================================================================
    # DEFINE TASK DEPENDENCIES (DAG FLOW)
    # ========================================================================

    # Instantiate all tasks
    db_setup = setup_database_task()
    extracted = extract_data_task()
    validated = validate_data_task(extracted)
    transformed = transform_data_task(validated)
    loaded = load_data_task(transformed)
    analyzed = analyze_task(transformed)
    branch = branch_on_alert(analyzed)
    alert = send_alert_task(analyzed)
    summary = send_summary_task(analyzed)

    # Define dependency chain
    # Giải thích >> operator:
    #   - task1 >> task2: task2 chạy SAU task1
    #   - task1 >> [task2, task3]: task2 và task3 chạy song song SAU task1

    # Linear chain: setup → extract → validate → transform → load
    db_setup >> extracted >> validated >> transformed >> loaded

    # Parallel: load và analyze có thể chạy song song (nhưng analyzed depends on transformed)
    loaded >> analyzed

    # Branching: branch → (alert HOẶC summary) → end
    analyzed >> branch
    branch >> [alert, summary]  # Parallel outputs (nhưng chỉ 1 trong 2 chạy)
    [alert, summary] >> end_task  # Cả 2 đều dẫn đến end

crypto_dag = crypto_price_pipeline()