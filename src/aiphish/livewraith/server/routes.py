import asyncio
from uuid import UUID, uuid4
import logging
import json
import os
from secrets import token_urlsafe
from pathlib import Path

import aiofiles
from fastapi import (
    APIRouter,
    Depends,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
    UploadFile
)

from aiphish.livewraith.server.auth import verify_api_key, APIKeyDep
from aiphish.livewraith.server.sessions import SessionNotFoundError
from aiphish.livewraith.server.dependency import (
    SessionDep,
    ModelDep,
    AvatarDep,
    OptDep,
    CreatorDep,
    ConfigDep,
)
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
            offer_result.pipeline.stop()
            session_manager.remove_session(offer_result.peer_id)
    
    offer_result.pipeline.start()
    return {"sdp": offer_result.sdp, "type": offer_result.type}

@router.post("/wraith/create", status_code=status.HTTP_202_CREATED)
async def create_wraith(
    creator: CreatorDep,
    api_key_hash: APIKeyDep,
    cfg: ConfigDep,
    video: UploadFile,
    tenant_id: UUID | None = None,
    org_id: UUID | None = None,
) -> dict[str, UUID]:
    """
    Endpoint to create a new wraith. Returns ref id for the wraith.
    """


    wraith_id = uuid4()
    tempfile = token_urlsafe(32)
    temp_video_path = os.path.join(cfg.TEMP_FOLDER, tempfile)

    chunk_size = 1024*1024
    async with aiofiles.open(temp_video_path, "wb") as f:
        while chunk := await video.read(chunk_size):
            await f.write(chunk)
    
    bbox_shift = cfg.BBOX_SHIFT
    extra_margin = cfg.EXTRA_MARGIN
    parsing_mode = cfg.PARSING_MODE

    async_thread = asyncio.to_thread(
        creator.generate_avatar,
        avatar_id=wraith_id,
        videofile_path=temp_video_path,
        tenant_id=tenant_id,
        org_id=org_id,
        save_path=cfg.AVATAR_FOLDER,
        bbox_shift=bbox_shift,
        extra_margin=extra_margin,
        parsing_mode=parsing_mode
    )
    task = asyncio.create_task(async_thread)
    creator.tasks.add(task)

    def _on_done(t: asyncio.Task) -> None:
        creator.tasks.discard(t)
        Path(temp_video_path).unlink(missing_ok=True)
        if not t.cancelled() and (exc := t.exception()):
            logger.error("Wraith generation failed: %s", wraith_id, exc_info=exc)

    task.add_done_callback(_on_done)

    return {"wraith_id": wraith_id}

@router.websocket("/wraith/stream")  
async def wraith_stream(
    ws: WebSocket,
    session_manager: SessionDep,
    _: APIKeyDep,
    pc_id: UUID,
    tenant_id: UUID | None = None,
    org_id: UUID | None = None
):
    """
    Takes in a stream of TTS audio output. Caller must
    have already setup the webRTC connection through the offer endpoint.
    """
    try:
        session = session_manager.get_session(
            session_id=pc_id,
            tenant_id=tenant_id,
            org_id=org_id
        )
    except SessionNotFoundError as e:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="WebRTC Session not found. Use the /offer endpoint to start a sessionn.") from e
    await ws.accept()
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
                    session.pipeline.flush_talk()
    except WebSocketDisconnect:
        try:
            session.pipeline.stop()
            await ws.close(code=1000, reason=None)
        except Exception:
            pass

@router.get("/wraith/status")
async def get_wraith_status():
    """
    Polls the status of the wraith creation process to determine if a wraith is ready for
    streaming.
    """
    return 200