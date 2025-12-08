"""
Formatting utilities for dashboard display
"""


def format_price(price: float) -> str:
    """
    Format price with appropriate decimals and comma separators

    Args:
        price: Price value

    Returns:
        Formatted price string
    """
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    else:
        return f"${price:.8f}"


def format_large_number(num: float, suffix: str = "") -> str:
    """
    Format large numbers with K, M, B suffixes

    Args:
        num: Number to format
        suffix: Additional suffix (e.g., 'B' for billion)

    Returns:
        Formatted string
    """
    if num >= 1e9:
        return f"${num / 1e9:.2f}B{suffix}"
    elif num >= 1e6:
        return f"${num / 1e6:.2f}M{suffix}"
    elif num >= 1e3:
        return f"${num / 1e3:.2f}K{suffix}"
    else:
        return f"${num:.2f}{suffix}"


def format_percentage(pct: float, include_sign: bool = True) -> str:
    """
    Format percentage with sign and color coding

    Args:
        pct: Percentage value
        include_sign: Whether to include +/- sign

    Returns:
        Formatted percentage string
    """
    if include_sign:
        if pct > 0:
            return f"+{pct:.2f}%"
        else:
            return f"{pct:.2f}%"
    else:
        return f"{pct:.2f}%"


def get_trend_emoji(change_pct: float) -> str:
    """
    Get emoji based on price trend

    Args:
        change_pct: Percentage change

    Returns:
        Emoji string
    """
    if change_pct > 5:
        return "🚀"
    elif change_pct > 0:
        return "📈"
    elif change_pct < -5:
        return "💥"
    elif change_pct < 0:
        return "📉"
    else:
        return "➡️"


def get_trend_color(change_pct: float) -> str:
    """
    Get color for trend display

    Args:
        change_pct: Percentage change

    Returns:
        Color string (for Streamlit styling)
    """
    if change_pct > 0:
        return "green"
    elif change_pct < 0:
        return "red"
    else:
        return "gray"