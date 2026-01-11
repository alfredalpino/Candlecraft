"""
Example script for pulling forex data.

This script demonstrates how to:
1. Initialize the forex provider
2. Authenticate with OANDA
3. Fetch OHLCV data
4. Store data in the database
"""

from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.providers import ForexProvider
from src.database import DatabaseManager
from src.models.ohlcv import AssetClass
from src.utils.logger import setup_logger

# Set up logging
logger = setup_logger("example.forex", log_level="INFO")


def main():
    """Main function to pull forex data."""
    
    # Initialize provider
    logger.info("Initializing forex provider...")
    provider = ForexProvider()
    
    # Authenticate
    logger.info("Authenticating with OANDA...")
    try:
        provider.authenticate()
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return
    
    # Initialize database
    logger.info("Initializing database...")
    db = DatabaseManager()
    db.create_tables()
    
    # Define symbols to fetch (OANDA format: BASE_QUOTE)
    symbols = ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD"]
    
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
    
    logger.info("Forex data pull completed!")


if __name__ == "__main__":
    main()
