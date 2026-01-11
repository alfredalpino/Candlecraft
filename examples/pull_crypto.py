"""
Example script for pulling cryptocurrency data.

This script demonstrates how to:
1. Initialize the crypto provider
2. Authenticate with Binance
3. Fetch OHLCV data
4. Store data in the database
"""

from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.providers import CryptoProvider
from src.database import DatabaseManager
from src.models.ohlcv import AssetClass
from src.utils.logger import setup_logger

# Set up logging
logger = setup_logger("example.crypto", log_level="INFO")


def main():
    """Main function to pull crypto data."""
    
    # Initialize provider
    logger.info("Initializing crypto provider...")
    provider = CryptoProvider()
    
    # Authenticate
    logger.info("Authenticating with Binance...")
    try:
        provider.authenticate()
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return
    
    # Initialize database
    logger.info("Initializing database...")
    db = DatabaseManager()
    db.create_tables()
    
    # Define symbols to fetch
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"]
    
    # Define time range (last 7 days for hourly data)
    end = datetime.now()
    start = end - timedelta(days=7)
    
    # Fetch and store data for each symbol
    for symbol in symbols:
        logger.info(f"Fetching data for {symbol}...")
        try:
            # Fetch data
            data = provider.fetch_ohlcv(
                symbol=symbol,
                timeframe="1hour",
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
    
    logger.info("Crypto data pull completed!")


if __name__ == "__main__":
    main()
