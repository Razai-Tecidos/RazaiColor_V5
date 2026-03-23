import numpy as np
from skimage import filters


def extract_texture_map(l_channel: np.ndarray, sigma: float, threshold: float) -> np.ndarray:
    blurred = filters.gaussian(l_channel.astype(np.float32), sigma=max(sigma, 0.1), preserve_range=True)
    detail = l_channel.astype(np.float32) - blurred.astype(np.float32)
    suppressed = np.where(np.abs(detail) >= threshold, detail, 0.0)
    return suppressed.astype(np.float32)


def reinject_texture(
    l_channel: np.ndarray,
    texture_map: np.ndarray,
    texture_strength: float,
    highlight_mask: np.ndarray,
    shadow_mask: np.ndarray,
) -> np.ndarray:
    emphasis = (1.0 - 0.45 * highlight_mask) * (1.0 - 0.65 * shadow_mask)
    reinjected = l_channel.astype(np.float32) + (texture_strength * texture_map.astype(np.float32) * emphasis.astype(np.float32))
    return np.clip(reinjected, 0.0, 100.0).astype(np.float32)