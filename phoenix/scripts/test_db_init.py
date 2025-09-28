"""
Test database initialization and table creation.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import text, inspect
from sqlalchemy.engine.reflection import Inspector
from phoenix.config import DATA_DIR
from phoenix.utils.database import DatabaseManager, db_manager
from phoenix.models import Base

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def get_table_info(session, table_name):
    """Get detailed information about a table's schema."""
    # Get table info
    result = await session.execute(
        text(f"PRAGMA table_info({table_name})")
    )
    columns = result.fetchall()
    
    # Get foreign key info
    result = await session.execute(
        text(f"PRAGMA foreign_key_list({table_name})")
    )
    fks = result.fetchall()
    
    # Get index info
    result = await session.execute(
        text(f"PRAGMA index_list({table_name})")
    )
    indexes = result.fetchall()
    
    return {
        'name': table_name,
        'columns': columns,
        'foreign_keys': fks,
        'indexes': indexes
    }

async def test_database_initialization():
    """Test database initialization and table creation."""
    try:
        # Ensure the data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Initialize the database
        logger.info("Initializing database...")
        await db_manager.initialize()
        
        # Verify that the database file was created
        db_path = os.path.join(DATA_DIR, "phoenix.db")
        if not os.path.exists(db_path):
            logger.error(f"Database file not found at {db_path}")
            return False
        
        logger.info(f"Database file created at {db_path}")
        
        # Check if tables were created
        async with db_manager.session() as session:
            # Get all tables
            result = await session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            )
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"All tables in database: {', '.join(tables) if tables else 'None'}")
            
            # Check for required tables
            required_tables = ['users', 'emails', 'email_categories', 'email_labels', 'email_category_mapping']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                logger.error(f"Missing required tables: {', '.join(missing_tables)}")
                return False
            
            logger.info("All required tables exist")
            
            # Get detailed info about tables with foreign key issues
            logger.info("Getting detailed schema information...")
            table_info = {}
            for table in tables:
                table_info[table] = await get_table_info(session, table)
                logger.debug(f"Table {table} info: {table_info[table]}")
            
            # Check foreign key constraints
            try:
                result = await session.execute(text("PRAGMA foreign_key_check"))
                fk_errors = result.fetchall()
                
                if fk_errors:
                    logger.error(f"Foreign key constraint errors found: {fk_errors}")
                    
                    # Get more details about the foreign key constraints
                    for error in fk_errors:
                        table = error[0]
                        rowid = error[1]
                        parent_table = error[2]
                        fk_id = error[3]
                        
                        logger.error(f"Foreign key error in table '{table}' (rowid={rowid}) "
                                   f"referencing table '{parent_table}' (fk_id={fk_id})")
                        
                        # Get the specific row causing the issue
                        result = await session.execute(
                            text(f"SELECT * FROM {table} WHERE rowid = :rowid"),
                            {'rowid': rowid}
                        )
                        row = result.fetchone()
                        if row:
                            logger.error(f"Problematic row data: {dict(row)}")
                    
                    return False
                
                logger.info("No foreign key constraint errors found")
                
            except Exception as e:
                logger.error(f"Error checking foreign key constraints: {e}", exc_info=True)
                return False
            
            # Check the schema of the email_category_mapping table
            mapping_info = table_info.get('email_category_mapping', {})
            logger.info("Email Category Mapping table schema:")
            for col in mapping_info.get('columns', []):
                logger.info(f"  Column: {col['name']} (Type: {col['type']}, PK: {col['pk'] > 0}, Not Null: {col['notnull']})")
            
            for fk in mapping_info.get('foreign_keys', []):
                logger.info(f"  Foreign Key: {fk['from']} -> {fk['table']}.{fk['to']}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error during database initialization test: {e}", exc_info=True)
        return False
    finally:
        # Clean up
        if 'db_manager' in locals() and hasattr(db_manager, 'close'):
            await db_manager.close()

if __name__ == "__main__":
    logger.info("Starting database initialization test...")
    
    # Run the test
    success = asyncio.run(test_database_initialization())
    
    if success:
        logger.info("Database initialization test completed successfully!")
        sys.exit(0)
    else:
        logger.error("Database initialization test failed!")
        sys.exit(1)
