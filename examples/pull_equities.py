"""
Example script for pulling U.S. equities data.

This script demonstrates how to:
1. Initialize the equities provider
2. Authenticate with the data source
3. Fetch OHLCV data
4. Store data in the database
"""

from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.providers import EquitiesProvider
from src.database import DatabaseManager
from src.models.ohlcv import AssetClass
from src.utils.logger import setup_logger

# Set up logging
logger = setup_logger("example.equities", log_level="INFO")


def main():
    """Main function to pull equities data."""
    
    # Initialize provider (auto-detects Massive.com or Yahoo Finance)
    logger.info("Initializing equities provider...")
    provider = EquitiesProvider(source="auto")
    
    # Authenticate
    logger.info("Authenticating...")
    try:
        provider.authenticate()
        logger.info(f"Using data source: {provider.source_name}")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return
    
    # Initialize database
    logger.info("Initializing database...")
    db = DatabaseManager()
    db.create_tables()
    
    # Define symbols to fetch
    symbols = ["AAPL", "MSFT", "GOOGL", "SPY", "QQQ"]
    
    # Define time range (last 30 days)
    end = datetime.now()
    start = end - timedelta(days=30)
    
    # Fetch and store data for each symbol
    for symbol in symbols:
        logger.info(f"Fetching data for {symbol}...")
        try:
            # Fetch data
            data = provider.fetch_ohlcv(
                symbol=symbol,
                timeframe="1day",
                start=start,
                end=end,
            )
            
            if not data:
                logger.warning(f"No data returned for {symbol}")
                continue
            
            # Store in database
            stats = db.insert_batch(data, update_on_conflict=True)
            logger.info(
                f"{symbol}: Inserted {stats['inserted']}, "
                f"Updated {stats['updated']}, Skipped {stats['skipped']}"
            )
        
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            continue
    
    logger.info("Equities data pull completed!")


if __name__ == "__main__":
    main()
