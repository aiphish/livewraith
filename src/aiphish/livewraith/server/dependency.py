import asyncio
from typing import Annotated
from fastapi import Depends, Request, HTTPException
import logging

from aiphish.livewraith.config import LiveWraithConfig
from aiphish.livewraith.server.sessions import SessionManager
from aiphish.livewraith.wraithmuse.wraithmuse_types import WraithModel, WraithAvatar, WraithOpt
from aiphish.livewraith.server.musetalk import load_avatar, AvatarCreator

logger = logging.getLogger(__name__)


def get_session_mgr(request: Request) -> SessionManager:
    """
    Returns the session manager singleton.
    """
    return request.app.state.session_mgr

SessionDep = Annotated[SessionManager, Depends(get_session_mgr)]

def get_model(request: Request) -> WraithModel:
    """
    Returns the pre-loaded model.
    """
    return request.app.state.model

ModelDep = Annotated[WraithModel, Depends(get_model)]

async def get_avatar(request: Request, avatar_id: str) -> WraithAvatar:
    """
    Loads the avatar files
    """
    cache: dict[str, WraithAvatar] = request.app.state.avatars
    lock: asyncio.Lock = request.app.state.avatar_lock

    if avatar_id in cache:
        return cache[avatar_id]
    async with request.app.state.avatar_lock:
        try:
            cache[avatar_id] = await asyncio.to_thread(load_avatar, avatar_id)
        except FileNotFoundError as e:
            logger.warning("avatar not found: %s (%s)", avatar_id, e)
            raise HTTPException(status_code=404, detail=f"avatar not found: {avatar_id}") from e
        
    return cache[avatar_id]

AvatarDep = Annotated[WraithAvatar, Depends(get_avatar)]

def get_opt(request: Request) -> WraithOpt:
    """
    Returns the Options
    """
    return request.app.state.opt

OptDep = Annotated[WraithOpt, Depends(get_opt)]

def get_config(request: Request) -> LiveWraithConfig:
    """
    Returns the running configuration.
    """
    return request.app.state.cfg

ConfigDep = Annotated[LiveWraithConfig, Depends(get_config)]

def get_creator(request: Request) -> AvatarCreator:
    """
    Returns the avatar creator that tracks creation progress.
    """

    return request.app.state.creator

CreatorDep = Annotated[AvatarCreator, Depends(get_creator)]

