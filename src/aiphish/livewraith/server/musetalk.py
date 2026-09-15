
import pickle
import os
import glob

import torch
from fastapi import UploadFile

from aiphish.livewraith.wraithmuse.utils import read_imgs

from aiphish.livewraith.musetalk.utils.utils import load_all_model
from aiphish.livewraith.musetalk.whisper import audio2feature as A2F

def load_model():
    """
    Pre-loads the MuseTalk models
    """
    vae, unet, pe = load_all_model()
    if torch.cuda.is_available():
        device = torch.device('cuda')
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = torch.device('mps')
    else:
        device = torch.device('cpu')
    timesteps = torch.tensor([0], device=device)
    pe = pe.half().to(device)
    vae.vae = vae.vae.half().to(device)
    unet.model = unet.model.half().to(device)
    audio_processor = A2F(model_path="./models/whisper") #pylint: disable=not-callable
    return vae, unet, pe, timesteps, audio_processor

def load_avatar(avatar_id):
    """
    Returns the saved avatar files.
    """
    avatar_path = f"./data/avatars/{avatar_id}"
    full_imgs_path = f"{avatar_path}/full_imgs" 
    coords_path = f"{avatar_path}/coords.pkl"
    latents_out_path= f"{avatar_path}/latents.pt"
    mask_out_path =f"{avatar_path}/mask"
    mask_coords_path =f"{avatar_path}/mask_coords.pkl"

    input_latent_list_cycle = torch.load(latents_out_path)
    with open(coords_path, 'rb') as f:
        coord_list_cycle = pickle.load(f)
    frame_list_cycle = None
    input_img_list = glob.glob(os.path.join(full_imgs_path, '*.[jpJP][pnPN]*[gG]'))
    input_img_list = sorted(input_img_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    frame_list_cycle = read_imgs(input_img_list)
    with open(mask_coords_path, 'rb') as f:
        mask_coords_list_cycle = pickle.load(f)
    input_mask_list = glob.glob(os.path.join(mask_out_path, '*.[jpJP][pnPN]*[gG]'))
    input_mask_list = sorted(input_mask_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    mask_list_cycle = read_imgs(input_mask_list)
    
    return frame_list_cycle,mask_list_cycle,coord_list_cycle,mask_coords_list_cycle,input_latent_list_cycle

import asyncio
import os
from uuid import uuid4, UUID
import logging
import shutil
import json
from secrets import token_urlsafe
import aiofiles
from aiphish.livewraith.musetalk.utils.preprocessing import get_landmark_and_bbox, read_imgs
from aiphish.livewraith.musetalk.utils.face_parsing import FaceParsing

logger = logging.getLogger(__name__)

class VideoError(Exception):
    """
    Error with the provided video.
    """

class AvatarCreator:
    """
    Class for handling the creation of MuseTalk Avatars and tracking progress.
    """
    def __init__(self):
        self._progress: dict[UUID, int] = {}
        self._error_reason: dict[UUID, str] = {}
        self._subprogress_percent: dict[UUID, float] = 0

        self._progress_map = {
            0: "Does not exist",
            1: "Initialized",
            2: "Frame extraction complete",
            3: "Face detection complete",
            4: "VAE encoding complete",
            5: "Masking complete"
            

        }

    async def generate_avatar(
        self,
        media_file: UploadFile,
        tenant_id: UUID,
        org_id: UUID,
        save_path: str = "/aiphish/livewraith/avatars",
        reprocess_avatar_id: UUID | None = None,
        bbox_shift: int = 0,
        extra_margin: int = 10,
        parsing_mode='jaw',
        version='v15', # required, param for visibility

    ) -> UUID:
        """
        Generates the MuseTalk Avatar and saves it to disk. Returns the avatar reference ID.
        Class takes an uploaded video and converts it to images.
        The uploaded video should be validated before calling this method. Designed to
        site behind the Aiphish api server's consent flow. Not safe for direct user input.
        For best results, uploaded video should be 10-15 seconds of not talking, neutral expression,
        staring at the camera as if listening to someone speaking.

        ffmpeg used for frame extraction. resamples to 25 fps and adjusts for rotation if
        recorded on mobile. Normalizes resolution to 720p.

        If avatar id is provided, existing avatar under that ID will be deleted and avatar
        will be reprocessed. Avatar ID should not be provided for a new avatar
        but is not enforced.

        bbox_shifts:    Vertically offsets the detected face bounding box, changing 
                        which region of the face is cropped and fed to the model. Default 0.
        extra_margin:   pixels added to the bottom of the crop, applied at crop time. Extends 
                        the box downward to include more jaw and chin in what the model sees.
                        bbox shifts the entire box down, extra_margin expand bottom edge with 
                        top fixed.
        Designed to run as a non-priority background task within the consent and wraith creation
        pipeline. For that reason uses CPU to prefer free GPU cycles over speed incase inference
        is being run in parallel.

        Musetalk V15 required.
        """

        if not os.path.exists(save_path):
            save_path = "/aiphish/livewraith/avatars"
        
        if reprocess_avatar_id:
            avatar_id = reprocess_avatar_id
            avatar_save_path = os.path.join(save_path, org_id, tenant_id, avatar_id)
            if os.path.exists(avatar_save_path):
                shutil.rmtree(avatar_save_path)
        else:
            avatar_id = uuid4()
            avatar_save_path = os.path.join(save_path, org_id, tenant_id, avatar_id)
        
        temp_filename = token_urlsafe(32)
        temp_video_path = os.path.join(avatar_save_path, "video", temp_filename)
        full_imgs_path = os.path.join(avatar_save_path, 'full_imgs')
        mask_out_path = os.path.join(avatar_save_path, 'mask')
        os.makedirs(temp_video_path, exist_ok=True)
        os.makedirs(full_imgs_path, exist_ok=True)
        os.makedirs(mask_out_path, exist_ok=True)
        mask_coords_path = os.path.join(avatar_save_path, 'mask_coords.pkl')
        coords_path = os.path.join(avatar_save_path, 'coords.pkl')
        latents_out_path = os.path.join(avatar_save_path, 'latents.pt')
        
        chunk_size = 1024*1024
        await media_file.seek(0)
        async with aiofiles.open(temp_video_path, "wb") as f:
            while chunk := await media_file.read(chunk_size):
                await f.write(chunk)
        

todo        ####### WRITE VIDEO FILE TO TEMPFILE FOLDER FOR ALL VIDEO FILES AND PASS PATH IN. KEEP THIS METHOD SYNC ONLY
        
        metadata_file = os.path.join(avatar_save_path, "avatar_info.json")
        async with aiofiles.open(metadata_file, "wb") as f:
            await f.write(
                json.dump({
                    "avatar_id": avatar_id,
                    "bbox_shift": bbox_shift
                })
            )
        
        self._progress[avatar_id] = 1
        self._subprogress_percent[avatar_id] = 0

        ffmpeg_cmd = [
            "ffmpeg",
            "-nostdin",
            "-loglevel", "error",
            "-i", str(temp_video_path),
            "-vf",
            "fps=25",
            "scale=-2:720",
            f"{full_imgs_path}/%08d.png"
        ]
        proc = await asyncio.create_subprocess.exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        except asyncio.TimeoutError:
            proc.kill()

        if proc.returncode != 0:
            self._progress[avatar_id] = 1000
            self._error_reason[avatar_id] = "Unable to extract frames from video. Confirm valid video file and try again later."
            logger.error("Avatar creation failed for: %s. Reason: %s", avatar_id, stderr.decode())
            raise VideoError("Cannot extract frames from video")
        
        self._progress[avatar_id] += 1
        self._subprogress_percent[avatar_id] = 0

        img_list = sorted(glob.glob(os.path.join(full_imgs_path, '*.png')))
        coord_list, frame_list = get_landmark_and_bbox(img_list, bbox_shift)

        self._progress[avatar_id] += 1

        input_latent_list = []
        idx = -1
        coord_placeholder = (0.0, 0.0, 0.0, 0.0)

        device = torch.device('cpu')

        vae_local, _, _ = load_all_model(device=device)
        #vae_local.vae = vae_local.vae.half().to(device) skip for cpu, uncomment if switched back to gpu
       
        fp_local = FaceParsing(left_cheek_width=90, right_cheek_width=90)
        
        for bbox, frame in zip(coord_list, frame_list):
            idx = idx + 1
            if bbox == coord_placeholder:
                continue
            x1, y1, x2, y2 = bbox
            y2 = y2 + extra_margin
            y2 = min(y2, frame.shape[0])
            coord_list[idx] = [x1, y1, x2, y2]
            crop_frame = frame[y1:y2, x1:x2]
            resized_crop_frame = cv2.resize(crop_frame, (256, 256), interpolation=cv2.INTER_LANCZOS4)
            latents = vae_local.get_latents_for_unet(resized_crop_frame)
            input_latent_list.append(latents)

        self._progress[avatar_id] += 1
        self._subprogress_percent[avatar_id] = 0

        mask_coords_list_cycle = []
        mask_list_cycle = []
        for i, frame in enumerate(frame_list):
            cv2.imwrite(f"{full_imgs_path}/{str(i).zfill(8)}.png", frame)

            x1, y1, x2, y2 = coord_list[i]
            mode = parsing_mode
            mask, crop_box = get_image_prepare_material(frame, [x1, y1, x2, y2], fp=fp_local, mode=mode)
            cv2.imwrite(f"{mask_out_path}/{str(i).zfill(8)}.png", mask)

            mask_coords_list_cycle += [crop_box]
            mask_list_cycle.append(mask)

            self._subprogress_percent[avatar_id] = (i / len(frame_list))
        
        self._progress[avatar_id] += 1
        self._subprogress_percent[avatar_id] = 0

        with open(mask_coords_path, 'wb') as f:
            pickle.dump(mask_coords_list_cycle, f)
        
        async with aiofiles.open(mask_coords_path, "wb") as f:
                await f.write(
                    pickle.dump(mask_coords_list_cycle, f)
                )



        



        
           





    
    def video2imgs(
        vid_path,
        save_path,
        ext='.png', 
        cut_frame=10000000
    ):
        """
        """
    cap = cv2.VideoCapture(vid_path)
    count = 0
    while True:
        if count > cut_frame:
            break
        ret, frame = cap.read()
        if ret:
            cv2.putText(frame, "LiveTalking", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (128,128,128), 1)
            cv2.imwrite(f"{save_path}/{count:08d}.png", frame)
            count += 1
        else:
            break










