import numpy as np


def clamp_lab_ranges(l_channel: np.ndarray, a_channel: np.ndarray, b_channel: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    l_clamped = np.clip(l_channel.astype(np.float32), 0.0, 100.0)
    a_clamped = np.clip(a_channel.astype(np.float32), -128.0, 127.0)
    b_clamped = np.clip(b_channel.astype(np.float32), -128.0, 127.0)
    return l_clamped, a_clamped, b_clamped


def compress_and_clip_rgb(rgb_image: np.ndarray, compression: float) -> tuple[np.ndarray, dict]:
    rgb = rgb_image.astype(np.float32)
    underflow = np.maximum(-rgb, 0.0)
    overflow = np.maximum(rgb - 1.0, 0.0)
    max_overflow = float(max(np.max(underflow, initial=0.0), np.max(overflow, initial=0.0)))

    if compression < 1.0:
        center = 0.5
        rgb = center + (rgb - center) * compression

    clipped = np.clip(rgb, 0.0, 1.0)
    clipped_ratio = float(np.mean((rgb < 0.0) | (rgb > 1.0)))
    debug = {
        "max_overflow": max_overflow,
        "clipped_ratio": clipped_ratio,
    }
    return clipped.astype(np.float32), debug