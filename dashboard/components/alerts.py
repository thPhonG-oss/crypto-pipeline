"""
Alert history component
Shows timeline of triggered alerts
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys
sys.path.append('..')
from utils.formatters import format_price, format_percentage, get_trend_emoji


def render_alert_history(df: pd.DataFrame):
    """
    Render alert history with timeline and details

    Args:
        df: DataFrame with alert data (coins that exceeded threshold)
    """
    if df.empty:
        st.info("🎉 No alerts triggered in this period - market is stable!")
        return

    st.subheader("⚠️ Alert History")

    # Display summary metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Alerts", len(df))

    with col2:
        unique_coins = df['coin_id'].nunique()
        st.metric("Coins with Alerts", unique_coins)

    with col3:
        max_change = df['price_change_percentage_24h'].abs().max()
        st.metric("Max Change", format_percentage(max_change, include_sign=False))

    st.divider()

    # Render timeline chart
    render_alert_timeline(df)

    st.divider()

    # Render detailed table
    render_alert_table(df)


def render_alert_timeline(df: pd.DataFrame):
    """
    Render interactive timeline of alerts

    Args:
        df: DataFrame with alert data
    """
    st.markdown("### 📅 Alert Timeline")

    # Prepare data for plotting
    df = df.sort_values('execution_date')

    # Create figure
    fig = go.Figure()

    # Separate positive and negative changes
    positive_alerts = df[df['price_change_percentage_24h'] > 0]
    negative_alerts = df[df['price_change_percentage_24h'] < 0]

    # Add trace for positive changes (pumps)
    if not positive_alerts.empty:
        fig.add_trace(go.Scatter(
            x=positive_alerts['execution_date'],
            y=positive_alerts['price_change_percentage_24h'],
            mode='markers',
            name='Pumps 📈',
            marker=dict(
                size=15,
                color='green',
                symbol='triangle-up',
                line=dict(width=2, color='white')
            ),
            text=positive_alerts['symbol'].str.upper(),
            hovertemplate=(
                '<b>%{text}</b><br>'
                'Change: %{y:.2f}%<br>'
                'Time: %{x|%Y-%m-%d %H:%M}<br>'
                '<extra></extra>'
            )
        ))

    # Add trace for negative changes (dumps)
    if not negative_alerts.empty:
        fig.add_trace(go.Scatter(
            x=negative_alerts['execution_date'],
            y=negative_alerts['price_change_percentage_24h'],
            mode='markers',
            name='Dumps 📉',
            marker=dict(
                size=15,
                color='red',
                symbol='triangle-down',
                line=dict(width=2, color='white')
            ),
            text=negative_alerts['symbol'].str.upper(),
            hovertemplate=(
                '<b>%{text}</b><br>'
                'Change: %{y:.2f}%<br>'
                'Time: %{x|%Y-%m-%d %H:%M}<br>'
                '<extra></extra>'
            )
        ))

    # Add threshold lines
    fig.add_hline(y=5, line_dash="dash", line_color="yellow",
                  annotation_text="+5% threshold")
    fig.add_hline(y=-5, line_dash="dash", line_color="yellow",
                  annotation_text="-5% threshold")

    # Update layout
    fig.update_layout(
        title="Alert Events Over Time",
        xaxis_title="Date",
        yaxis_title="Price Change (%)",
        height=400,
        template='plotly_dark',
        hovermode='closest',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Display
    st.plotly_chart(fig, use_container_width=True)


def render_alert_table(df: pd.DataFrame):
    """
    Render detailed table of alerts

    Args:
        df: DataFrame with alert data
    """
    st.markdown("### 📋 Alert Details")

    # Prepare display dataframe
    display_df = df.copy()
    display_df = display_df.sort_values('execution_date', ascending=False)

    # Format columns
    display_df['Time'] = pd.to_datetime(display_df['execution_date']).dt.strftime(
        '%Y-%m-%d %H:%M'
    )
    display_df['Coin'] = display_df['symbol'].str.upper()
    display_df['Price'] = display_df['current_price'].apply(format_price)
    display_df['Change'] = display_df['price_change_percentage_24h'].apply(
        lambda x: format_percentage(x)
    )
    display_df['Trend'] = display_df['price_change_percentage_24h'].apply(
        get_trend_emoji
    )

    # Add severity indicator
    def get_severity(pct):
        abs_pct = abs(pct)
        if abs_pct >= 15:
            return "🔴 Critical"
        elif abs_pct >= 10:
            return "🟠 High"
        elif abs_pct >= 5:
            return "🟡 Medium"
        else:
            return "🟢 Low"

    display_df['Severity'] = display_df['price_change_percentage_24h'].apply(
        get_severity
    )

    # Select columns to display
    display_cols = ['Time', 'Trend', 'Coin', 'Price', 'Change', 'Severity']

    # Display table with color coding
    st.dataframe(
        display_df[display_cols],
        use_container_width=True,
        hide_index=True,
        height=400
    )

    # Add download button
    csv = display_df[display_cols].to_csv(index=False)
    st.download_button(
        label="📥 Download Alert History (CSV)",
        data=csv,
        file_name=f"crypto_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )


def render_alert_frequency_chart(df: pd.DataFrame):
    """
    Render bar chart showing alert frequency by coin

    Args:
        df: DataFrame with alert data
    """
    if df.empty:
        return

    st.markdown("### 📊 Alert Frequency by Coin")

    # Count alerts per coin
    alert_counts = df.groupby('symbol').size().reset_index(name='count')
    alert_counts = alert_counts.sort_values('count', ascending=True)

    # Create horizontal bar chart
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=alert_counts['symbol'].str.upper(),
        x=alert_counts['count'],
        orientation='h',
        marker_color='orange',
        text=alert_counts['count'],
        textposition='outside',
        hovertemplate=(
            '<b>%{y}</b><br>'
            'Alerts: %{x}<br>'
            '<extra></extra>'
        )
    ))

    # Update layout
    fig.update_layout(
        title="Number of Alerts per Coin",
        xaxis_title="Alert Count",
        yaxis_title="",
        height=max(300, len(alert_counts) * 40),
        template='plotly_dark',
        showlegend=False
    )

    # Display
    st.plotly_chart(fig, use_container_width=True)