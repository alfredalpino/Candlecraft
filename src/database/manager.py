"""
Unified database management module.

This module provides a single interface for storing OHLCV data from all
asset classes. It handles schema creation, inserts, updates, and queries
in a consistent manner regardless of the data source.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, JSON, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from ..models.ohlcv import OHLCVData, AssetClass
from ..utils.config import get_config, DatabaseConfig
from ..utils.logger import get_logger
from ..utils.exceptions import DatabaseError

Base = declarative_base()


class OHLCVRecord(Base):
    """
    SQLAlchemy model for OHLCV data.
    
    This table stores normalized OHLCV data from all asset classes
    in a unified schema.
    """
    
    __tablename__ = "ohlcv_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    asset_class = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)
    timeframe = Column(String(20), nullable=False, index=True)
    source = Column(String(50), nullable=False)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: same symbol, asset_class, timestamp, and timeframe
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "asset_class",
            "timestamp",
            "timeframe",
            name="uq_symbol_asset_timestamp_timeframe",
        ),
        Index("idx_symbol_asset_timeframe", "symbol", "asset_class", "timeframe"),
        Index("idx_timestamp_asset", "timestamp", "asset_class"),
    )


class DatabaseManager:
    """
    Unified database manager for OHLCV data.
    
    Handles all database operations including:
    - Schema creation and migrations
    - Inserting new OHLCV records
    - Updating existing records
    - Querying data
    - Handling duplicates and conflicts
    """
    
    def __init__(self, db_config: Optional[DatabaseConfig] = None):
        """
        Initialize database manager.
        
        Args:
            db_config: Optional database configuration. If None, loads from environment.
        """
        self.logger = get_logger("database.manager")
        config = get_config()
        self.db_config = db_config or config.database
        
        # Build connection string
        if self.db_config.dialect == "sqlite":
            connection_string = f"sqlite:///{self.db_config.database}"
        elif self.db_config.dialect == "postgresql":
            connection_string = (
                f"postgresql://{self.db_config.user}:{self.db_config.password}"
                f"@{self.db_config.host}:{self.db_config.port}/{self.db_config.database}"
            )
        elif self.db_config.dialect == "mysql":
            connection_string = (
                f"mysql+pymysql://{self.db_config.user}:{self.db_config.password}"
                f"@{self.db_config.host}:{self.db_config.port}/{self.db_config.database}"
            )
        else:
            raise DatabaseError(f"Unsupported database dialect: {self.db_config.dialect}")
        
        # Create engine
        try:
            self.engine = create_engine(
                connection_string,
                echo=False,  # Set to True for SQL query logging
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,  # Recycle connections after 1 hour
            )
            self.SessionLocal = sessionmaker(bind=self.engine)
            self.logger.info(f"Database manager initialized for {self.db_config.dialect}")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Failed to initialize database: {e}") from e
    
    def create_tables(self):
        """
        Create all database tables.
        
        This should be called once to set up the database schema.
        Safe to call multiple times (won't recreate existing tables).
        """
        try:
            Base.metadata.create_all(self.engine)
            self.logger.info("Database tables created/verified")
        except Exception as e:
            self.logger.error(f"Failed to create tables: {e}")
            raise DatabaseError(f"Failed to create tables: {e}") from e
    
    def insert_ohlcv(self, ohlcv_data: OHLCVData, update_on_conflict: bool = True) -> bool:
        """
        Insert a single OHLCV record.
        
        Args:
            ohlcv_data: OHLCVData object to insert
            update_on_conflict: If True, update existing record on conflict
        
        Returns:
            True if inserted/updated successfully, False otherwise
        
        Raises:
            DatabaseError: If database operation fails
        """
        session = self.SessionLocal()
        try:
            # Check if record already exists
            existing = session.query(OHLCVRecord).filter_by(
                symbol=ohlcv_data.symbol,
                asset_class=ohlcv_data.asset_class.value,
                timestamp=ohlcv_data.timestamp,
                timeframe=ohlcv_data.timeframe,
            ).first()
            
            if existing:
                if update_on_conflict:
                    # Update existing record
                    existing.open = ohlcv_data.open
                    existing.high = ohlcv_data.high
                    existing.low = ohlcv_data.low
                    existing.close = ohlcv_data.close
                    existing.volume = ohlcv_data.volume
                    existing.source = ohlcv_data.source
                    existing.metadata = ohlcv_data.metadata
                    existing.updated_at = datetime.utcnow()
                    session.commit()
                    self.logger.debug(f"Updated existing record: {ohlcv_data.symbol} @ {ohlcv_data.timestamp}")
                    return True
                else:
                    self.logger.debug(f"Record already exists, skipping: {ohlcv_data.symbol} @ {ohlcv_data.timestamp}")
                    return False
            else:
                # Insert new record
                record = OHLCVRecord(
                    symbol=ohlcv_data.symbol,
                    asset_class=ohlcv_data.asset_class.value,
                    timestamp=ohlcv_data.timestamp,
                    open=ohlcv_data.open,
                    high=ohlcv_data.high,
                    low=ohlcv_data.low,
                    close=ohlcv_data.close,
                    volume=ohlcv_data.volume,
                    timeframe=ohlcv_data.timeframe,
                    source=ohlcv_data.source,
                    metadata=ohlcv_data.metadata,
                )
                session.add(record)
                session.commit()
                self.logger.debug(f"Inserted new record: {ohlcv_data.symbol} @ {ohlcv_data.timestamp}")
                return True
        
        except IntegrityError as e:
            session.rollback()
            if update_on_conflict:
                # Retry with update
                return self.insert_ohlcv(ohlcv_data, update_on_conflict=True)
            else:
                self.logger.warning(f"Integrity error (duplicate?): {e}")
                return False
        
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error inserting record: {e}")
            raise DatabaseError(f"Failed to insert record: {e}") from e
        
        finally:
            session.close()
    
    def insert_batch(
        self,
        ohlcv_list: List[OHLCVData],
        update_on_conflict: bool = True,
        batch_size: int = 1000,
    ) -> Dict[str, int]:
        """
        Insert multiple OHLCV records in batches.
        
        Args:
            ohlcv_list: List of OHLCVData objects to insert
            update_on_conflict: If True, update existing records on conflict
            batch_size: Number of records to process per batch
        
        Returns:
            Dictionary with counts: {'inserted': int, 'updated': int, 'skipped': int, 'errors': int}
        
        Raises:
            DatabaseError: If database operation fails
        """
        stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}
        
        session = self.SessionLocal()
        try:
            for i in range(0, len(ohlcv_list), batch_size):
                batch = ohlcv_list[i : i + batch_size]
                
                for ohlcv_data in batch:
                    try:
                        # Check if record exists
                        existing = session.query(OHLCVRecord).filter_by(
                            symbol=ohlcv_data.symbol,
                            asset_class=ohlcv_data.asset_class.value,
                            timestamp=ohlcv_data.timestamp,
                            timeframe=ohlcv_data.timeframe,
                        ).first()
                        
                        if existing:
                            if update_on_conflict:
                                existing.open = ohlcv_data.open
                                existing.high = ohlcv_data.high
                                existing.low = ohlcv_data.low
                                existing.close = ohlcv_data.close
                                existing.volume = ohlcv_data.volume
                                existing.source = ohlcv_data.source
                                existing.metadata = ohlcv_data.metadata
                                existing.updated_at = datetime.utcnow()
                                stats["updated"] += 1
                            else:
                                stats["skipped"] += 1
                        else:
                            record = OHLCVRecord(
                                symbol=ohlcv_data.symbol,
                                asset_class=ohlcv_data.asset_class.value,
                                timestamp=ohlcv_data.timestamp,
                                open=ohlcv_data.open,
                                high=ohlcv_data.high,
                                low=ohlcv_data.low,
                                close=ohlcv_data.close,
                                volume=ohlcv_data.volume,
                                timeframe=ohlcv_data.timeframe,
                                source=ohlcv_data.source,
                                metadata=ohlcv_data.metadata,
                            )
                            session.add(record)
                            stats["inserted"] += 1
                    
                    except Exception as e:
                        self.logger.warning(f"Error processing record: {e}")
                        stats["errors"] += 1
                        continue
                
                # Commit batch
                try:
                    session.commit()
                    self.logger.info(
                        f"Batch {i//batch_size + 1}: "
                        f"Inserted {stats['inserted']}, Updated {stats['updated']}, "
                        f"Skipped {stats['skipped']}, Errors {stats['errors']}"
                    )
                except IntegrityError:
                    session.rollback()
                    # Retry batch with individual inserts
                    for ohlcv_data in batch:
                        if self.insert_ohlcv(ohlcv_data, update_on_conflict):
                            if stats["inserted"] > 0:
                                stats["inserted"] += 1
                            else:
                                stats["updated"] += 1
                        else:
                            stats["skipped"] += 1
        
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error in batch insert: {e}")
            raise DatabaseError(f"Failed to insert batch: {e}") from e
        
        finally:
            session.close()
        
        return stats
    
    def query_ohlcv(
        self,
        symbol: str,
        asset_class: AssetClass,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[OHLCVData]:
        """
        Query OHLCV data from the database.
        
        Args:
            symbol: Trading symbol
            asset_class: Asset class
            timeframe: Timeframe string
            start: Optional start datetime
            end: Optional end datetime
            limit: Optional maximum number of records to return
        
        Returns:
            List of OHLCVData objects
        
        Raises:
            DatabaseError: If query fails
        """
        session = self.SessionLocal()
        try:
            query = session.query(OHLCVRecord).filter_by(
                symbol=symbol,
                asset_class=asset_class.value,
                timeframe=timeframe,
            )
            
            if start:
                query = query.filter(OHLCVRecord.timestamp >= start)
            
            if end:
                query = query.filter(OHLCVRecord.timestamp <= end)
            
            query = query.order_by(OHLCVRecord.timestamp.asc())
            
            if limit:
                query = query.limit(limit)
            
            records = query.all()
            
            # Convert to OHLCVData objects
            ohlcv_list = []
            for record in records:
                ohlcv = OHLCVData(
                    symbol=record.symbol,
                    asset_class=AssetClass(record.asset_class),
                    timestamp=record.timestamp,
                    open=record.open,
                    high=record.high,
                    low=record.low,
                    close=record.close,
                    volume=record.volume,
                    timeframe=record.timeframe,
                    source=record.source,
                    metadata=record.metadata,
                )
                ohlcv_list.append(ohlcv)
            
            self.logger.info(f"Queried {len(ohlcv_list)} records for {symbol}")
            return ohlcv_list
        
        except SQLAlchemyError as e:
            self.logger.error(f"Database error querying data: {e}")
            raise DatabaseError(f"Failed to query data: {e}") from e
        
        finally:
            session.close()
    
    def get_latest_timestamp(
        self,
        symbol: str,
        asset_class: AssetClass,
        timeframe: str,
    ) -> Optional[datetime]:
        """
        Get the latest timestamp for a symbol/asset_class/timeframe combination.
        
        Useful for incremental data updates.
        
        Args:
            symbol: Trading symbol
            asset_class: Asset class
            timeframe: Timeframe string
        
        Returns:
            Latest timestamp or None if no data exists
        """
        session = self.SessionLocal()
        try:
            record = (
                session.query(OHLCVRecord)
                .filter_by(
                    symbol=symbol,
                    asset_class=asset_class.value,
                    timeframe=timeframe,
                )
                .order_by(OHLCVRecord.timestamp.desc())
                .first()
            )
            
            if record:
                return record.timestamp
            return None
        
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting latest timestamp: {e}")
            raise DatabaseError(f"Failed to get latest timestamp: {e}") from e
        
        finally:
            session.close()
