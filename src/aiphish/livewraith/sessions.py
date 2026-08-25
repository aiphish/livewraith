
from uuid import UUID
from pydantic import BaseModel

class WraithSession(BaseModel):
    """
    An active inference session that's used to house the required
    sub-classes.
    """

    rtc_connection: 

    tenant_id: UUID
    org_id: UUID
    


class SessionManager:
    """
    Manages sessions across requests. Required to link webRTC setup with
    webRTC connection and websocket TTS connections.
    """

    def __init__(
        self,
    ) -> None:
        self._sessions: dict[UUID, WraithSession] = {}

    def new_session(self):


    def get_session()


    def close_session(self):


    def get_session
