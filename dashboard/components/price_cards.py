"""
Price display cards component
Shows current prices in card layout
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys

sys.path.append('..')
from utils.formatters import (
    format_price,
    format_percentage,
    get_trend_emoji,
    get_trend_color
)


def render_price_cards(df: pd.DataFrame):
    """
    Render price cards in grid layout

    Args:
        df: DataFrame with latest prices
    """
    if df.empty:
        st.warning("📊 No data available")
        return

    # Sort by market cap (descending)
    df = df.sort_values('market_cap', ascending=False)

    st.subheader("💰 Current Prices")

    # Display last update time
    if 'last_updated' in df.columns:
        last_update = pd.to_datetime(df['last_updated'].max())
        st.caption(f"Last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Create columns for cards (3 per row)
    cols_per_row = 3
    rows = len(df) // cols_per_row + (1 if len(df) % cols_per_row else 0)

    for row in range(rows):
        cols = st.columns(cols_per_row)

        for col_idx in range(cols_per_row):
            idx = row * cols_per_row + col_idx

            if idx >= len(df):
                break

            coin = df.iloc[idx]

            with cols[col_idx]:
                render_single_card(coin)


def render_single_card(coin: pd.Series):
    """
    Render a single price card

    Args:
        coin: Series with coin data
    """
    symbol = coin['symbol'].upper()
    price = coin['current_price']
    change_pct = coin.get('price_change_percentage_24h', 0)

    # Get styling
    emoji = get_trend_emoji(change_pct)
    color = get_trend_color(change_pct)

    # Create card with border and padding
    with st.container():
        # Header with symbol and emoji
        st.markdown(f"### {emoji} {symbol}")

        # Price (large text)
        st.markdown(f"<h2 style='margin:0'>{format_price(price)}</h2>",
                    unsafe_allow_html=True)

        # 24h change (colored)
        change_text = format_percentage(change_pct)
        st.markdown(
            f"<p style='color:{color}; font-size:18px; margin:0'>{change_text}</p>",
            unsafe_allow_html=True
        )

        # Additional info (smaller text)
        if 'market_cap' in coin and coin['market_cap']:
            from utils.formatters import format_large_number
            st.caption(f"Market Cap: {format_large_number(coin['market_cap'])}")

        # Divider
        st.divider()


def render_compact_table(df: pd.DataFrame):
    """
    Alternative: Render as compact table (for many coins)

    Args:
        df: DataFrame with latest prices
    """
    if df.empty:
        st.warning("📊 No data available")
        return

    st.subheader("💰 All Prices (Table View)")

    # Prepare display dataframe
    display_df = df.copy()

    # Format columns
    display_df['Price'] = display_df['current_price'].apply(format_price)
    display_df['24h Change'] = display_df['price_change_percentage_24h'].apply(
        lambda x: format_percentage(x)
    )
    display_df['Symbol'] = display_df['symbol'].str.upper()
    display_df['Trend'] = display_df['price_change_percentage_24h'].apply(
        get_trend_emoji
    )

    # Select columns to display
    display_cols = ['Trend', 'Symbol', 'Price', '24h Change']

    if 'market_cap' in display_df.columns:
        from utils.formatters import format_large_number
        display_df['Market Cap'] = display_df['market_cap'].apply(
            lambda x: format_large_number(x) if pd.notna(x) else 'N/A'
        )
        display_cols.append('Market Cap')

    # Display table
    st.dataframe(
        display_df[display_cols],
        use_container_width=True,
        hide_index=True
    )


def render_summary_metrics(df: pd.DataFrame):
    """
    Render summary metrics in columns

    Args:
        df: DataFrame with latest prices
    """
    if df.empty:
        return

    st.subheader("📊 Market Summary")

    cols = st.columns(4)

    # Total coins tracked
    with cols[0]:
        st.metric(
            label="Coins Tracked",
            value=len(df)
        )

    # Average 24h change
    with cols[1]:
        avg_change = df['price_change_percentage_24h'].mean()
        st.metric(
            label="Avg 24h Change",
            value=format_percentage(avg_change, include_sign=False),
            delta=format_percentage(avg_change)
        )

    # Top gainer
    with cols[2]:
        top_gainer = df.loc[df['price_change_percentage_24h'].idxmax()]
        st.metric(
            label="Top Gainer",
            value=top_gainer['symbol'].upper(),
            delta=format_percentage(top_gainer['price_change_percentage_24h'])
        )

    # Top loser
    with cols[3]:
        top_loser = df.loc[df['price_change_percentage_24h'].idxmin()]
        st.metric(
            label="Top Loser",
            value=top_loser['symbol'].upper(),
            delta=format_percentage(top_loser['price_change_percentage_24h'])
        )