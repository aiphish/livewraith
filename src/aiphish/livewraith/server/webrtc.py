import asyncio
from dataclasses import dataclass
import logging
from uuid import UUID, uuid4

from pydantic import BaseModel

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceServer, RTCConfiguration

from aiphish.livewraith.wraithmuse.wraithoutput import WraithOutput
from aiphish.livewraith.wraithmuse.wraithstream import WraithPipeline
from aiphish.livewraith.wraithmuse.wraithmuse_types import WraithAvatar, WraithModel, WraithOpt


logger = logging.getLogger(__name__)

class OfferRequest(BaseModel):
    """
    Format for requesting an offer:
    """
    sdp: str
    type: str


@dataclass
class OfferResult:
    """
    The response from the offer request.
    """
    sdp: str
    type: str
    pipeline: WraithPipeline
    peer_id: UUID
    peer_conn: RTCPeerConnection

async def rtc_offer(
    offer_req: OfferRequest,
    model: WraithModel,
    avatar: WraithAvatar,
    opt: WraithOpt,
    stun: str | list[str] | None = None,
) -> OfferResult:
    """
    Recieves the clients SDP and returns an RTC signaling answer.
    """

    offer = RTCSessionDescription(sdp=offer_req.sdp, type=offer_req.type)

    if stun:
        ice_server = RTCIceServer(urls=stun)
        pc_cfg = RTCConfiguration(iceServers=[ice_server])
    else:
        pc_cfg = None

    pc = RTCPeerConnection(configuration=pc_cfg)

    pc_id = uuid4()

    def log_info(msg, *args):
        logger.info(f"PeerConnection({pc_id}): " + msg, *args)

    await pc.setRemoteDescription(offer)

    loop = asyncio.get_running_loop()
    output = WraithOutput(loop=loop)
    
    pc.addTrack(output.audio)
    pc.addTrack(output.video)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        log_info(f"Connection state: {pc.connectionState}")
        if pc.connectionState == "failed":
            await pc.close()
    
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    
    pipeline = WraithPipeline(
        model=model,
        avatar=avatar,
        opt=opt,
        output=output
    )

    return OfferResult(
        sdp=pc.localDescription.sdp,
        type=pc.localDescription.type,
        pipeline=pipeline,
        peer_id=pc_id,
        peer_conn=pc
    )
