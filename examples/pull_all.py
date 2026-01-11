"""
Example script for pulling data from all asset classes.

This script demonstrates how to:
1. Initialize all providers
2. Fetch data from equities, crypto, and forex
3. Store all data in a unified database
"""

from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.providers import EquitiesProvider, CryptoProvider, ForexProvider
from src.database import DatabaseManager
from src.utils.logger import setup_logger

# Set up logging
logger = setup_logger("example.all", log_level="INFO")


def main():
    """Main function to pull data from all asset classes."""
    
    # Initialize database first
    logger.info("Initializing database...")
    db = DatabaseManager()
    db.create_tables()
    
    # Initialize all providers
    logger.info("Initializing providers...")
    providers = {
        "equities": EquitiesProvider(source="auto"),
        "crypto": CryptoProvider(),
        "forex": ForexProvider(),
    }
    
    # Authenticate all providers
    for name, provider in providers.items():
        logger.info(f"Authenticating {name} provider...")
        try:
            provider.authenticate()
            logger.info(f"{name.capitalize()} provider ready")
        except Exception as e:
            logger.error(f"Failed to authenticate {name} provider: {e}")
            providers.pop(name)  # Remove failed provider
    
    if not providers:
        logger.error("No providers available. Exiting.")
        return
    
    # Define time range
    end = datetime.now()
    start = end - timedelta(days=30)
    
    # Equities data
    if "equities" in providers:
        logger.info("=" * 50)
        logger.info("PULLING EQUITIES DATA")
        logger.info("=" * 50)
        equity_symbols = ["AAPL", "MSFT", "GOOGL"]
        for symbol in equity_symbols:
            try:
                data = providers["equities"].fetch_ohlcv(
                    symbol=symbol,
                    timeframe="1day",
                    start=start,
                    end=end,
                )
                if data:
                    stats = db.insert_batch(data, update_on_conflict=True)
                    logger.info(f"{symbol}: {stats['inserted']} inserted, {stats['updated']} updated")
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
    
    # Crypto data
    if "crypto" in providers:
        logger.info("=" * 50)
        logger.info("PULLING CRYPTO DATA")
        logger.info("=" * 50)
        crypto_symbols = ["BTCUSDT", "ETHUSDT"]
        for symbol in crypto_symbols:
            try:
                data = providers["crypto"].fetch_ohlcv(
                    symbol=symbol,
                    timeframe="1hour",
                    start=start,
                    end=end,
                )
                if data:
                    stats = db.insert_batch(data, update_on_conflict=True)
                    logger.info(f"{symbol}: {stats['inserted']} inserted, {stats['updated']} updated")
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
    
    # Forex data
    if "forex" in providers:
        logger.info("=" * 50)
        logger.info("PULLING FOREX DATA")
        logger.info("=" * 50)
        forex_symbols = ["EUR_USD", "GBP_USD"]
        for symbol in forex_symbols:
            try:
                data = providers["forex"].fetch_ohlcv(
                    symbol=symbol,
                    timeframe="1day",
                    start=start,
                    end=end,
                )
                if data:
                    stats = db.insert_batch(data, update_on_conflict=True)
                    logger.info(f"{symbol}: {stats['inserted']} inserted, {stats['updated']} updated")
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
    
    logger.info("=" * 50)
    logger.info("ALL DATA PULLS COMPLETED!")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
