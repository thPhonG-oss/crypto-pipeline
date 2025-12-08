"""
Crypto Monitoring Dashboard - Main App
=======================================

Streamlit dashboard to visualize crypto price data from Airflow pipeline

Run with: streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.db_client import CryptoDBClient
from components import price_cards, charts, alerts

# Page configuration
st.set_page_config(
    page_title="Crypto Monitor",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    h1 {
        color: #FF6B35;
    }
    .stMetric {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
    }
    .stAlert {
        background-color: #1E1E1E;
        border: 1px solid #FFD700;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_db_client():
    """Initialize database client (cached)"""
    return CryptoDBClient()


def main():
    """Main application"""

    # Header
    st.title("💰 Crypto Price Monitoring Dashboard")
    st.markdown("Real-time cryptocurrency price tracking powered by Apache Airflow")

    # Initialize database client
    db_client = get_db_client()

    # Test connection
    if not db_client.test_connection():
        st.error("❌ Cannot connect to database. Please check your configuration.")
        st.info("💡 Make sure PostgreSQL is running and accessible")
        return

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Settings")

        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        if auto_refresh:
            # Auto-refresh every 30 seconds
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=30000, key="datarefresh")
            st.caption("🔄 Refreshing every 30s")

        st.divider()

        # Time range selector
        st.subheader("📅 Time Range")
        time_range = st.selectbox(
            "Select period",
            options=[
                ("Last 24 hours", 24),
                ("Last 3 days", 72),
                ("Last 7 days", 168),
                ("Last 14 days", 336),
                ("Last 30 days", 720)
            ],
            format_func=lambda x: x[0],
            index=2  # Default: 7 days
        )
        hours = time_range[1]

        st.divider()

        # View mode selector
        st.subheader("👁️ View Mode")
        view_mode = st.radio(
            "Display style",
            options=["Cards", "Table", "Both"],
            index=0
        )

        st.divider()

        # Info section
        st.subheader("ℹ️ Info")
        st.caption("Dashboard Version: 1.0")
        st.caption(f"Current Time: {datetime.now().strftime('%H:%M:%S')}")
        st.caption("Data Source: Airflow Pipeline")

    # Main content area
    try:
        # Fetch latest prices
        with st.spinner("Loading latest prices..."):
            latest_df = db_client.get_latest_prices()

        if latest_df.empty:
            st.warning("⚠️ No data available yet. Please wait for the first pipeline run.")
            return

        # Display summary metrics
        price_cards.render_summary_metrics(latest_df)

        st.divider()

        # Display price cards/table
        if view_mode in ["Cards", "Both"]:
            price_cards.render_price_cards(latest_df)

        if view_mode in ["Table", "Both"]:
            if view_mode == "Both":
                st.divider()
            price_cards.render_compact_table(latest_df)

        st.divider()

        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Price Charts",
            "⚠️ Alerts",
            "📊 Analysis",
            "🔍 Pipeline Status"
        ])

        # TAB 1: Price Charts
        with tab1:
            # Fetch historical data
            with st.spinner("Loading historical data..."):
                history_df = db_client.get_price_history(hours=hours)

            if not history_df.empty:
                # Coin selector
                available_coins = history_df['coin_id'].unique().tolist()
                selected_coins = st.multiselect(
                    "Select coins to display",
                    options=available_coins,
                    default=available_coins[:3] if len(available_coins) >= 3 else available_coins,
                    format_func=lambda x: x.upper()
                )

                if selected_coins:
                    # Price history line chart
                    charts.render_price_history_chart(history_df, selected_coins)
                else:
                    st.info("👆 Select at least one coin to view price history")

                st.divider()

                # 24h change bar chart
                charts.render_percentage_change_chart(latest_df)
            else:
                st.info("📊 Historical data not available yet")

        # TAB 2: Alerts
        with tab2:
            # Fetch alert history
            with st.spinner("Loading alert history..."):
                alert_df = db_client.get_alert_history(hours=hours)

            # Render alert components
            alerts.render_alert_history(alert_df)

            if not alert_df.empty:
                st.divider()
                alerts.render_alert_frequency_chart(alert_df)

        # TAB 3: Analysis
        with tab3:
            col1, col2 = st.columns(2)

            with col1:
                # Market cap distribution
                charts.render_market_cap_chart(latest_df)

            with col2:
                # Trading volume
                charts.render_volume_chart(latest_df)

            # Correlation heatmap (if enough data)
            if not history_df.empty and len(history_df['coin_id'].unique()) >= 2:
                st.divider()
                charts.render_correlation_heatmap(history_df)

        # TAB 4: Pipeline Status
        with tab4:
            st.subheader("🔧 Pipeline Information")

            # Fetch pipeline runs
            with st.spinner("Loading pipeline status..."):
                runs_df = db_client.get_pipeline_runs(limit=20)

            if not runs_df.empty:
                st.success(f"✅ Pipeline is operational")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "Total Runs",
                        len(runs_df)
                    )

                with col2:
                    latest_run = pd.to_datetime(runs_df['execution_date'].iloc[0])
                    time_since = datetime.now() - latest_run.tz_localize(None)
                    hours_ago = int(time_since.total_seconds() / 3600)
                    st.metric(
                        "Last Run",
                        f"{hours_ago}h ago"
                    )

                with col3:
                    avg_coins = int(runs_df['coins_processed'].mean())
                    st.metric(
                        "Avg Coins/Run",
                        avg_coins
                    )

                st.divider()

                # Pipeline run history
                st.markdown("### 📅 Recent Pipeline Runs")

                display_runs = runs_df.copy()
                display_runs['Execution Time'] = pd.to_datetime(
                    display_runs['execution_date']
                ).dt.strftime('%Y-%m-%d %H:%M:%S')
                display_runs['Coins Processed'] = display_runs['coins_processed']

                st.dataframe(
                    display_runs[['Execution Time', 'Coins Processed']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("⚠️ No pipeline runs detected")

            st.divider()

            # System info
            st.markdown("### 🖥️ System Information")

            col1, col2 = st.columns(2)

            with col1:
                st.info("""
                **Airflow DAG:** `crypto_price_pipeline`

                **Schedule:** Every 4 hours

                **Data Source:** CoinGecko API
                """)

            with col2:
                st.info("""
                **Database:** PostgreSQL

                **Notification:** Telegram

                **Alert Threshold:** ±5%
                """)

    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")
        st.info("💡 Check if the Airflow pipeline has run successfully")

        # Show error details in expander
        with st.expander("🐛 Error Details"):
            st.code(str(e))


# Footer
def render_footer():
    """Render page footer"""
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>🚀 Built with Apache Airflow + Streamlit | 📊 Data from CoinGecko API</p>
        <p style='font-size: 0.8em;'>For educational purposes - Seminar Project</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
    render_footer()