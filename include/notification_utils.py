import os
import requests
from typing import Dict, List
from datetime import datetime


def send_telegram_message(message: str, parse_mode: str = 'Markdown') -> bool:
    """
    Gửi message qua Telegram Bot

    Args:
        message: Nội dung message (support Markdown hoặc HTML)
        parse_mode: 'Markdown' hoặc 'HTML'

    Returns:
        True nếu gửi thành công, False nếu fail

    Giải thích:
        - Lấy token và chat_id từ environment variables
        - Dùng sendMessage API của Telegram
        - parse_mode cho phép format text (bold, italic, code, etc.)
    """
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        print("❌ Missing Telegram credentials in environment variables")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': parse_mode
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        print("✅ Telegram message sent successfully")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send Telegram message: {str(e)}")
        return False


def format_crypto_summary(data: List[Dict], execution_date: datetime) -> str:
    """
    Format crypto data thành message đẹp

    Args:
        data: List of crypto data dicts
        execution_date: Thời gian execution

    Returns:
        Formatted message string với Markdown

    Giải thích:
        - Dùng emoji để message sinh động
        - Format số với dấu phẩy và 2 decimal places
        - Hiển thị trend với mũi tên
    """
    timestamp = execution_date.strftime('%d/%m/%Y %H:%M UTC')

    # Header
    message = f"🚀 *Crypto Price Update*\n"
    message += f"📅 _{timestamp}_\n\n"

    # Crypto prices
    for item in data:
        symbol = item['symbol'].upper()
        price = item['current_price']
        change_pct = item.get('price_change_percentage_24h', 0)

        # Emoji based on trend
        if change_pct > 0:
            trend_emoji = "📈"
            change_text = f"+{change_pct:.2f}%"
        elif change_pct < 0:
            trend_emoji = "📉"
            change_text = f"{change_pct:.2f}%"
        else:
            trend_emoji = "➡️"
            change_text = "0.00%"

        # Format price với dấu phẩy
        if price >= 1000:
            price_str = f"${price:,.2f}"
        else:
            price_str = f"${price:.4f}"

        message += f"{trend_emoji} *{symbol}*: {price_str} ({change_text})\n"

    # Footer
    total_volume = sum(item.get('total_volume', 0) for item in data)
    message += f"\n💰 _Total 24h Volume: ${total_volume / 1e9:.2f}B_"

    return message


def format_alert_message(alert_data: Dict, execution_date: datetime) -> str:
    """
    Format alert message với thông tin chi tiết

    Args:
        alert_data: Dict từ analyze_for_alerts()
        execution_date: Thời gian execution

    Returns:
        Formatted alert message

    Giải thích:
        - Highlight alerts với emoji nổi bật
        - Show threshold để user biết tiêu chí
        - List tất cả coins vượt ngưỡng
    """
    timestamp = execution_date.strftime('%d/%m/%Y %H:%M UTC')
    threshold = alert_data['threshold']
    alerts = alert_data['alerts']

    # Header với cảnh báo
    message = f"⚠️ *CRYPTO ALERT!*\n"
    message += f"📅 _{timestamp}_\n"
    message += f"🎯 _Threshold: ±{threshold}%_\n\n"

    # List alerts
    for alert in alerts:
        direction = alert['direction']
        symbol = alert['symbol']
        price = alert['price']
        change_pct = alert['change_pct']

        if price >= 1000:
            price_str = f"${price:,.2f}"
        else:
            price_str = f"${price:.4f}"

        message += f"{direction} *{symbol}*: {price_str}\n"
        message += f"   Change: *{change_pct:+.2f}%*\n\n"

    message += "💡 _Check the market for opportunities!_"

    return message