import requests
from datetime import datetime
from typing import List, Dict, Optional

# CoinGecko API configuration
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"


# Rate limit: 10-30 calls/minute (free tier)
# Giải thích: Free API có giới hạn, cần xử lý retry và timeout

def fetch_crypto_prices(coin_ids: List[str] = None, timeout: int = 30) -> List[Dict]:
    """
    Lấy giá crypto từ CoinGecko API

    Args:
        coin_ids: List các coin IDs (mặc định: bitcoin, ethereum, binancecoin)
        timeout: Timeout cho request (seconds)

    Returns:
        List of dicts chứa crypto data

    Raises:
        requests.exceptions.RequestException: Nếu API call fail

    Giải thích:
        - vs_currency=usd: Giá theo USD
        - order=market_cap_desc: Sắp xếp theo market cap
        - price_change_percentage=24h: Lấy % thay đổi 24h
        - sparkline=false: Không cần chart data (tiết kiệm bandwidth)
    """
    if coin_ids is None:
        coin_ids = ['bitcoin', 'ethereum', 'binancecoin']

    endpoint = f"{COINGECKO_BASE_URL}/coins/markets"

    params = {
        'vs_currency': 'usd',
        'ids': ','.join(coin_ids),
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': False,
        'price_change_percentage': '24h'
    }

    print(f"🔍 Fetching data for: {', '.join(coin_ids)}")

    try:
        response = requests.get(
            endpoint,
            params=params,
            timeout=timeout,
            headers={'Accept': 'application/json'}
        )

        # Raise exception nếu status code không phải 2xx
        response.raise_for_status()

        data = response.json()

        print(f"✅ Fetched {len(data)} coins successfully")
        return data

    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout after {timeout}s")
        raise
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {str(e)}")
        raise


def validate_crypto_data(data: List[Dict]) -> bool:
    """
    Validate dữ liệu từ API

    Args:
        data: List of crypto data dicts

    Returns:
        True nếu data hợp lệ, False nếu không

    Giải thích:
        Kiểm tra các điều kiện cần thiết:
        - Data không rỗng
        - Mỗi record có đủ required fields
        - Giá phải > 0 (reasonable check)
    """
    if not data:
        print("❌ Validation failed: Empty data")
        return False

    required_fields = ['id', 'symbol', 'current_price', 'last_updated']

    for item in data:
        # Check required fields
        missing_fields = [field for field in required_fields if field not in item]
        if missing_fields:
            print(f"❌ Validation failed: Missing fields {missing_fields} in {item.get('id', 'unknown')}")
            return False

        # Check price > 0
        if item['current_price'] is None or item['current_price'] <= 0:
            print(f"❌ Validation failed: Invalid price for {item['id']}: {item['current_price']}")
            return False

    print(f"✅ Validation passed for {len(data)} records")
    return True


def transform_crypto_data(data: List[Dict]) -> List[Dict]:
    """
    Transform và clean data từ API

    Args:
        data: Raw data từ CoinGecko

    Returns:
        Cleaned và transformed data

    Giải thích:
        - Parse ISO timestamp thành datetime object
        - Xử lý None values (set default = 0)
        - Chỉ giữ lại fields cần thiết
    """
    transformed = []

    for item in data:
        transformed_item = {
            'id': item['id'],
            'symbol': item['symbol'],
            'current_price': item['current_price'],
            'market_cap': item.get('market_cap', 0),
            'total_volume': item.get('total_volume', 0),
            'price_change_24h': item.get('price_change_24h', 0),
            'price_change_percentage_24h': item.get('price_change_percentage_24h', 0),
            # Parse ISO 8601 timestamp
            'last_updated': datetime.fromisoformat(
                item['last_updated'].replace('Z', '+00:00')
            )
        }
        transformed.append(transformed_item)

    print(f"✅ Transformed {len(transformed)} records")
    return transformed


def analyze_for_alerts(data: List[Dict], threshold: float = 5.0) -> Optional[Dict]:
    """
    Phân tích data để tạo alerts

    Args:
        data: List of crypto data
        threshold: % thay đổi để trigger alert (mặc định 5%)

    Returns:
        Dict chứa alert info nếu có, None nếu không

    Giải thích:
        - Tìm coin có % thay đổi vượt ngưỡng
        - Ưu tiên coin có % thay đổi cao nhất (abs value)
    """
    alerts = []

    for item in data:
        change_pct = item.get('price_change_percentage_24h', 0)

        if abs(change_pct) >= threshold:
            alerts.append({
                'coin_id': item['id'],
                'symbol': item['symbol'].upper(),
                'price': item['current_price'],
                'change_pct': change_pct,
                'direction': '📈' if change_pct > 0 else '📉'
            })

    if not alerts:
        print(f"ℹ️ No alerts (threshold: ±{threshold}%)")
        return None

    # Sort by absolute change percentage (descending)
    alerts.sort(key=lambda x: abs(x['change_pct']), reverse=True)

    print(f"⚠️ Found {len(alerts)} alert(s)")

    return {
        'has_alert': True,
        'alerts': alerts,
        'threshold': threshold
    }