"""
Database client for Streamlit dashboard
Queries PostgreSQL to fetch crypto data
"""

import psycopg2
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict

# Database configuration (same as your DAG)
DB_CONFIG = {
    'host': 'localhost',  # Change to 'postgres' if running in Docker network
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'postgres'
}


class CryptoDBClient:
    """Client for querying crypto price data"""

    def __init__(self, config: Dict = None):
        """Initialize with custom config or use defaults"""
        self.config = config or DB_CONFIG

    def _get_connection(self):
        """Create database connection"""
        return psycopg2.connect(**self.config)

    def get_latest_prices(self) -> pd.DataFrame:
        """
        Get latest prices for all coins

        Returns:
            DataFrame with columns: coin_id, symbol, current_price,
            price_change_24h, price_change_percentage_24h, last_updated
        """
        query = """
            SELECT DISTINCT ON (coin_id)
                coin_id,
                symbol,
                current_price,
                market_cap,
                total_volume,
                price_change_24h,
                price_change_percentage_24h,
                last_updated,
                execution_date
            FROM crypto_prices
            ORDER BY coin_id, execution_date DESC
        """

        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn)

        return df

    def get_price_history(
            self,
            coin_id: str = None,
            hours: int = 168  # 7 days default
    ) -> pd.DataFrame:
        """
        Get historical prices for specific coin or all coins

        Args:
            coin_id: Specific coin (None = all coins)
            hours: How many hours of history

        Returns:
            DataFrame with time series data
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        query = """
            SELECT 
                execution_date,
                coin_id,
                symbol,
                current_price,
                price_change_percentage_24h,
                market_cap,
                total_volume
            FROM crypto_prices
            WHERE execution_date >= %s
        """

        params = [cutoff_time]

        if coin_id:
            query += " AND coin_id = %s"
            params.append(coin_id)

        query += " ORDER BY execution_date ASC"

        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        return df

    def get_alert_history(self, hours: int = 168) -> pd.DataFrame:
        """
        Get coins that triggered alerts (price change > threshold)

        Args:
            hours: Lookback period

        Returns:
            DataFrame with alert events
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        threshold = 5.0  # Same as DAG threshold

        query = """
            SELECT 
                execution_date,
                coin_id,
                symbol,
                current_price,
                price_change_24h,
                price_change_percentage_24h
            FROM crypto_prices
            WHERE execution_date >= %s
              AND ABS(price_change_percentage_24h) >= %s
            ORDER BY execution_date DESC, ABS(price_change_percentage_24h) DESC
        """

        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=[cutoff_time, threshold])

        return df

    def get_statistics(self) -> Dict:
        """
        Get summary statistics

        Returns:
            Dict with aggregated metrics
        """
        query = """
            WITH latest_prices AS (
                SELECT DISTINCT ON (coin_id)
                    coin_id,
                    symbol,
                    current_price,
                    price_change_percentage_24h,
                    market_cap,
                    total_volume
                FROM crypto_prices
                ORDER BY coin_id, execution_date DESC
            )
            SELECT 
                COUNT(*) as total_coins,
                SUM(market_cap) as total_market_cap,
                SUM(total_volume) as total_volume_24h,
                AVG(price_change_percentage_24h) as avg_change_24h,
                MAX(price_change_percentage_24h) as max_gain_24h,
                MIN(price_change_percentage_24h) as max_loss_24h
            FROM latest_prices
        """

        with self._get_connection() as conn:
            result = pd.read_sql_query(query, conn).iloc[0].to_dict()

        return result

    def get_top_movers(self, limit: int = 5) -> pd.DataFrame:
        """
        Get top gainers and losers

        Args:
            limit: Number of coins to return

        Returns:
            DataFrame with top movers
        """
        query = """
            WITH latest_prices AS (
                SELECT DISTINCT ON (coin_id)
                    coin_id,
                    symbol,
                    current_price,
                    price_change_percentage_24h
                FROM crypto_prices
                ORDER BY coin_id, execution_date DESC
            )
            SELECT * FROM latest_prices
            ORDER BY ABS(price_change_percentage_24h) DESC
            LIMIT %s
        """

        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=[limit])

        return df

    def get_pipeline_runs(self, limit: int = 10) -> pd.DataFrame:
        """
        Get recent pipeline execution info

        Args:
            limit: Number of runs to return

        Returns:
            DataFrame with execution timestamps
        """
        query = """
            SELECT DISTINCT 
                execution_date,
                COUNT(DISTINCT coin_id) as coins_processed
            FROM crypto_prices
            GROUP BY execution_date
            ORDER BY execution_date DESC
            LIMIT %s
        """

        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=[limit])

        return df

    def test_connection(self) -> bool:
        """Test if database is accessible"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False