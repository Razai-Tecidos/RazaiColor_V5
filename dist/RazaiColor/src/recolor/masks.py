import numpy as np


def build_highlight_mask(l_channel: np.ndarray, strength: float) -> np.ndarray:
    l_norm = np.clip(l_channel.astype(np.float32) / 100.0, 0.0, 1.0)
    pivot = np.clip(0.68 - (0.1 * (1.0 - strength)), 0.5, 0.85)
    ramp = np.clip((l_norm - pivot) / max(1.0 - pivot, 1e-6), 0.0, 1.0)
    return ramp * ramp


def build_shadow_mask(l_channel: np.ndarray, strength: float) -> np.ndarray:
    l_norm = np.clip(l_channel.astype(np.float32) / 100.0, 0.0, 1.0)
    pivot = np.clip(0.22 + (0.08 * strength), 0.12, 0.35)
    ramp = np.clip((pivot - l_norm) / max(pivot, 1e-6), 0.0, 1.0)
    return ramp * ramp


def build_chroma_weight_map(
    l_channel: np.ndarray,
    color_strength: float,
    highlight_protection: float,
    shadow_protection: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    highlight_mask = build_highlight_mask(l_channel, highlight_protection)
    shadow_mask = build_shadow_mask(l_channel, shadow_protection)
    weight = color_strength * (1.0 - highlight_mask * highlight_protection) * (1.0 - shadow_mask * shadow_protection)
    return np.clip(weight, 0.0, 1.0).astype(np.float32), highlight_mask.astype(np.float32), shadow_mask.astype(np.float32)