#######################################################################################################
### Live streaming Wraith for the aiphish platform.
### This app takes recieves TTS output and generates the deepfake video frames
### to match what the TTS output says. Data is streamed in over websocket and out
### over webRTC. 
### Additionally, this app creates the cloned video identities for use with the livestream endpoints.
###
### This repo adapts code from https://github.com/lipku/LiveTalking/ published under Apache 2.0 
########################################################################################################


from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from aiphish.livewraith.config import LiveWraithConfig
from aiphish.livewraith.factory import (build_db_engine)

@asynccontextmanager
async def lifespan(app: FastAPI):   # pylint: disable=redefined-outer-name
    """
    This function provides startup and shutdown tasks for the
    FastAPI application to load the selected model and adapters (TODO)
    """

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

    db_engine = build_db_engine()
    session_maker = async_sessionmaker(
        bind=db_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )

    logger.info("Attaching singletons to state...")

    server.state.cfg = cfg
    server.state.db_engine = db_engine
    server.state.db_session_maker = session_maker

    logger.info("Importing routes...")

    import aiphish.livewraith.routes as routes

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
    
    
