import time
import queue
from queue import Queue
import numpy as np
from numpy.typing import NDArray

from aiphish.livewraith.wraithmuse.utils import AudioFrameData
from aiphish.livewraith.wraithmuse.wraithmuse_types import WraithOpt
from aiphish.livewraith.musetalk.whisper.audio2feature import Audio2Feature

class WhisperASR:
    """
    Streaming adapter for MuseTalk.
    """

    def __init__(self, opt: WraithOpt, audio_processor: Audio2Feature):
        self.opt = opt

        self.fps = opt.fps # 20 ms per frame
        self.sample_rate = 16000
        self.chunk = self.sample_rate // (opt.fps*2) # 320 samples per chunk (20ms * 16000 / 1000)
        self.queue:Queue[AudioFrameData] = Queue()
        self.output_queue:Queue[AudioFrameData] = Queue()

        self.batch_size = opt.batch_size

        self.frames: list[NDArray[np.float32]] = []
        self.stride_left_size = opt.stride_left_size
        self.stride_right_size = opt.stride_right_size
        self.feat_queue = Queue(maxsize=2)

        self.audio_processor = audio_processor

    def flush_talk(self):
        self.queue.queue.clear()
    
    def put_audio_frame(self,audio_chunk:NDArray[np.float32],datainfo:dict): #16khz 20ms pcm
        self.queue.put(AudioFrameData(data=audio_chunk,type=0,userdata=datainfo))
    
    def get_audio_frame(self)->AudioFrameData:        
        try:
            return self.queue.get(block=True,timeout=0.01)
        except queue.Empty:
            frame = np.zeros(self.chunk, dtype=np.float32)
            return AudioFrameData(data=frame, type=1, userdata={})
    
    def get_audio_out(self)->AudioFrameData: 
        return self.output_queue.get()
    
    def warm_up(self):
        for _ in range(self.stride_left_size + self.stride_right_size):
            audio_frame=self.get_audio_frame()
            self.frames.append(audio_frame.data)
            self.output_queue.put(audio_frame)
        for _ in range(self.stride_left_size):
            self.output_queue.get()
    
    def run_step(self):
        """
        Consumes one batch of audio, emits its whisper conditioning.

        Called in a loop by the render thread. Each call:
        1.  Pulls ``batch_size * 2`` audio frames (two 20ms frames per video
            frame) via ``get_audio_frame``, which creates silence when the
            input queue is empty so the pipeline never stalls.
        2.  Forks each frame: the raw samples join the sliding window for
            whisper; the full ``AudioFrameData`` goes to ``output_queue``, where
            it waits to be re-paired with the video frame it produces. This
            pairing is what keeps the audio and video tracks in sync — the two
            queues are drained in the same 1:``batch_size*2`` ratio downstream.
        3.  Runs the whisper *encoder* (no decoder, no transcription) over the
            window and slices the result into one conditioning window per video
            frame. Windows are cross-attention input to the UNet.
        4.  Retains ``stride_left_size + stride_right_size`` frames as context
            for the next call.

        The window spans ``stride_left_size`` frames of past context, the
        ``batch_size * 2`` new frames, and ``stride_right_size`` frames of
        future context. Only the middle range is rendered this call; the right
        stride exists because lip shape depends on the *upcoming* phoneme
        (coarticulation), which imposes a ``stride_right_size * 20ms``
        floor on end-to-end latency.

        Blocks on ``feat_queue.put`` when the GPU is behind, which propagates
        backpressure to the audio input queue rather than letting work pile up.
        """
        start_time = time.time()
        for _ in range(self.batch_size*2):
            audio_frame = self.get_audio_frame()
            self.frames.append(audio_frame.data)
            self.output_queue.put(audio_frame)
        
        if len(self.frames) <= self.stride_left_size + self.stride_right_size:
            return
        
        inputs = np.concatenate(self.frames) # [N * chunk]
        whisper_feature = self.audio_processor.audio2feat(inputs)
        whisper_chunks = self._feature2chunks(feature_array=whisper_feature,batch_size=self.batch_size,
                                              audio_feat_win = [2,3],start=self.stride_left_size/2,
                                              feature_idx_multiplier=2)
        self.feat_queue.put(whisper_chunks)
        # discard the old part to save memory
        self.frames = self.frames[-(self.stride_left_size + self.stride_right_size):]

    def get_next_feat(self,block,timeout):        
        return self.feat_queue.get(block,timeout)
    
    def _get_sliced_feature(self, feature_array, 
                        vid_idx,  
                        audio_feat_win,  
                        feature_idx_multiplier=1.0):
        """
        Get sliced features based on a given index
        :param feature_array: 
        :param vid_idx: video frames are numbered within a batch
        :param audio_feat_win: audio feature window size, in unites of video frames
        :param feature_idx_multiplier: Multiplier used to convert video frame indices to feature indices, typically (feature extraction width / video frame rate).
        :return: 
        """
        length = feature_array.shape[0]
        selected_feature = []
        selected_idx = []
        
        center_idx = int(vid_idx * feature_idx_multiplier) 
        left = int(center_idx - audio_feat_win[0]*feature_idx_multiplier)
        right = int(center_idx + audio_feat_win[1]*feature_idx_multiplier)
        
        for idx in range(left,right):
            idx = max(0, idx)
            idx = min(length-1, idx)
            x = feature_array[idx]
            selected_feature.append(x)
            selected_idx.append(idx)
        
        return np.asarray(selected_feature),selected_idx
    
    def _feature2chunks(self,feature_array,batch_size,audio_feat_win=[8,8],start=0,feature_idx_multiplier=1.0):
        """
        :param feature_array: 
        :param batch_size:
        :param audio_feat_win: audio feature window size, in unites of video frames
        :param start: start frame index, typically stride_left_size/2
        :param feature_idx_multiplier: Multiplier used to convert video frame indices to feature indices.
        :return: 
        """
        feature_chunks = []
        for i in range(batch_size):
            selected_feature,selected_idx = self._get_sliced_feature(
                feature_array=feature_array, vid_idx=i+start,
                audio_feat_win=audio_feat_win, feature_idx_multiplier=feature_idx_multiplier)
            feature_chunks.append(selected_feature)
        return feature_chunks
    
    def _feature2chunks(self,feature_array,batch_size,audio_feat_win=[8,8],start=0,feature_idx_multiplier=1.0):
        """
        :param feature_array: 
        :param batch_size:
        :param audio_feat_win: audio feature window size, in unites of video frames
        :param start: start frame index, typically stride_left_size/2
        :param feature_idx_multiplier: Multiplier used to convert video frame indices to feature indices.
        :return: 
        """
        feature_chunks = []
        for i in range(batch_size):
            selected_feature,selected_idx = self._get_sliced_feature(
                feature_array=feature_array, vid_idx=i+start,
                audio_feat_win=audio_feat_win, feature_idx_multiplier=feature_idx_multiplier)
            feature_chunks.append(selected_feature.reshape(-1, 384))
        return feature_chunks
    

