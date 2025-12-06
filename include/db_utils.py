import os
import psycopg2
from psycopg2.extras import execute_values
from contextlib import contextmanager

# Database connection parameters (từ Astro defaults)
DB_CONFIG = {
    'host': 'postgres',  # Tên container trong Docker network
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'postgres'
}


@contextmanager
def get_db_connection():
    """
    Context manager để tự động đóng connection
    Giải thích: Dùng 'with' để đảm bảo connection được đóng đúng cách
    """
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


def create_table():
    """
    Tạo table nếu chưa tồn tại
    Giải thích: Chạy lần đầu trong DAG để setup schema
    """
    sql_file = '/usr/local/airflow/include/sql/create_table.sql'

    with open(sql_file, 'r') as f:
        create_table_sql = f.read()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)

    print("✅ Table created successfully")


def insert_crypto_data(data_list, execution_date):
    """
    Insert multiple records vào database

    Args:
        data_list: List of dicts chứa crypto data
        execution_date: Timestamp từ Airflow context

    Giải thích:
        - Dùng execute_values() để insert nhiều rows cùng lúc (nhanh hơn)
        - ON CONFLICT DO UPDATE: Nếu record đã tồn tại (same execution_date + coin_id)
          thì UPDATE thay vì báo lỗi (đảm bảo idempotency)
    """
    if not data_list:
        print("⚠️ No data to insert")
        return

    insert_sql = """
        INSERT INTO crypto_prices (
            execution_date, coin_id, symbol, current_price,
            market_cap, total_volume, price_change_24h,
            price_change_percentage_24h, last_updated
        ) VALUES %s
        ON CONFLICT (execution_date, coin_id) 
        DO UPDATE SET
            current_price = EXCLUDED.current_price,
            market_cap = EXCLUDED.market_cap,
            total_volume = EXCLUDED.total_volume,
            price_change_24h = EXCLUDED.price_change_24h,
            price_change_percentage_24h = EXCLUDED.price_change_percentage_24h,
            last_updated = EXCLUDED.last_updated
    """

    # Prepare data tuples
    values = [
        (
            execution_date,
            item['id'],
            item['symbol'].upper(),
            item['current_price'],
            item.get('market_cap'),
            item.get('total_volume'),
            item.get('price_change_24h'),
            item.get('price_change_percentage_24h'),
            item['last_updated']
        )
        for item in data_list
    ]

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, insert_sql, values)

    print(f"✅ Inserted/Updated {len(data_list)} records")


def get_latest_prices(coin_ids=None):
    """
    Lấy giá mới nhất của các coins

    Args:
        coin_ids: List of coin IDs (optional), nếu None thì lấy tất cả

    Returns:
        List of dicts chứa thông tin giá
    """
    query = """
        SELECT DISTINCT ON (coin_id)
            coin_id, symbol, current_price, 
            price_change_percentage_24h, last_updated
        FROM crypto_prices
        WHERE 1=1
    """

    params = []
    if coin_ids:
        query += " AND coin_id = ANY(%s)"
        params.append(coin_ids)

    query += " ORDER BY coin_id, execution_date DESC"

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            results = [dict(zip(columns, row)) for row in cur.fetchall()]

    return results