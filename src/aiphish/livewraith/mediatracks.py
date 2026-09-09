
import asyncio
import fractions
import time

from aiortc import MediaStreamTrack, MediaStreamError
import numpy as np

AUDIO_PTIME = 0.020  # 20ms audio packetization
VIDEO_CLOCK_RATE = 90000
VIDEO_PTIME = 1 / 30  # 30fps
VIDEO_TIME_BASE = fractions.Fraction(1, VIDEO_CLOCK_RATE)


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

class WraithAudioTrack(MediaStreamTrack):
    """
    The webRTC audio output. 
    This is a passthrough of the TTS input.
    """

    kind = "audio"
    _start: float
    _timestamp: int

    def __init__(self, ):
        super().__init__()
        self._tts_queue = asyncio.Queue()

    async def recv(self):
        """
        Recieves the next audio frame from the queue and returns it to the audio track.
        """

        if self.readyState != "live":
            raise MediaStreamError

        frame = await self._tts_queue.get()
        samples = frame.samples
        sample_rate = frame.sample_rate

        if hasattr(self, "_timestamp"):
            self._timestamp += samples
            wait = self._start + (self._timestamp / sample_rate) - time.time()
            if wait > 0:
                await asyncio.sleep(wait)
        else:
            self._start = time.time()
            self._timestamp = 0

        frame.pts = self._timestamp
        frame.time_base = fractions.Fraction(1, sample_rate)

        return frame 

class WraithVideoTrack(MediaStreamTrack):
    """
    The webrtc video output.
    Takes in data from the tts queue, generates the lipsync video frames
    and outputs them to the track.
    """
    kind = "video"
    _start: float
    _timestamp: int

    def __init__(self, ):
        super().__init__()
        self._tts_queue = asyncio.Queue() # Must be pcm_16000, 1ch
        self._reassembler = SampleReassembler()
    
    async def recv(self):
        """
        Recieves the next tts audio frame from the queue and generates the video frames.
        """
        frame = await self._tts_queue.get()
        samples = frame.samples
        sample_rate = frame.sample_rate
        
        if hasattr(self, "_timestamp"):
            self._timestamp += samples
            wait = self._start + (self._timestamp / sample_rate) - time.time()
            if wait > 0:
                await asyncio.sleep(wait)
        else:
            self._start = time.time()
            self._timestamp = 0

        frame.pts = self._timestamp
        frame.time_base = fractions.Fraction(1, sample_rate)

        x_i16 = self._reassembler.push(frame)
        x_f32 = x_i16.astype(np.float32) / 32768.0




