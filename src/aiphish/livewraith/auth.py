
import hashlib, secrets
import logging
from typing import Annotated

from fastapi import Depends, Request, HTTPException, status
from fastapi.security import APIKeyHeader

header_scheme = APIKeyHeader(name="x-key")

logger = logging.getLogger(__name__)

def verify_api_key(
    request: Request,
    api_key: str = Depends(header_scheme),
) -> str:
    """
    Validates the api key that has been provided against the set of key hashes.
    Injected as a dependancy to all routes. New keys require server restart.

    Returns key hash.
    """

    try:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    except Exception:
        logger.exception("Error processing api_key hash")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key Provided"
        )

    valid_key_hashes = request.app.state.api_key_hashes

    if not any(secrets.compare_digest(key_hash, k) for k in valid_key_hashes):
        logger.warning("API key does not match valid hash list: %s", key_hash)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key Provided"
        )

    return key_hash

APIKeyDep = Annotated[str, Depends(verify_api_key)]



