
import asyncio
from uuid import UUID
import logging
from dataclasses import dataclass

from aiortc import RTCPeerConnection

from aiphish.livewraith.wraithmuse.wraithstream import WraithPipeline

logger = logging.getLogger(__name__)

@dataclass
class WraithSession:
    """
    An active inference session that's used to house the required
    sub-classes.
    """

    pipeline: WraithPipeline
    avatar_id: str
    peer_id: UUID
    peer_conn: RTCPeerConnection
    key_hash: str
    tenant_id: UUID | None
    org_id: UUID | None

class SessionNotFoundError(Exception):
    """
    Raised if invalid session requested.
    """

class SessionManager:
    """
    Manages sessions across requests. Required to link webRTC setup with
    webRTC connection and websocket TTS connections.
    """

    def __init__(self) -> None:
        self._sessions: dict[UUID, WraithSession] = {}

    def new_session(self, info_obj: dict):
        """
        Created a new inference session.
        """
        new_session = WraithSession(
            avatar_id=info_obj['avatar_id'],
            peer_id=info_obj['id'],
            peer_conn=info_obj['peer_conn'],
            pipeline=info_obj['pipeline'],
            key_hash=info_obj['key_hash'],
            tenant_id=info_obj['tenant_id'],
            org_id=info_obj['org_id'],
        )
        self._sessions[info_obj["id"]] = new_session

    def get_session(
        self,
        session_id: str,
        tenant_id: UUID | None = None,
        org_id: UUID | None = None,
    ) -> WraithSession:
        """
        Returns the session object for a given session ID. Validates the tenant and org.
        """

        try:
            session = self._sessions[session_id]
        except KeyError:
            raise SessionNotFoundError(session_id) from None
        
        if session.tenant_id != tenant_id or session.org_id != org_id:
            raise SessionNotFoundError(session_id)
        
        return session

    def remove_session(self, session_id) -> None:
        """
        Removes a WraithSession from the active session registry.
        RTC session is closed by the listener registered during the offer.
        """

        self._sessions.pop(session_id, None)

    async def close_all(self) -> None:
        """
        Closes all sessions if not already closed.
        Used for app shutdown.
        """
        results = await asyncio.gather(
            *(session.peer_conn.close() for session in self._sessions.values()),
            return_exceptions=True
        )
        for session, result in zip(self._sessions, results):
            if isinstance(result, Exception):
                logger.warning("Failed to close peer connection %s", session.peer_id, exc_info=result)
     
        
