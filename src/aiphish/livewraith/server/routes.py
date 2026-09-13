

import logging
import json
from fastapi import APIRouter, Depends, status

from aiphish.livewraith.server.auth import verify_api_key, APIKeyDep
from aiphish.livewraith.server.dependency import SessionDep, ModelDep, AvatarDep
from aiphish.livewraith.server.webrtc import rtc_offer, OfferRequest

logger = logging.getLogger(__name__)

router = APIRouter(
    dependencies=[
        Depends(verify_api_key)
    ]
)

@router.post("/offer")
async def rtc_offer(
    avatar_id: str,
    avatar: AvatarDep,
    session_manager: SessionDep,
    model: ModelDep,
    opt: OptDep,
    api_key_hash: APIKeyDep,
    offer_request: OfferRequest,
    tenant_id: int | None = None,
    org_id: int | None = None,
):
    """
    Initiates the webRTC connection
    """

    offer_result = await rtc_offer(
        offer_req=offer_request,
        model=model,
        avatar=avatar,
        opt=opt,
    )

    session_manager.new_session(
        {
            "id": offer_result.peer_id,
            "avatar_id": avatar_id,
            "key_hash": api_key_hash,
            "audio": offer_result.audio_track,
            "video": offer_result.video_track,
            "peer_conn": offer_result.peer_conn,
            "tenant_id": tenant_id,
            "org_id": org_id
        }
    )

    pc = offer_result.peer_conn
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        if pc.connectionState == "failed":
            await pc.close()
            session_manager.close_session(offer_result.peer_id)

    return {"sdp": offer_result.sdp, "type": offer_result.type}

@router.post("/wraith/create")
async def create_wraith(

):
    """
    Endpoint to create a new wraith. Returns ref id for the wraith.
    """
    return 200

@router.websocket("/wraith/stream")
async def stream_wraith(
    
):
    """
    Takes in a stream of TTS audio output. Caller must
    have already setup the webRTC connection through the offer endpoint.
    """

   
    async def wraith_stream(ws: WebSocket, session_manager: SessionManagerDep, peer_id: UUID, ...):
        await ws.accept()
        session = session_manager.get_session(peer_id, tenant_id, org_id)
        try:
            while True:
                msg = await ws.receive()
                if "bytes" in msg:
                    session.pipeline.push_pcm(msg["bytes"])
                elif "text" in msg:
                    ctrl = json.loads(msg["text"])
                    if ctrl["type"] == "utterance_end":
                        session.pipeline.end_utterance(ctrl.get("text"))
                    elif ctrl["type"] == "interrupt":
                        session.pipeline.flush()
        except WebSocketDisconnect:
            pass




    return 200

@router.get("wraith/status")
async def get_wraith_status():
    """
    Polls the status of the wraith creation process to determine if a wraith is ready for
    streaming.
    """
    return 200