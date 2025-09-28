"""
Inspect the database schema and foreign key constraints.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from phoenix.config import DATA_DIR
from phoenix.models import Base
from phoenix.utils.database import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def get_table_info(conn, table_name):
    """Get detailed information about a table's schema."""
    # Get table info
    result = await conn.execute(
        text(f"PRAGMA table_info({table_name})")
    )
    columns = result.fetchall()
    
    # Get foreign key info
    result = await conn.execute(
        text(f"PRAGMA foreign_key_list({table_name})")
    )
    fks = result.fetchall()
    
    # Get index info
    result = await conn.execute(
        text(f"PRAGMA index_list({table_name})")
    )
    indexes = result.fetchall()
    
    return {
        'name': table_name,
        'columns': columns,
        'foreign_keys': fks,
        'indexes': indexes
    }

async def inspect_schema():
    """Inspect the database schema and print detailed information."""
    # Ensure the data directory exists
    data_dir = Path(DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a temporary engine to inspect the database
    db_url = f"sqlite+aiosqlite:///{DATA_DIR}/phoenix.db"
    engine = create_async_engine(db_url, echo=True)
    
    async with engine.connect() as conn:
        # Get all tables
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        )
        tables = [row[0] for row in result.fetchall()]
        
        if not tables:
            logger.warning("No tables found in the database")
            return
        
        logger.info(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        # Get detailed info for each table
        for table in tables:
            logger.info(f"\nInspecting table: {table}")
            
            # Get table info
            info = await get_table_info(conn, table)
            
            # Print columns
            logger.info("  Columns:")
            for col in info['columns']:
                # Access columns by position since we're getting tuples from raw SQL
                col_name = col[1]  # name is the second column in PRAGMA table_info
                col_type = col[2]  # type is the third column
                col_pk = col[5]    # pk is the sixth column (0 for non-PK)
                col_notnull = col[3]  # notnull is the fourth column
                logger.info(f"    {col_name} ({col_type}) {'PK' if col_pk > 0 else ''} {'NOT NULL' if col_notnull else 'NULL'}")
            
            # Print foreign keys
            if info['foreign_keys']:
                logger.info("  Foreign Keys:")
                for fk in info['foreign_keys']:
                    # Access columns by position since we're getting tuples from raw SQL
                    # fk[3] is 'from' column, fk[2] is 'table', fk[4] is 'to' column
                    logger.info(f"    {fk[3]} -> {fk[2]}.{fk[4]}")
            
            # Print indexes
            if info['indexes']:
                logger.info("  Indexes:")
                for idx in info['indexes']:
                    # Access columns by position since we're getting tuples from raw SQL
                    # idx[1] is the name, idx[2] is unique (0 or 1)
                    logger.info(f"    {idx[1]} (unique: {bool(idx[2])})")
        
        # Check foreign key constraints
        logger.info("\nChecking foreign key constraints...")
        try:
            result = await conn.execute(text("PRAGMA foreign_key_check"))
            fk_errors = result.fetchall()
            
            if fk_errors:
                logger.error("Foreign key constraint errors found:")
                for error in fk_errors:
                    logger.error(f"  Table: {error['table']}, Row ID: {error['rowid']}, Referenced Table: {error['parent']}, FK ID: {error['fkid']}")
            else:
                logger.info("No foreign key constraint errors found")
                
        except Exception as e:
            logger.error(f"Error checking foreign key constraints: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_schema())
