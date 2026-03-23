from dataclasses import dataclass, field

import numpy as np


@dataclass(slots=True)
class RecolorParams:
    target_hex: str
    color_strength: float = 0.72
    luminance_strength: float = 0.0
    lightness_offset: float = 0.0
    clahe_enabled: bool = True
    clahe_clip_limit: float = 0.015
    clahe_kernel_size: int = 8
    highlight_protection: float = 0.65
    shadow_protection: float = 1.0
    texture_strength: float = 0.18
    texture_blur_sigma: float = 1.2
    texture_threshold: float = 0.35
    gamut_compression: float = 1.0


@dataclass(slots=True)
class RecolorResult:
    output_rgb: np.ndarray
    output_lab: np.ndarray
    prepared_l: np.ndarray
    highlight_mask: np.ndarray
    shadow_mask: np.ndarray
    texture_map: np.ndarray
    weight_map: np.ndarray
    debug_info: dict = field(default_factory=dict)