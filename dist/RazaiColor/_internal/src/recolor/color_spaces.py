import numpy as np
from skimage import color


def hex_to_rgb01(hex_color: str) -> np.ndarray:
    value = hex_color.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError("Hex color must be in the format #RRGGBB.")

    rgb = np.array([int(value[index:index + 2], 16) for index in range(0, 6, 2)], dtype=np.float32)
    return rgb / 255.0


def rgb01_to_lab(image_rgb: np.ndarray) -> np.ndarray:
    clipped = np.clip(image_rgb.astype(np.float32), 0.0, 1.0)
    return color.rgb2lab(clipped)


def lab_to_rgb01(image_lab: np.ndarray) -> np.ndarray:
    return color.lab2rgb(image_lab.astype(np.float32)).astype(np.float32)


def hex_to_lab(hex_color: str) -> np.ndarray:
    rgb = hex_to_rgb01(hex_color)[None, None, :]
    return rgb01_to_lab(rgb)[0, 0, :]