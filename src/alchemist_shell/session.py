import os
from typing import Optional, Union, Tuple
from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    AsyncEngine, 
    async_sessionmaker
)
from sqlalchemy.orm import sessionmaker, Session
from .utils import find_and_load_env

# Strict Type Aliases
DatabaseSession = Union[Session, AsyncSession]
DatabaseEngine = Union[Engine, AsyncEngine]

def _create_sync_session(url: str) -> Tuple[Session, Engine]:
    engine: Engine = create_engine(url, echo=False)
    # Correct sessionmaker typing for SQLAlchemy 2.0
    factory: sessionmaker[Session] = sessionmaker(
        bind=engine, 
        expire_on_commit=False
    )
    return factory(), engine

def _create_async_session(url: str) -> Tuple[AsyncSession, AsyncEngine]:
    engine: AsyncEngine = create_async_engine(url, echo=False)
    # async_sessionmaker is the future-proof standard
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, 
        expire_on_commit=False, 
        class_=AsyncSession
    )
    return factory(), engine

def get_session(
    db_url: Optional[str] = None, 
    env_file: Optional[str] = None
) -> Tuple[DatabaseSession, DatabaseEngine]:
    """
    Gateway to initialize the database connection.
    """
    find_and_load_env(env_file)
    url: Optional[str] = db_url or os.getenv("DATABASE_URL")
    
    if not url:
        raise ValueError("DATABASE_URL not found. Check your .env or --db-url.")

    # Detection logic
    is_async: bool = any(d in url for d in ["+asyncpg", "+aiosqlite"])

    if is_async:
        return _create_async_session(url)
    
    return _create_sync_session(url)