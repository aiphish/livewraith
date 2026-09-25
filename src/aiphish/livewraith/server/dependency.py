import asyncio
from uuid import UUID
from typing import Annotated
from fastapi import Depends, Request, HTTPException
from fastapi.requests import HTTPConnection
import logging

from aiphish.livewraith.config import LiveWraithConfig
from aiphish.livewraith.server.sessions import SessionManager
from aiphish.livewraith.wraithmuse.wraithmuse_types import WraithModel, WraithAvatar, WraithOpt
from aiphish.livewraith.server.musetalk import load_avatar, AvatarCreator

logger = logging.getLogger(__name__)


def get_session_mgr(conn: HTTPConnection) -> SessionManager:
    """
    Returns the session manager singleton.
    """
    return conn.app.state.session_mgr

SessionDep = Annotated[SessionManager, Depends(get_session_mgr)]

def get_model(request: Request) -> WraithModel:
    """
    Returns the pre-loaded model.
    """
    return request.app.state.model

ModelDep = Annotated[WraithModel, Depends(get_model)]

async def get_avatar(
    request: Request,
    wraith_id: UUID,
    tenant_id: UUID,
    org_id: UUID,
) -> WraithAvatar:
    """
    Loads the avatar files. Cache is currently unbounded. Need to revise in future with cleanup.
    """
    cache: dict[UUID, WraithAvatar] = request.app.state.avatars
    lock: asyncio.Lock = request.app.state.avatar_lock
    cfg = request.app.state.cfg
    avatar_path = cfg.AVATAR_FOLDER
    
    async with lock:
        if wraith_id in cache:
            return cache[wraith_id]
        try:
            cache[wraith_id] = await asyncio.to_thread(
                load_avatar, wraith_id, tenant_id, org_id, avatar_path
            )
        except FileNotFoundError as e:
            logger.warning("avatar not found: %s (%s)", wraith_id, e)
            raise HTTPException(status_code=404, detail=f"avatar not found: {wraith_id}") from e
        
    return cache[wraith_id]

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

