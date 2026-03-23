import numpy as np
from skimage import exposure


def prepare_luminance_channel(
    l_channel: np.ndarray,
    clip_limit: float,
    kernel_size: int,
    enabled: bool,
) -> np.ndarray:
    if not enabled:
        return l_channel.astype(np.float32)

    normalized = np.clip(l_channel.astype(np.float32) / 100.0, 0.0, 1.0)
    prepared = exposure.equalize_adapthist(
        normalized,
        clip_limit=max(clip_limit, 0.001),
        kernel_size=max(kernel_size, 2),
    )
    return (prepared.astype(np.float32) * 100.0)