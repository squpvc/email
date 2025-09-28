"""
Compare the schema of two tables to identify any mismatches.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from phoenix.config import DATA_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def get_table_schema(conn, table_name):
    """Get detailed schema information for a table."""
    # Get table info
    result = await conn.execute(
        text(f"PRAGMA table_info({table_name})")
    )
    columns = {}
    for row in result.fetchall():
        # cid, name, type, notnull, dflt_value, pk
        columns[row[1]] = {
            'type': row[2],
            'notnull': bool(row[3]),
            'default': row[4],
            'pk': bool(row[5])
        }
    
    # Get foreign key info
    result = await conn.execute(
        text(f"PRAGMA foreign_key_list({table_name})")
    )
    foreign_keys = []
    for row in result.fetchall():
        # id, seq, table, from, to, on_update, on_delete, match
        foreign_keys.append({
            'id': row[0],
            'seq': row[1],
            'table': row[2],
            'from': row[3],
            'to': row[4],
            'on_update': row[5],
            'on_delete': row[6],
            'match': row[7]
        })
    
    return {
        'name': table_name,
        'columns': columns,
        'foreign_keys': foreign_keys
    }

async def compare_tables_schema(table1, table2):
    """Compare the schema of two tables and log the differences."""
    # Create a temporary engine to inspect the database
    db_url = f"sqlite+aiosqlite:///{DATA_DIR}/phoenix.db"
    engine = create_async_engine(db_url, echo=False)
    
    async with engine.connect() as conn:
        # Get schema for both tables
        schema1 = await get_table_schema(conn, table1)
        schema2 = await get_table_schema(conn, table2)
        
        # Compare columns
        logger.info(f"\nComparing columns between {table1} and {table2}:")
        all_columns = set(schema1['columns'].keys()).union(set(schema2['columns'].keys()))
        
        differences = False
        for col in sorted(all_columns):
            col1 = schema1['columns'].get(col)
            col2 = schema2['columns'].get(col)
            
            if col1 is None:
                logger.warning(f"  - Column '{col}' exists in {table2} but not in {table1}")
                differences = True
            elif col2 is None:
                logger.warning(f"  - Column '{col}' exists in {table1} but not in {table2}")
                differences = True
            else:
                # Compare column properties
                if col1['type'] != col2['type']:
                    logger.warning(f"  - Column '{col}' type differs: {table1}={col1['type']}, {table2}={col2['type']}")
                    differences = True
                if col1['notnull'] != col2['notnull']:
                    logger.warning(f"  - Column '{col}' NOT NULL differs: {table1}={col1['notnull']}, {table2}={col2['notnull']}")
                    differences = True
                if col1.get('default') != col2.get('default'):
                    logger.warning(f"  - Column '{col}' default value differs: {table1}={col1.get('default')}, {table2}={col2.get('default')}")
                    differences = True
                if col1['pk'] != col2['pk']:
                    logger.warning(f"  - Column '{col}' PRIMARY KEY differs: {table1}={col1['pk']}, {table2}={col2['pk']}")
                    differences = True
        
        if not differences:
            logger.info("  - No differences found in column definitions")
        
        # Compare foreign keys
        logger.info(f"\nForeign keys in {table1}:")
        if schema1['foreign_keys']:
            for fk in schema1['foreign_keys']:
                logger.info(f"  - {fk['from']} -> {fk['table']}({fk['to']}) ON DELETE {fk['on_delete']}")
        else:
            logger.info("  - No foreign keys found")
        
        logger.info(f"\nForeign keys in {table2}:")
        if schema2['foreign_keys']:
            for fk in schema2['foreign_keys']:
                logger.info(f"  - {fk['from']} -> {fk['table']}({fk['to']}) ON DELETE {fk['on_delete']}")
        else:
            logger.info("  - No foreign keys found")
        
        # Check for circular references
        logger.info("\nChecking for circular references:")
        circular = False
        for fk in schema1['foreign_keys']:
            if fk['table'] == table2:
                logger.warning(f"  - {table1} has a foreign key to {table2}")
                circular = True
        for fk in schema2['foreign_keys']:
            if fk['table'] == table1:
                logger.warning(f"  - {table2} has a foreign key to {table1}")
                circular = True
        
        if not circular:
            logger.info("  - No circular references found")
        
        # Check for self-references
        logger.info("\nChecking for self-references:")
        self_ref = False
        for fk in schema1['foreign_keys']:
            if fk['table'] == table1:
                logger.warning(f"  - {table1} has a self-referencing foreign key on {fk['from']}")
                self_ref = True
        for fk in schema2['foreign_keys']:
            if fk['table'] == table2:
                logger.warning(f"  - {table2} has a self-referencing foreign key on {fk['from']}")
                self_ref = True
        
        if not self_ref:
            logger.info("  - No self-references found")

async def main():
    """Main function to compare the schema of email_labels and email_category_mapping tables."""
    table1 = "email_labels"
    table2 = "email_category_mapping"
    
    logger.info(f"Comparing schema between {table1} and {table2}...")
    await compare_tables_schema(table1, table2)

if __name__ == "__main__":
    asyncio.run(main())
