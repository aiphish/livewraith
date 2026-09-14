
from uuid import UUID
import logging
import json
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from aiphish.livewraith.server.auth import verify_api_key, APIKeyDep
from aiphish.livewraith.server.dependency import SessionDep, ModelDep, AvatarDep, OptDep
from aiphish.livewraith.server.webrtc import rtc_offer, OfferRequest

logger = logging.getLogger(__name__)

router = APIRouter(
    dependencies=[
        Depends(verify_api_key)
    ]
)

@router.post("/offer")
async def create_rtc_offer(
    avatar_id: str,
    avatar: AvatarDep,
    session_manager: SessionDep,
    model: ModelDep,
    opt: OptDep,
    api_key_hash: APIKeyDep,
    offer_request: OfferRequest,
    tenant_id: UUID | None = None,
    org_id: UUID | None = None,
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
            "pipeline": offer_result.pipeline,
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
            session_manager.remove_session(offer_result.peer_id)
    
    offer_result.pipeline.start()
    return {"sdp": offer_result.sdp, "type": offer_result.type}

@router.post("/wraith/create")
async def create_wraith(

):
    """
    Endpoint to create a new wraith. Returns ref id for the wraith.
    """
    return 200

@router.websocket("/wraith/stream")  
async def wraith_stream(
    ws: WebSocket,
    session_manager: SessionDep,
    api_key_hash: APIKeyDep,
    pc_id: UUID,
    tenant_id: UUID | None = None,
    org_id: UUID | None = None
):
    """
    Takes in a stream of TTS audio output. Caller must
    have already setup the webRTC connection through the offer endpoint.
    """
    await ws.accept()
    session = session_manager.get_session(
        session_id=pc_id,
        tenant_id=tenant_id,
        org_id=org_id
    )
    try:
        while True:
            data = await ws.receive()
            if "bytes" in data:
                session.pipeline.push_pcm(data["bytes"])
            elif "text" in data:
                ctrl = json.loads(data["text"])
                if ctrl["type"] == "utterance_end":
                    session.pipeline.end_utterance(ctrl.get("text"))
                elif ctrl["type"] == "interrupt":
                    session.pipeline.flush()
    except WebSocketDisconnect:
        try:
            await ws.close(code=1000, reason=None)
        except Exception:
            pass
        pass




    return 200

@router.get("/wraith/status")
async def get_wraith_status():
    """
    Polls the status of the wraith creation process to determine if a wraith is ready for
    streaming.
    """
    return 200