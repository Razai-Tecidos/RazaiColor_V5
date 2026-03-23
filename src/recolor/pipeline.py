import numpy as np

from .color_spaces import hex_to_lab, rgb01_to_lab, lab_to_rgb01
from .gamut import clamp_lab_ranges, compress_and_clip_rgb
from .models import RecolorParams, RecolorResult


def _build_shadow_mask(l_channel: np.ndarray) -> np.ndarray:
    l_normalized = np.clip(l_channel / 100.0, 0.0, 1.0)
    shadow_start = 0.42
    mask = np.clip((shadow_start - l_normalized) / shadow_start, 0.0, 1.0).astype(np.float32)
    return np.power(mask, 1.6).astype(np.float32)


def recolor_fabric_image(image_rgb: np.ndarray, params: RecolorParams) -> RecolorResult:
    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError("Input image must be an RGB image with shape [H, W, 3].")

    rgb = np.clip(image_rgb.astype(np.float32), 0.0, 1.0)
    image_lab = rgb01_to_lab(rgb)
    target_lab = hex_to_lab(params.target_hex)

    l_original = image_lab[..., 0].astype(np.float32)
    a_original = image_lab[..., 1].astype(np.float32)
    b_original = image_lab[..., 2].astype(np.float32)

    prepared_l = l_original.copy()
    base_color_strength = np.clip(params.color_strength, 0.0, 3.0)
    weight_map = np.full_like(l_original, fill_value=base_color_strength, dtype=np.float32)
    highlight_mask = np.zeros_like(l_original, dtype=np.float32)
    shadow_mask = _build_shadow_mask(l_original)
    luminance_weight = np.clip(params.luminance_strength, 0.0, 1.0)
    lightness_offset = float(params.lightness_offset)
    shadow_protection = np.clip(params.shadow_protection, 0.0, 1.0)

    shadow_chroma_application = 1.0 - (shadow_mask * shadow_protection * 0.58)
    weight_map = weight_map * shadow_chroma_application

    l_target = np.full_like(l_original, target_lab[0], dtype=np.float32)
    a_target = np.full_like(a_original, target_lab[1], dtype=np.float32)
    b_target = np.full_like(b_original, target_lab[2], dtype=np.float32)

    a_new = (a_original * (1.0 - weight_map)) + (a_target * weight_map)
    b_new = (b_original * (1.0 - weight_map)) + (b_target * weight_map)

    texture_map = np.zeros_like(l_original, dtype=np.float32)
    mean_l_original = float(np.mean(l_original))
    mean_l_target = float(target_lab[0])
    luminance_delta = (mean_l_target - mean_l_original) * luminance_weight
    luminance_application = 1.0 - (shadow_mask * shadow_protection)
    luminance_adjustment = (luminance_delta + lightness_offset) * luminance_application
    shadow_depth_boost = shadow_mask * shadow_protection * np.clip(base_color_strength / 3.0, 0.0, 1.0) * 4.0
    l_final = l_original + luminance_adjustment - shadow_depth_boost

    l_final, a_new, b_new = clamp_lab_ranges(l_final, a_new, b_new)
    lab_output = np.stack([l_final, a_new, b_new], axis=-1).astype(np.float32)

    rgb_output = lab_to_rgb01(lab_output)
    rgb_output, gamut_debug = compress_and_clip_rgb(rgb_output, params.gamut_compression)

    debug_info = {
        "mode": "simple_preserve_l",
        "target_lab": target_lab.tolist(),
        "mean_l_target": mean_l_target,
        "mean_l_original": mean_l_original,
        "mean_l_prepared": float(np.mean(prepared_l)),
        "mean_l_final": float(np.mean(l_final)),
        "mean_weight": float(np.mean(weight_map)),
        "base_color_strength": float(base_color_strength),
        "mean_luminance_weight": float(luminance_weight),
        "luminance_delta": float(luminance_delta),
        "lightness_offset": float(lightness_offset),
        "mean_shadow_mask": float(np.mean(shadow_mask)),
        "shadow_protection": float(shadow_protection),
        "mean_shadow_chroma_application": float(np.mean(shadow_chroma_application)),
        "mean_luminance_application": float(np.mean(luminance_application)),
        "mean_shadow_depth_boost": float(np.mean(shadow_depth_boost)),
        **gamut_debug,
    }

    return RecolorResult(
        output_rgb=rgb_output,
        output_lab=lab_output,
        prepared_l=prepared_l,
        highlight_mask=highlight_mask,
        shadow_mask=shadow_mask,
        texture_map=texture_map,
        weight_map=weight_map,
        debug_info=debug_info,
    )