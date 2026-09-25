
import hashlib
import secrets

import logging
from typing import Annotated

from fastapi import Depends, Request, HTTPException, status, WebSocket, WebSocketException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

logger = logging.getLogger(__name__)

def verify_api_key(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> str:
    """
    Validates the api key that has been provided against the set of key hashes.
    Injected as a dependancy to all non-websocket routes. New keys require server restart.

    Returns key hash.
    """
    api_key = credentials.credentials
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    valid_key_hashes = request.app.state.api_key_hashes

    if not any(secrets.compare_digest(key_hash, k) for k in valid_key_hashes):
        logger.warning("API key does not match valid hash list.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key Provided"
        )

    return key_hash

APIKeyDep = Annotated[str, Depends(verify_api_key)]

async def verify_api_key_ws(ws: WebSocket) -> str:
    """
    Validates the api key that has been provided against the set of key hashes.
    Injected as a dependancy to all websocket routes. New keys require server restart.

    Returns key hash.
    """
    logger.debug(dict(ws.headers))
    auth = ws.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid API key.",
        )

    token = auth.removeprefix("Bearer ")
    key_hash = hashlib.sha256(token.encode()).hexdigest()
    valid_key_hashes = ws.app.state.api_key_hashes
    if not any(secrets.compare_digest(key_hash, k) for k in valid_key_hashes):
        logger.warning("API key does not match valid hash list.")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid API key.",
        )

    return key_hash

WSAPIKeyDep = Annotated[str, Depends(verify_api_key_ws)]