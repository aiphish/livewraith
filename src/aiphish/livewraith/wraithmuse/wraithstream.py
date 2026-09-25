
import time
import queue
from threading import Thread, Event
import json
import logging
from queue import Queue

import torch
import numpy as np
from numpy.typing import NDArray
import cv2

from aiphish.livewraith.wraithmuse.utils import mirror_index, SampleReassembler, AudioFrameData
from aiphish.livewraith.wraithmuse.whisperasr import WhisperASR
from aiphish.livewraith.wraithmuse.wraithmuse_types import WraithAvatar, WraithModel, WraithOpt
from aiphish.livewraith.wraithmuse.wraithoutput import WraithOutput

logger = logging.getLogger(__name__)

class WraithPipeline:
    """
    The primary orchestration class that owns frame generation and 
    the two media tracks.
    """
    @torch.no_grad()
    def __init__(
        self, 
        model: WraithModel,
        avatar: WraithAvatar,
        opt: WraithOpt,
        output: WraithOutput
        
    ) -> None:

        self.vae, self.unet, self.pe, self.timesteps, self.audio_processor = model
        self.frame_list_cycle,self.mask_list_cycle,self.coord_list_cycle,self.mask_coords_list_cycle, self.input_latent_list_cycle = avatar
        self.opt = opt
        self.chunk = 16000 // opt.fps          # 320
        self.batch_size = opt.batch_size
        self.output = output
        self.speaking = False

        self.asr = WhisperASR(opt, self.audio_processor)
        self.asr.warm_up()

        self._tail = np.zeros(0, dtype=np.float32)
        self.res_frame_queue = Queue(opt.batch_size * 2)
        self.render_event = Event()
        
        self.quit_event = Event()

        self._reassembler = SampleReassembler()

        self.msgqueues = []
    
    def put_audio_frame(self, audio_chunk:NDArray[np.float32], datainfo:dict={}): # 16khz 20ms pcm
        self.asr.put_audio_frame(audio_chunk, datainfo)

    def push_pcm(self, data: bytes, eventpoint=None):
        """Called from the WS handler. Never sleeps."""
        frame = self._reassembler.push(data)
        pcm = frame.astype(np.float32) / 32767
        buf = np.concatenate([self._tail, pcm])
        n = (len(buf) // self.chunk) * self.chunk
        for i in range(0, n, self.chunk):
            self.put_audio_frame(buf[i:i+self.chunk],
                                 eventpoint if i == 0 else None)
        self._tail = buf[n:]

    def end_utterance(self, text=None):
        if len(self._tail):
            pad = np.zeros(self.chunk - len(self._tail), dtype=np.float32)
            self.put_audio_frame(np.concatenate([self._tail, pad]))
            self._tail = np.zeros(0, dtype=np.float32)
        self.put_audio_frame(np.zeros(self.chunk, np.float32),
                             {'status': 'end', 'text': text})

    def start(self):
        self.quit_event = Event()
        Thread(target=self.render, daemon=True).start()

    def stop(self):
        self.quit_event.set()
    
    def flush_talk(self):
        self.asr.flush_talk()

    def is_speaking(self) -> bool:
        return self.speaking

    def add_msgqueue(self, msgqueue):
        self.msgqueues.append(msgqueue)

    def send_msg(self, msg):
        for q in self.msgqueues:
            q.put(msg)

    def notify(self, eventpoint:dict):
        if eventpoint and eventpoint.get('status'):
            logger.info("notify:%s", eventpoint)
            self.send_msg(json.dumps(eventpoint))
    
    def get_avatar_length(self):
        if hasattr(self, 'frame_list_cycle'):
            return len(self.frame_list_cycle)
        return 1
    
    def inference(self, quit_event):
        length = self.get_avatar_length()
        index = 0
        count = 0
        counttime = 0
        last_speaking = False

        logger.info('start inference')
        while not quit_event.is_set():
            audiofeat_batch = []
            try:
                audiofeat_batch = self.asr.feat_queue.get(block=True, timeout=1)
            except queue.Empty:
                continue
                
            is_all_silence = True
            audio_frames: list[AudioFrameData] = []
            for _ in range(self.batch_size * 2):
                audioframe:AudioFrameData = self.asr.output_queue.get()
                if audioframe.type == 0:
                    is_all_silence = False               
                audio_frames.append(audioframe)

            current_speaking = not is_all_silence

            if is_all_silence:
                for i in range(self.batch_size):
                    idx = mirror_index(length, index)
                    self.res_frame_queue.put((None, audio_frames[i*2:i*2+2], idx))
                    index = index + 1
            else:
                t = time.perf_counter()

                pred = self.inference_batch(index, audiofeat_batch)

                counttime += (time.perf_counter() - t)
                count += self.batch_size
                if count >= 100:
                    logger.info("------actual avg infer fps: %s ", (count/counttime))
                    count = 0
                    counttime = 0
                for i, res_frame in enumerate(pred):
                    self.res_frame_queue.put((res_frame, audio_frames[i*2:i*2+2], mirror_index(length, index)))
                    index = index + 1
                    
            if current_speaking != last_speaking:
                last_speaking_state = 'Speaking' if last_speaking else 'Muted'
                current_speaking_state = 'Speaking' if current_speaking else 'Muted'
                logger.info("inference state switching： %s → %s", last_speaking_state, current_speaking_state)
                last_speaking = current_speaking         
        logger.info('baseavatar inference thread stop')
    
    def process_frames(self,quit_event):
        enable_transition = False # Smoothing around mouth
        
        _last_speaking = False
        _transition_start = time.time()
        if enable_transition:
            _transition_duration = 0.1
            _last_silent_frame = None
            _last_speaking_frame = None

        self.output.start()
        
        while not quit_event.is_set():
            try:
                audio_frames: list[AudioFrameData]
                res_frame,audio_frames,idx = self.res_frame_queue.get(block=True, timeout=1)
            except queue.Empty:
                continue
            
            current_speaking = not (audio_frames[0].type!=0 and audio_frames[1].type!=0)
            if current_speaking != _last_speaking:
                last_speaking_state = 'Speaking' if _last_speaking else 'Muted'
                current_speaking_state = 'Speaking' if current_speaking else 'Muted'
                logger.info("State transition： %s → %s", last_speaking_state, current_speaking_state)
                _transition_start = time.time()
            _last_speaking = current_speaking

            if audio_frames[0].type!=0 and audio_frames[1].type!=0:
                self.speaking = False
                target_frame = self.frame_list_cycle[idx]
                
                if enable_transition: 
                    # Speech to silence transition smoothing
                    if time.time() - _transition_start < _transition_duration and _last_speaking_frame is not None:
                        alpha = min(1.0, (time.time() - _transition_start) / _transition_duration)
                        combine_frame = cv2.addWeighted(_last_speaking_frame, 1-alpha, target_frame, alpha, 0)
                    else:
                        combine_frame = target_frame
                    _last_silent_frame = combine_frame.copy()
                else:
                    combine_frame = target_frame
            else:
                self.speaking = True
                try:
                    current_frame = self.paste_back_frame(res_frame,idx)
                except Exception as e:
                    logger.warning("paste_back_frame error: %s ", e)
                    continue
                if enable_transition:
                    # Silence to speech transition smoothing
                    if time.time() - _transition_start < _transition_duration and _last_silent_frame is not None:
                        alpha = min(1.0, (time.time() - _transition_start) / _transition_duration)
                        combine_frame = cv2.addWeighted(_last_silent_frame, 1-alpha, current_frame, alpha, 0)
                    else:
                        combine_frame = current_frame
                    _last_speaking_frame = combine_frame.copy()
                else:
                    combine_frame = current_frame

            self.output.push_video_frame(combine_frame)

            for audio_frame in audio_frames:
                #frame,type,eventpoint = audio_frame
                frame = (audio_frame.data * 32767).astype(np.int16)

                self.output.push_audio_frame(frame, audio_frame.userdata)

        self.output.stop()
        logger.info('baseavatar process_frames thread stop')
    
    def render(self,quit_event):
        self.quit_event = quit_event

        infer_quit_event = Event()
        infer_thread = Thread(target=self.inference, args=(infer_quit_event,))
        infer_thread.start()
        
        process_quit_event = Event()
        process_thread = Thread(target=self.process_frames, args=(process_quit_event,))
        process_thread.start()

        while not quit_event.is_set(): 
            t = time.perf_counter()
            self.asr.run_step()

            buffer_size = self.output.get_buffer_size() if hasattr(self.output, 'get_buffer_size') else 0
            if buffer_size >= 5:
                logger.debug('sleep qsize=%d', buffer_size)
                time.sleep(0.04 * buffer_size * 0.8)
        logger.info('baseavatar render thread stop')

        infer_quit_event.set()
        infer_thread.join()

        process_quit_event.set()
        process_thread.join()
    
    def get_image_blending(
        self,
        image,
        face,
        face_box,
        mask_array,
        crop_box
    ):
        body = image
        x, y, x1, y1 = face_box
        x_s, y_s, x_e, y_e = crop_box
        face_large = body[y_s:y_e, x_s:x_e].copy()
        face_large[y-y_s:y1-y_s, x-x_s:x1-x_s]=face

        mask_image = cv2.cvtColor(mask_array,cv2.COLOR_BGR2GRAY)
        mask_image = (mask_image/255).astype(np.float32)
        
        body[y_s:y_e, x_s:x_e] = cv2.blendLinear(face_large,body[y_s:y_e, x_s:x_e],mask_image,1-mask_image)

        return body
    
    @torch.no_grad()
    def inference_batch(self, index, audiofeat_batch):
        # Index refers to the index of the current avatar
        # Returns the inference results for each batch. Batch size is determined by
        # self.batch_size.
        length = len(self.input_latent_list_cycle)
        whisper_batch = np.stack(audiofeat_batch)
        latent_batch = []
        for i in range(self.batch_size):
            idx = mirror_index(length, index + i)
            latent = self.input_latent_list_cycle[idx]
            latent_batch.append(latent)
        latent_batch = torch.cat(latent_batch, dim=0)
        
        audio_feature_batch = torch.from_numpy(whisper_batch)
        audio_feature_batch = audio_feature_batch.to(device=self.unet.device,
                                                        dtype=self.unet.model.dtype)
        audio_feature_batch = self.pe(audio_feature_batch)
        latent_batch = latent_batch.to(dtype=self.unet.model.dtype)

        pred_latents = self.unet.model(latent_batch, 
                                    self.timesteps, 
                                    encoder_hidden_states=audio_feature_batch).sample
        pred = self.vae.decode_latents(pred_latents)
        return pred

    def paste_back_frame(self,pred_frame,idx:int):
        bbox = self.coord_list_cycle[idx]
        ori_frame = self.frame_list_cycle[idx].copy()
        x1, y1, x2, y2 = bbox

        res_frame = cv2.resize(pred_frame.astype(np.uint8),(x2-x1,y2-y1)) # pylint: disable=no-member
        mask = self.mask_list_cycle[idx]
        mask_crop_box = self.mask_coords_list_cycle[idx]

        combine_frame = self.get_image_blending(ori_frame,res_frame,bbox,mask,mask_crop_box)
        return combine_frame

    
