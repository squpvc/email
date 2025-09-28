"""
Database management utilities for Project Phoenix.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional, Type, TypeVar, Union

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    create_async_engine, 
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base, sessionmaker

from ..config import DATA_DIR
from ..models.base import Base

logger = logging.getLogger(__name__)

# Type variable for SQLAlchemy models
ModelType = TypeVar("ModelType", bound=Base)

class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(
        self, 
        db_url: Optional[str] = None,
        echo: bool = False,
        create_tables: bool = True
    ):
        """Initialize the database manager.
        
        Args:
            db_url: Database URL. If not provided, uses SQLite in the data directory.
            echo: If True, log all SQL statements.
            create_tables: If True, create tables on initialization.
        """
        self.db_url = db_url or f"sqlite+aiosqlite:///{DATA_DIR}/phoenix.db"
        self.echo = echo
        self.create_tables = create_tables
        
        # Will be initialized in initialize()
        self._engine = None
        self._async_session_factory = None
        self._sync_engine = None
    
    async def initialize(self) -> None:
        """Initialize the database connection and create tables if needed."""
        logger.info(f"Initializing database: {self.db_url}")
        
        # Create async engine
        self._engine = create_async_engine(
            self.db_url,
            echo=self.echo,
            future=True,
            connect_args={"check_same_thread": False} if "sqlite" in self.db_url else {}
        )
        
        # Create async session factory
        self._async_session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )
        
        # Create sync engine for operations that require it (like Alembic)
        sync_url = self.db_url.replace("+aiosqlite", "") if "aiosqlite" in self.db_url else self.db_url
        self._sync_engine = create_engine(
            sync_url,
            echo=self.echo,
            future=True,
            connect_args={"check_same_thread": False} if "sqlite" in sync_url else {}
        )
        
        # Create tables if needed
        if self.create_tables:
            await self.create_database_tables()
    
    async def create_database_tables(self) -> None:
        """Create all database tables."""
        if not self._engine:
            raise RuntimeError("Database engine not initialized")
            
        logger.info("Creating database tables...")
        
        # Import all models to ensure they are registered with SQLAlchemy
        from ..models import email, calendar  # noqa
        
        # Create tables
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
    
    async def drop_database_tables(self) -> None:
        """Drop all database tables (for testing/development)."""
        if not self._engine:
            raise RuntimeError("Database engine not initialized")
            
        logger.warning("Dropping all database tables...")
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.warning("Database tables dropped successfully")
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session."""
        if not self._async_session_factory:
            raise RuntimeError("Database not initialized")
            
        session = self._async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            await session.close()
    
    async def execute(self, stmt, **params):
        """Execute a raw SQL statement."""
        if not self._engine:
            raise RuntimeError("Database engine not initialized")
            
        async with self._engine.connect() as conn:
            result = await conn.execute(text(stmt), params)
            await conn.commit()
            return result
    
    async def fetch_one(self, stmt, **params):
        """Fetch one row from a raw SQL query."""
        result = await self.execute(stmt, **params)
        return result.fetchone()
    
    async def fetch_all(self, stmt, **params):
        """Fetch all rows from a raw SQL query."""
        result = await self.execute(stmt, **params)
        return result.fetchall()
    
    async def get_or_create(
        self,
        model: Type[ModelType],
        defaults: Optional[dict] = None,
        **kwargs
    ) -> tuple[ModelType, bool]:
        """Get an instance of the model or create it if it doesn't exist.
        
        Args:
            model: SQLAlchemy model class.
            defaults: Default values for creating a new instance.
            **kwargs: Attributes to filter by.
            
        Returns:
            A tuple of (instance, created) where created is a boolean indicating
            whether the instance was created.
        """
        async with self.session() as session:
            instance = await session.get(model, **kwargs)
            if instance:
                return instance, False
                
            # Create new instance
            params = {**kwargs, **defaults} if defaults else kwargs
            instance = model(**params)
            
            session.add(instance)
            await session.commit()
            
            return instance, True
    
    def execute_sync(self, stmt, **params):
        """Execute a raw SQL statement synchronously."""
        if not self._sync_engine:
            raise RuntimeError("Synchronous database engine not initialized")
            
        with self._sync_engine.connect() as conn:
            result = conn.execute(text(stmt), params)
            conn.commit()
            return result
    
    def fetch_all_sync(self, stmt, **params):
        """Fetch all rows from a raw SQL query synchronously."""
        result = self.execute_sync(stmt, **params)
        return result.fetchall()
    
    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
        
        if self._sync_engine:
            self._sync_engine.dispose()
            self._sync_engine = None
        
        self._async_session_factory = None
    
    def __del__(self) -> None:
        """Ensure connections are closed when the object is destroyed."""
        if hasattr(self, '_engine') and self._engine:
            asyncio.create_task(self.close())


# Global database manager instance
db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get a database session."""
    async with db_manager.session() as session:
        yield session
