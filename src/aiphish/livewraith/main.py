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

from aiphish.livewraith.config import LiveWraithConfig

logger = logging.getLogger(__name__)

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

    

    
