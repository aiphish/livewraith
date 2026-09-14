from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
from dataclasses import dataclass, field
from numpy.typing import NDArray
import numpy as np

def read_imgs(img_list):
    def load_image(index, img_path):
        img = cv2.imread(img_path)
        if img is None:
            raise ValueError(f"failed to read image: {img_path}")
        return index, img

    frames = [None] * len(img_list)  # Initialize a list with the same length as img_list
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(load_image, i, p) for i, p in enumerate(img_list)]
        for future in as_completed(futures):
            idx, img = future.result()
            frames[idx] = img
    return frames

def mirror_index(size, index):
    turn = index // size
    res = index % size
    if turn % 2 == 0:
        return res
    else:
        return size - res - 1 

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

@dataclass
class AudioFrameData:
    data: NDArray[np.float32]
    type: int = 0  # 默认值
    userdata: dict = field(default_factory=dict)