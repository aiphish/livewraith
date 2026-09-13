
import asyncio
import fractions
import time

from aiortc import MediaStreamTrack, MediaStreamError
import numpy as np

class SampleReassembler:
    """
    Used to ensure the streamed data samples are 2 bytes. If oversized or undersized the
    incomplete data is stored and combined with the next sample, with excess being stored for
    the sample after that and so on.
    """
    def __init__(self):
        self._leftover = b""

    def push(self, chunk: bytes) -> np.ndarray:
        data = self._leftover + chunk
        usable_len = len(data) - (len(data) % 2)
        self._leftover = data[usable_len:]
        return np.frombuffer(data[:usable_len], dtype='<i2')

VIDEO_CLOCK_RATE = 90000
VIDEO_PTIME = 1 / 25
AUDIO_CLOCK_RATE = 16000
AUDIO_PTIME = 0.020

class WraithTrack(MediaStreamTrack):
    """
    A media stream for the WebRTC connection.
    """
    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self._queue = asyncio.Queue()
        self._start: float | None = None
        self._timestamp: int = 0
    
    async def recv(self):
        if self.readyState != "live":
            raise MediaStreamError

        frame, _ = await self._queue.get()

        if self.kind == "video":
            rate, ptime = VIDEO_CLOCK_RATE, VIDEO_PTIME
        else:
            rate, ptime = AUDIO_CLOCK_RATE, AUDIO_PTIME

        if hasattr(self, "_timestamp"):
            self._timestamp += int(ptime * rate)
            wait = self._start + (self._timestamp / rate) - time.time()
            if wait > 0:
                await asyncio.sleep(wait)
        else:
            self._start = time.time()
            self._timestamp = 0

        frame.pts = self._timestamp
        frame.time_base = fractions.Fraction(1, rate)
        return frame

