"""
Chart components using Plotly
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime


def render_price_history_chart(df: pd.DataFrame, selected_coins: list = None):
    """
    Render interactive line chart for price history

    Args:
        df: DataFrame with historical prices
        selected_coins: List of coin_ids to display (None = all)
    """
    if df.empty:
        st.warning("📈 No historical data available")
        return

    st.subheader("📈 Price History")

    # Filter by selected coins if provided
    if selected_coins:
        df = df[df['coin_id'].isin(selected_coins)]

    if df.empty:
        st.info("Select at least one coin to display")
        return

    # Create figure
    fig = go.Figure()

    # Add trace for each coin
    for coin_id in df['coin_id'].unique():
        coin_data = df[df['coin_id'] == coin_id].sort_values('execution_date')

        fig.add_trace(go.Scatter(
            x=coin_data['execution_date'],
            y=coin_data['current_price'],
            mode='lines+markers',
            name=coin_data['symbol'].iloc[0].upper(),
            hovertemplate=(
                '<b>%{fullData.name}</b><br>'
                'Price: $%{y:,.2f}<br>'
                'Date: %{x|%Y-%m-%d %H:%M}<br>'
                '<extra></extra>'
            )
        ))

    # Update layout
    fig.update_layout(
        title="Crypto Prices Over Time",
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        hovermode='x unified',
        height=500,
        template='plotly_dark',
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


def render_percentage_change_chart(df: pd.DataFrame):
    """
    Render bar chart for 24h percentage changes

    Args:
        df: DataFrame with latest prices
    """
    if df.empty:
        st.warning("📊 No data available")
        return

    st.subheader("📊 24h Price Changes")

    # Sort by percentage change
    df = df.sort_values('price_change_percentage_24h', ascending=True)

    # Create color list (red for negative, green for positive)
    colors = ['red' if x < 0 else 'green' for x in df['price_change_percentage_24h']]

    # Create figure
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df['symbol'].str.upper(),
        x=df['price_change_percentage_24h'],
        orientation='h',
        marker=dict(color=colors),
        text=df['price_change_percentage_24h'].apply(lambda x: f"{x:+.2f}%"),
        textposition='outside',
        hovertemplate=(
            '<b>%{y}</b><br>'
            'Change: %{x:.2f}%<br>'
            '<extra></extra>'
        )
    ))

    # Update layout
    fig.update_layout(
        title="24-Hour Price Changes (%)",
        xaxis_title="Change (%)",
        yaxis_title="",
        height=max(400, len(df) * 40),  # Dynamic height based on number of coins
        template='plotly_dark',
        showlegend=False
    )

    # Add vertical line at 0
    fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="white")

    # Display
    st.plotly_chart(fig, use_container_width=True)


def render_market_cap_chart(df: pd.DataFrame):
    """
    Render pie chart for market cap distribution

    Args:
        df: DataFrame with latest prices
    """
    if df.empty or 'market_cap' not in df.columns:
        return

    st.subheader("🥧 Market Cap Distribution")

    # Filter out null market caps
    df = df[df['market_cap'].notna()]

    if df.empty:
        st.info("Market cap data not available")
        return

    # Sort by market cap
    df = df.sort_values('market_cap', ascending=False)

    # Create pie chart
    fig = px.pie(
        df,
        values='market_cap',
        names=df['symbol'].str.upper(),
        title='Market Capitalization Share',
        hole=0.4,  # Donut chart
        template='plotly_dark'
    )

    # Update traces for better display
    fig.update_traces(
        textposition='outside',
        textinfo='label+percent',
        hovertemplate=(
            '<b>%{label}</b><br>'
            'Market Cap: $%{value:,.0f}<br>'
            'Share: %{percent}<br>'
            '<extra></extra>'
        )
    )

    # Display
    st.plotly_chart(fig, use_container_width=True)


def render_volume_chart(df: pd.DataFrame):
    """
    Render bar chart for 24h trading volume

    Args:
        df: DataFrame with latest prices
    """
    if df.empty or 'total_volume' not in df.columns:
        return

    st.subheader("📦 24h Trading Volume")

    # Filter out null volumes
    df = df[df['total_volume'].notna()]

    if df.empty:
        st.info("Volume data not available")
        return

    # Sort by volume
    df = df.sort_values('total_volume', ascending=False)

    # Create bar chart
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df['symbol'].str.upper(),
        y=df['total_volume'],
        marker_color='lightblue',
        text=df['total_volume'].apply(lambda x: f"${x / 1e9:.2f}B"),
        textposition='outside',
        hovertemplate=(
            '<b>%{x}</b><br>'
            'Volume: $%{y:,.0f}<br>'
            '<extra></extra>'
        )
    ))

    # Update layout
    fig.update_layout(
        title="24-Hour Trading Volume",
        xaxis_title="Coin",
        yaxis_title="Volume (USD)",
        height=400,
        template='plotly_dark',
        showlegend=False
    )

    # Display
    st.plotly_chart(fig, use_container_width=True)


def render_correlation_heatmap(df: pd.DataFrame):
    """
    Render correlation heatmap between coins

    Args:
        df: DataFrame with historical prices
    """
    if df.empty:
        return

    st.subheader("🔥 Price Correlation Heatmap")

    # Pivot data to get coins as columns
    pivot_df = df.pivot_table(
        index='execution_date',
        columns='symbol',
        values='current_price'
    )

    if pivot_df.shape[1] < 2:
        st.info("Need at least 2 coins for correlation analysis")
        return

    # Calculate correlation matrix
    corr_matrix = pivot_df.corr()

    # Create heatmap
    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        z=corr_matrix.values,
        x=[col.upper() for col in corr_matrix.columns],
        y=[col.upper() for col in corr_matrix.index],
        colorscale='RdYlGn',
        zmid=0,
        text=corr_matrix.values,
        texttemplate='%{text:.2f}',
        textfont={"size": 10},
        hovertemplate=(
            'Coins: %{x} vs %{y}<br>'
            'Correlation: %{z:.3f}<br>'
            '<extra></extra>'
        )
    ))

    # Update layout
    fig.update_layout(
        title="Price Correlation Matrix",
        height=max(400, len(corr_matrix) * 50),
        template='plotly_dark'
    )

    # Display
    st.plotly_chart(fig, use_container_width=True)

    st.caption("💡 Values closer to 1 indicate strong positive correlation, "
               "closer to -1 indicate negative correlation")