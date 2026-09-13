from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2



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