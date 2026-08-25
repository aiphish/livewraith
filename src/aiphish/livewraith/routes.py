

import logging

from fastapi import APIRouter, Depends, status

from aiphish.livewraith.auth import verify_api_key, APIKeyDep

logger = logging.getLogger(__name__)

router = APIRouter(
    dependencies=[
        Depends(verify_api_key)
    ]
)

@router.post("/offer", response_model=)
async def rtc_offer(
    session_manager: SessionManager,
    api_key_hash: APIKeyDep,
):
    """
    Initiates the webRTC connection
    """

    # Create Session
    # Assign RTC session

