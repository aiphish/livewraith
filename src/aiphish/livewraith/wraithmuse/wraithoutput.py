
import asyncio
import numpy as np
from av import AudioFrame, VideoFrame
from aiphish.livewraith.server.mediatracks import WraithTrack

class WraithOutput:
    """
    Holds the output WebRTC tracks and sends data to them.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._audio_track = WraithTrack("video")
        self._video_track = WraithTrack("audio")
        self._loop = loop
        
    def push_video_frame(self, bgr: np.ndarray) -> None:
        """
        Pushes a video frame to the webRTC conn
        """
        frame = VideoFrame.from_ndarray(bgr, format="bgr24")
        asyncio.run_coroutine_threadsafe(
            self._video_track._queue.put((frame, None)), self._loop)

    def push_audio_frame(self, pcm_i16: np.ndarray, userdata: dict) -> None:
        """
        Pushes an audio frame to the webRTC conn.
        """
        af = AudioFrame(format='s16', layout='mono', samples=pcm_i16.shape[0])
        af.planes[0].update(pcm_i16.tobytes())
        af.sample_rate = 16000
        asyncio.run_coroutine_threadsafe(
            self._audio_track._queue.put((af, userdata)), self._loop)

    def get_buffer_size(self) -> int:
        """
        Returns the buffer size of the video track.
        """
        return self._video_track._queue.qsize()
    
    @property
    def audio(self) -> WraithTrack:
        """
        Exposes the audio track - WraithTrack type inherits from aiortc.MediaTrack
        """
        return self._audio_track
    
    @property
    def video(self) -> WraithTrack:
        """
        Exposes the video track - WraithTrack type inherits from aiortc.MediaTrack
        """
        return self._video_track