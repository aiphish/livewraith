#######################################################################################################
### Live streaming Wraith for the aiphish platform.
### This app takes recieves TTS output and generates the deepfake video frames
### to match what the TTS output says. Data is streamed in over websocket and out
### over webRTC. 
### Additionally, this app creates the cloned video identities for use with the livestream endpoints.
###
### This repo adapts code from https://github.com/lipku/LiveTalking/ published under Apache 2.0 
########################################################################################################

import asyncio
from contextlib import asynccontextmanager
import logging
import hashlib
import secrets

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from aiphish.livewraith.config import LiveWraithConfig
from aiphish.livewraith.server.sessions import SessionManager

from aiphish.livewraith.wraithmuse.wraithmuse_types import WraithOpt

from aiphish.livewraith.server.musetalk import load_model

@asynccontextmanager
async def lifespan(app: FastAPI):   # pylint: disable=redefined-outer-name
    """
    This function provides startup and shutdown tasks for the
    FastAPI application to load the selected model and adapters (TODO)
    """

    cfg = app.state.cfg
    if not cfg.API_KEYS:
        if cfg.DEBUG:
            logger.info("DEV MODE, NO API KEYS PROVIDED. GENERATING...")
            key = secrets.token_urlsafe(32)
            logger.info("DO NOT USE IN PRODUCTION. API_KEY: %s", key)
            cfg.API_KEYS = [key]
        else:
            raise RuntimeError("PRODUCTION MODE: NO API KEYS FOUND")
            
    app.state.api_key_hashes = {hashlib.sha256(k.encode()).hexdigest() for k in cfg.API_KEYS}
    db_uri="sqlite+aiosqlite:///db/livewraith.db"
    db_engine: AsyncEngine = create_async_engine(
        db_uri,
        echo=cfg.DEBUG
    )
    app.state.db_engine = db_engine
    session_maker = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )
    app.state.db_session_maker = session_maker

    session_mgr = SessionManager()
    app.state.session_mgr = session_mgr

    app.state.model = load_model()
    app.state.avatars = {}
    app.state.avatar_lock = asyncio.Lock()
    app.state.opt: WraithOpt = cfg.OPT

    yield

    await db_engine.dispose()
    await session_mgr.close_all()

def create_app(cfg: LiveWraithConfig) -> FastAPI:
    """
    Entrypoint for the livewraith application server.
    """

    logger.info("Starting Aiphish LiveWraith...")

    server = FastAPI(lifespan=lifespan)

    if cfg.CORS_ORIGINS:
        logger.debug("CORS Enabled. URIs: %s", cfg.CORS_ORIGINS)
        server.add_middleware(
            CORSMiddleware,
            allow_origins=cfg.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            max_age=600
    )

    server.state.cfg = cfg

    logger.info("Importing routes...")

    import aiphish.livewraith.server.routes as routes

    server.include_router(routes.router, prefix="/api/v1")

    logger.info("Initialization finished.")

    return server

config = LiveWraithConfig()

logging.basicConfig(
    level=logging.DEBUG if config.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True
)
logger = logging.getLogger(__name__)
if config.DEBUG:
    logger.info("DEBUG MODE ENABLED. NOT FOR PRODUCTION.")

app = create_app(config)
    
    
