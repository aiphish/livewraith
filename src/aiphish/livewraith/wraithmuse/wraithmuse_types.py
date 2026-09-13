from typing import NamedTuple
import numpy as np
import numpy.typing as npt
import torch

from pydantic_settings import BaseSettings

from musetalk.models.vae import VAE
from musetalk.models.unet import UNet, PositionalEncoding
from musetalk.whisper.audio2feature import Audio2Feature

BGRImage = npt.NDArray[np.uint8]
GrayMask = npt.NDArray[np.uint8]
BBox = tuple[int, int, int, int]

class WraithModel(NamedTuple):
    """
    Type hint for the loaded model from Musetalk using load_all_model.
    Loaded on app startup.
    """
    vae: VAE
    unet: UNet
    pe: PositionalEncoding
    timesteps: torch.Tensor
    audio_processor: Audio2Feature

class WraithAvatar(NamedTuple):
    """
    Type hint for the loaded MuseTalk avatar. Represents
    a cloned identity. Loaded on session creation.
    """

    frame_list_cycle: list[BGRImage]
    mask_list_cycle: list[GrayMask]
    coord_list_cycle: list[BBox]
    mask_coords_list_cycle: list[BBox]
    input_latent_list_cycle: list[torch.Tensor]


class WraithOpt(BaseSettings):
    """
    CLI flags passed into MuseTalk.
    """
    fps: int = 50
    batch_size: int = 16
    stride_left_size: int = 10
    stride_right_size: int = 10

    @property
    def chunk(self) -> int:
        return 16000 // self.fps

    @property
    def frame_bytes(self) -> int:
        return self.chunk * 2

