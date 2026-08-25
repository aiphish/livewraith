### Factory module to build out singleton classes on startup

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from aiphish.livewraith.config import LiveWraithConfig

def build_db_engine(cfg: LiveWraithConfig) -> AsyncEngine:
    """
    Builds an SQLite3 database engine with the given configuration.
    """
    db_uri = "sqlite+aiosqlite:///aiphish/db/livewraith.db"

    return create_async_engine(
        db_uri, 
        echo=cfg.DEBUG, 
    )