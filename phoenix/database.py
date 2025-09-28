"""
Database module for Project Phoenix.

This module provides the main database interface for the application.
It re-exports the DatabaseManager from the utils.database module
for easier imports throughout the application.
"""
from .utils.database import DatabaseManager
from sqlalchemy.orm import sessionmaker

# Global database manager instance
db_manager = DatabaseManager()

# Dependency for FastAPI to get a database session
async def get_db():
    """Get an async database session for FastAPI.
    
    Yields:
        AsyncSession: An async database session.
    """
    async with db_manager.session() as session:
        yield session

def get_db_session():
    """Get a synchronous database session.
    
    Returns:
        Session: A synchronous database session.
    """
    if not hasattr(db_manager, '_sync_engine') or not db_manager._sync_engine:
        raise RuntimeError("Database sync engine not initialized. Call initialize() first.")
    
    Session = sessionmaker(bind=db_manager._sync_engine)
    session = Session()
    try:
        return session
    except Exception as e:
        session.rollback()
        raise e

__all__ = ['DatabaseManager', 'db_manager', 'get_db', 'get_db_session']
