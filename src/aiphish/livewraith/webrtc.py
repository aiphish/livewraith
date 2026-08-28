from dataclasses import dataclass
import logging
from uuid import UUID, uuid4

from pydantic import BaseModel

from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription

logger = logging.getLogger(__name__)

class OfferRequest(BaseModel):
    """
    Format for requesting an offer:
    """
    sdp: str
    type: str


@dataclass
class OfferResult:
    sdp: str
    type: str
    audio_track: TTSStream
    video_track: WraithStream
    peer_id: UUID
    peer_conn: RTCPeerConnection

class RTCManager:
    """
    Manages the WebRTC connections. Singleton that persists across sessions.
    """

    async def __init__(self, cfg):
        self._cfg = cfg

    async def offer(
        self,
        offer: OfferRequest
    ) -> OfferResult:
        """
        Recieves the clients SDP offer and returns an RTC signaling answer.
        """

        offer = RTCSessionDescription(sdp=offer.sdp, type=offer.type)

        ice_server = RTCIceServer(urls=self._cfg.stun)

        pc = RTCPeerConnection(
            configuration=RTCConfiguration(iceServers=[ice_server])
        )

        pc_id = uuid4()

        def log_info(msg, *args):
            logger.info(f"PeerConnection({pc_id}): " + msg, *args)

        await pc.setRemoteDescription(offer)

        videostream = WraithStream()
        audiostream = TTSStream()
    
        pc.addTrack(audiostream)
        pc.addTrack(videostream)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            log_info(f"Connection state: {pc.connectionState}")
            if pc.connectionState == "failed":
                await pc.close()
        
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return OfferResult(
            sdp=pc.localDescription.sdp,
            type=pc.localDescription.type,
            video_track=videostream,
            audio_track=audiostream,
            peer_id=pc_id,
            peer_conn=pc
        )
