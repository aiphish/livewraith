

import logging
import json
from fastapi import APIRouter, Depends, status

from aiphish.livewraith.auth import verify_api_key, APIKeyDep

logger = logging.getLogger(__name__)

router = APIRouter(
    dependencies=[
        Depends(verify_api_key)
    ]
)

@router.post("/offer")
async def rtc_offer(
    session_manager: SessionManagerDep,
    rtc_manager: RTCManagerDep,
    api_key_hash: APIKeyDep,
    offer_request: OfferRequest,
):
    """
    Initiates the webRTC connection
    """
    offer_result = await rtc_manager.offer(offer_request)

    session_manager.add(
        {
            "id": offer_result.peer_id,
            "key_hash": api_key_hash,
            "audio": offer_result.audio_track,
            "video": offer_result.video_track,
            "peer_connection": offer_result.peer_conn
        }
    )

    pc = offer_result.peer_conn
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        if pc.connectionState == "failed":
            session_manager.remove(offer_result.peer_id)

    return {"sdp": offer_result.sdp, "type": offer_result.type}

