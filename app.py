import io
import json
import os
import shutil
import zipfile
from dataclasses import asdict
from uuid import uuid4

import numpy as np
import streamlit as st
from PIL import Image

from src.recolor import RecolorParams, recolor_fabric_image


DEFAULT_COLOR_STRENGTH = 1.0
DEFAULT_LUMINANCE_STRENGTH = 1.0
DEFAULT_LIGHTNESS_OFFSET = 0.0
DEFAULT_SHADOW_PROTECTION = 1.0
COLLECTION_IMAGE_MAX_BYTES = 2 * 1024 * 1024
COLLECTION_IMAGE_MIN_BYTES = int(1.8 * 1024 * 1024)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_RUNTIME_DIR = os.path.join(PROJECT_ROOT, ".razaicolor_runtime")
COLLECTION_STORAGE_FOLDER = os.path.join(PROJECT_RUNTIME_DIR, "collection_assets")


def collection_item_exceeds_download_limit(item: dict) -> bool:
    return asset_size_bytes(item.get("processed_image_path") or item.get("processed_image_bytes") or b"") > COLLECTION_IMAGE_MAX_BYTES


def refresh_collection_download_state() -> None:
    collection = st.session_state.get("collection") or []
    st.session_state.collection_ready_for_download = bool(collection) and not any(
        collection_item_exceeds_download_limit(item) for item in collection
    )


def ensure_collection_page_in_bounds() -> None:
    collection = st.session_state.get("collection") or []
    page_size = max(1, int(st.session_state.get("collection_page_size", 12)))
    total_pages = max(1, int(np.ceil(len(collection) / page_size)))
    st.session_state.collection_page = min(max(1, int(st.session_state.get("collection_page", 1))), total_pages)


def invalidate_collection_export_cache() -> None:
    st.session_state.collection_zip_bytes = None


def ensure_collection_storage_dir() -> str:
    storage_dir = st.session_state.get("collection_storage_dir")
    if storage_dir and storage_dir != COLLECTION_STORAGE_FOLDER and os.path.isdir(storage_dir):
        shutil.rmtree(storage_dir, ignore_errors=True)

    os.makedirs(COLLECTION_STORAGE_FOLDER, exist_ok=True)
    st.session_state.collection_storage_dir = COLLECTION_STORAGE_FOLDER
    return COLLECTION_STORAGE_FOLDER


def clear_collection_storage() -> None:
    storage_dir = st.session_state.get("collection_storage_dir") or COLLECTION_STORAGE_FOLDER
    if storage_dir and os.path.isdir(storage_dir):
        shutil.rmtree(storage_dir, ignore_errors=True)

    st.session_state.collection_storage_dir = None
    st.session_state.collection_source_image_path = None
    st.session_state.collection_source_image_name = ""


def write_binary_asset(data: bytes, suffix: str) -> str:
    storage_dir = ensure_collection_storage_dir()
    file_path = os.path.join(storage_dir, f"{uuid4().hex}{suffix}")
    with open(file_path, "wb") as asset_file:
        asset_file.write(data)
    return file_path


def overwrite_binary_asset(file_path: str | None, data: bytes, suffix: str) -> str:
    target_path = file_path or write_binary_asset(data, suffix)
    with open(target_path, "wb") as asset_file:
        asset_file.write(data)
    return target_path


def read_binary_asset(file_path: str | None) -> bytes:
    if not file_path or not os.path.isfile(file_path):
        return b""

    with open(file_path, "rb") as asset_file:
        return asset_file.read()


def delete_binary_asset(file_path: str | None) -> None:
    if file_path and os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass


def asset_size_bytes(data_or_path: bytes | str) -> int:
    if isinstance(data_or_path, str):
        return os.path.getsize(data_or_path) if os.path.isfile(data_or_path) else 0
    return len(data_or_path or b"")


def migrate_collection_items_to_disk() -> None:
    collection = st.session_state.get("collection") or []
    if not collection:
        return

    if not st.session_state.get("collection_source_image_path"):
        for item in collection:
            original_image_bytes = item.get("original_image_bytes") or b""
            if original_image_bytes:
                st.session_state.collection_source_image_path = write_binary_asset(original_image_bytes, ".bin")
                st.session_state.collection_source_image_name = item.get("image_name") or st.session_state.uploaded_image_name
                break

    for item in collection:
        original_processed_image_bytes = item.pop("original_processed_image_bytes", None)
        if original_processed_image_bytes and not item.get("original_processed_image_path"):
            item["original_processed_image_path"] = write_binary_asset(original_processed_image_bytes, ".png")

        processed_image_bytes = item.pop("processed_image_bytes", None)
        if processed_image_bytes and not item.get("processed_image_path"):
            item["processed_image_path"] = write_binary_asset(processed_image_bytes, ".png")

        display_image_bytes = item.pop("display_image_bytes", None)
        if display_image_bytes and not item.get("display_image_path"):
            item["display_image_path"] = write_binary_asset(display_image_bytes, ".png")

        item.pop("original_image_bytes", None)


def initialize_state() -> None:
    if "stage" not in st.session_state:
        st.session_state.stage = 1
    if "uploaded_image_bytes" not in st.session_state:
        st.session_state.uploaded_image_bytes = None
    if "uploaded_image_name" not in st.session_state:
        st.session_state.uploaded_image_name = ""
    if "collection" not in st.session_state:
        st.session_state.collection = []
    if "processed_preview_rgb" not in st.session_state:
        st.session_state.processed_preview_rgb = None
    if "processed_image_bytes" not in st.session_state:
        st.session_state.processed_image_bytes = None
    if "recolor_params" not in st.session_state:
        st.session_state.recolor_params = None
    if "processing_debug" not in st.session_state:
        st.session_state.processing_debug = None
    if "live_preview_rgb" not in st.session_state:
        st.session_state.live_preview_rgb = None
    if "live_preview_source_rgb" not in st.session_state:
        st.session_state.live_preview_source_rgb = None
    if "live_preview_signature" not in st.session_state:
        st.session_state.live_preview_signature = None
    if "live_processing_debug" not in st.session_state:
        st.session_state.live_processing_debug = None
    if "color_strength_slider" not in st.session_state:
        st.session_state.color_strength_slider = DEFAULT_COLOR_STRENGTH
    if "luminance_strength_slider" not in st.session_state:
        st.session_state.luminance_strength_slider = DEFAULT_LUMINANCE_STRENGTH
    if "lightness_offset_slider" not in st.session_state:
        st.session_state.lightness_offset_slider = DEFAULT_LIGHTNESS_OFFSET
    if "shadow_protection_slider" not in st.session_state:
        st.session_state.shadow_protection_slider = DEFAULT_SHADOW_PROTECTION
    if "collection_ready_for_download" not in st.session_state:
        st.session_state.collection_ready_for_download = False
    if "collection_page" not in st.session_state:
        st.session_state.collection_page = 1
    if "collection_page_size" not in st.session_state:
        st.session_state.collection_page_size = 12
    if "collection_zip_bytes" not in st.session_state:
        st.session_state.collection_zip_bytes = None
    if "collection_panel_expanded" not in st.session_state:
        st.session_state.collection_panel_expanded = False
    if "collection_storage_dir" not in st.session_state:
        st.session_state.collection_storage_dir = None
    if "collection_source_image_path" not in st.session_state:
        st.session_state.collection_source_image_path = None
    if "collection_source_image_name" not in st.session_state:
        st.session_state.collection_source_image_name = ""


def reset_slider_defaults() -> None:
    st.session_state.color_strength_slider = DEFAULT_COLOR_STRENGTH
    st.session_state.luminance_strength_slider = DEFAULT_LUMINANCE_STRENGTH
    st.session_state.lightness_offset_slider = DEFAULT_LIGHTNESS_OFFSET
    st.session_state.shadow_protection_slider = DEFAULT_SHADOW_PROTECTION
    st.session_state.live_preview_signature = None


def clear_collection_state() -> None:
    st.session_state.collection = []
    st.session_state.collection_ready_for_download = False
    st.session_state.collection_page = 1
    st.session_state.collection_panel_expanded = False
    clear_collection_storage()
    invalidate_collection_export_cache()


def save_uploaded_file(uploaded_file) -> None:
    new_image_bytes = uploaded_file.getvalue()
    new_image_name = uploaded_file.name
    previous_image_bytes = st.session_state.uploaded_image_bytes
    previous_image_name = st.session_state.uploaded_image_name

    if previous_image_bytes is not None and (
        previous_image_name != new_image_name or previous_image_bytes != new_image_bytes
    ):
        clear_collection_state()

    st.session_state.uploaded_image_bytes = new_image_bytes
    st.session_state.uploaded_image_name = new_image_name
    st.session_state.processed_preview_rgb = None
    st.session_state.processed_image_bytes = None
    st.session_state.recolor_params = None
    st.session_state.processing_debug = None
    st.session_state.live_preview_rgb = None
    st.session_state.live_preview_source_rgb = None
    st.session_state.live_preview_signature = None
    st.session_state.live_processing_debug = None
    st.session_state.collection_ready_for_download = False
    invalidate_collection_export_cache()


def normalize_hex(value: str) -> str:
    cleaned = value.strip().upper()
    if len(cleaned) == 7 and cleaned.startswith("#"):
        return cleaned
    return ""


def image_bytes_to_rgb01(image_bytes: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(image_bytes)) as image:
        rgb_image = image.convert("RGB")
        return np.asarray(rgb_image, dtype=np.float32) / 255.0


def image_bytes_to_preview_rgb01(image_bytes: bytes, max_side: int = 768) -> np.ndarray:
    with Image.open(io.BytesIO(image_bytes)) as image:
        rgb_image = image.convert("RGB")
        rgb_image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        return np.asarray(rgb_image, dtype=np.float32) / 255.0


def rgb01_to_png_bytes(image_rgb: np.ndarray) -> bytes:
    image_uint8 = np.clip(image_rgb * 255.0, 0.0, 255.0).astype(np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(image_uint8, mode="RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def bytes_to_mb_label(data_or_path: bytes | str) -> str:
    size_mb = asset_size_bytes(data_or_path) / (1024 * 1024)
    return f"{size_mb:.2f} MB"


def build_collection_thumbnail_bytes(image_bytes: bytes, max_side: int = 320) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as image:
        rgb_image = image.convert("RGB")
        rgb_image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        rgb_image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()


def _save_rgb_image(image_rgb: np.ndarray, format_name: str, **save_kwargs) -> bytes:
    image_uint8 = np.clip(image_rgb * 255.0, 0.0, 255.0).astype(np.uint8)
    buffer = io.BytesIO()
    Image.fromarray(image_uint8, mode="RGB").save(buffer, format=format_name, **save_kwargs)
    return buffer.getvalue()


def compress_rgb_image_to_collection_target(image_rgb: np.ndarray, max_bytes: int = COLLECTION_IMAGE_MAX_BYTES) -> tuple[bytes, str, str]:
    working_image = np.clip(image_rgb, 0.0, 1.0)

    def encode_png(candidate_rgb: np.ndarray, optimize: bool = True, quantize_colors: int | None = None) -> bytes:
        image_uint8 = np.clip(candidate_rgb * 255.0, 0.0, 255.0).astype(np.uint8)
        pil_image = Image.fromarray(image_uint8, mode="RGB")

        if quantize_colors is not None:
            pil_image = pil_image.quantize(colors=quantize_colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)

        buffer = io.BytesIO()
        pil_image.save(buffer, format="PNG", optimize=optimize, compress_level=9)
        return buffer.getvalue()

    scale_factors = [1.0, 0.98, 0.96, 0.94, 0.92, 0.90, 0.88, 0.86, 0.84, 0.82, 0.80, 0.78, 0.76, 0.74, 0.72]
    png_variants = [
        (None, True),
        (256, True),
        (224, True),
        (192, True),
        (160, True),
        (128, True),
        (96, True),
        (64, True),
        (48, True),
        (32, True),
    ]

    candidate_bytes = None
    candidate_size = -1

    for scale in scale_factors:
        if scale == 1.0:
            resized_image = working_image
        else:
            target_height = max(1, int(round(working_image.shape[0] * scale)))
            target_width = max(1, int(round(working_image.shape[1] * scale)))
            resized_image = np.asarray(
                Image.fromarray(np.clip(working_image * 255.0, 0.0, 255.0).astype(np.uint8), mode="RGB").resize(
                    (target_width, target_height), Image.Resampling.LANCZOS
                ),
                dtype=np.float32,
            ) / 255.0

        for quantize_colors, optimize in png_variants:
            png_bytes = encode_png(resized_image, optimize=optimize, quantize_colors=quantize_colors)
            size_bytes = len(png_bytes)
            if size_bytes <= max_bytes and size_bytes > candidate_size:
                candidate_bytes = png_bytes
                candidate_size = size_bytes
                if COLLECTION_IMAGE_MIN_BYTES <= size_bytes <= max_bytes:
                    return candidate_bytes, "image/png", "png"

    if candidate_bytes is not None:
        return candidate_bytes, "image/png", "png"

    fallback_png = encode_png(working_image, optimize=True, quantize_colors=32)
    return fallback_png, "image/png", "png"


def build_recolor_params(
    target_hex: str,
    color_strength: float,
    luminance_strength: float,
    lightness_offset: float,
    shadow_protection: float,
) -> RecolorParams:
    return RecolorParams(
        target_hex=target_hex,
        color_strength=color_strength,
        luminance_strength=luminance_strength,
        lightness_offset=lightness_offset,
        shadow_protection=shadow_protection,
    )


def generate_recolor_preview(
    target_hex: str,
    color_strength: float,
    luminance_strength: float,
    lightness_offset: float,
    shadow_protection: float,
) -> None:
    if not st.session_state.uploaded_image_bytes:
        raise ValueError("Envie uma imagem antes de processar.")

    image_rgb = image_bytes_to_rgb01(st.session_state.uploaded_image_bytes)
    params = build_recolor_params(target_hex, color_strength, luminance_strength, lightness_offset, shadow_protection)
    result = recolor_fabric_image(image_rgb, params)

    st.session_state.processed_preview_rgb = result.output_rgb
    st.session_state.processed_image_bytes = rgb01_to_png_bytes(result.output_rgb)
    st.session_state.recolor_params = asdict(params)
    st.session_state.processing_debug = result.debug_info


def update_live_preview(
    target_hex: str,
    color_strength: float,
    luminance_strength: float,
    lightness_offset: float,
    shadow_protection: float,
) -> None:
    if not st.session_state.uploaded_image_bytes or not target_hex:
        st.session_state.live_preview_rgb = None
        st.session_state.live_preview_signature = None
        st.session_state.live_processing_debug = None
        return

    current_signature = (
        target_hex,
        round(float(color_strength), 4),
        round(float(luminance_strength), 4),
        round(float(lightness_offset), 4),
        round(float(shadow_protection), 4),
    )
    if st.session_state.live_preview_signature == current_signature:
        return

    if st.session_state.live_preview_source_rgb is None:
        st.session_state.live_preview_source_rgb = image_bytes_to_preview_rgb01(st.session_state.uploaded_image_bytes)

    params = build_recolor_params(target_hex, color_strength, luminance_strength, lightness_offset, shadow_protection)
    result = recolor_fabric_image(st.session_state.live_preview_source_rgb, params)
    st.session_state.live_preview_rgb = result.output_rgb
    st.session_state.live_preview_signature = current_signature
    st.session_state.live_processing_debug = result.debug_info


def add_current_image_to_collection(color_name: str, color_hex: str) -> None:
    if not st.session_state.uploaded_image_bytes or not st.session_state.processed_image_bytes:
        st.warning("Gere o preview recolorizado antes de adicionar a colecao.")
        return

    if not st.session_state.collection_source_image_path:
        st.session_state.collection_source_image_path = write_binary_asset(st.session_state.uploaded_image_bytes, ".bin")
        st.session_state.collection_source_image_name = st.session_state.uploaded_image_name

    processed_image_path = write_binary_asset(st.session_state.processed_image_bytes, ".png")
    original_processed_image_path = write_binary_asset(st.session_state.processed_image_bytes, ".png")
    display_image_path = write_binary_asset(build_collection_thumbnail_bytes(st.session_state.processed_image_bytes), ".png")

    normalized_hex = color_hex.strip().upper()
    collection_item = {
        "name": color_name.strip(),
        "hex": normalized_hex,
        "image_name": st.session_state.uploaded_image_name,
        "original_processed_image_path": original_processed_image_path,
        "processed_image_path": processed_image_path,
        "display_image_path": display_image_path,
        "processed_image_mime": "image/png",
        "processed_image_extension": "png",
        "compressed": False,
        "params": st.session_state.recolor_params,
        "debug": st.session_state.processing_debug,
    }
    st.session_state.collection.append(collection_item)
    ensure_collection_page_in_bounds()
    st.session_state.collection_page = max(1, int(np.ceil(len(st.session_state.collection) / st.session_state.collection_page_size)))
    invalidate_collection_export_cache()
    refresh_collection_download_state()
    st.success("Imagem adicionada a colecao.")


def compress_collection_for_download() -> tuple[int, int, int]:
    items_requiring_compression = [
        item for item in st.session_state.collection if collection_item_exceeds_download_limit(item)
    ]
    total_items = len(st.session_state.collection)
    items_to_compress = len(items_requiring_compression)

    if items_to_compress == 0:
        refresh_collection_download_state()
        return 0, 0, total_items

    progress_bar = st.progress(0.0, text="Preparando compressao da colecao...")
    status = st.empty()

    compressed_count = 0
    for index, item in enumerate(items_requiring_compression, start=1):
        status.text(f"Comprimindo imagem {index} de {items_to_compress}: {item['name']}")
        source_bytes = read_binary_asset(item.get("original_processed_image_path")) or item.get("original_processed_image_bytes") or read_binary_asset(item.get("processed_image_path")) or item.get("processed_image_bytes")
        source_rgb = image_bytes_to_rgb01(source_bytes)
        compressed_bytes, compressed_mime, compressed_extension = compress_rgb_image_to_collection_target(source_rgb)

        item["processed_image_path"] = overwrite_binary_asset(item.get("processed_image_path"), compressed_bytes, ".png")
        item["display_image_path"] = overwrite_binary_asset(item.get("display_image_path"), build_collection_thumbnail_bytes(compressed_bytes), ".png")
        item["processed_image_mime"] = compressed_mime
        item["processed_image_extension"] = compressed_extension
        item["compressed"] = True
        compressed_count += 1

        progress_bar.progress(index / items_to_compress, text=f"Comprimindo colecao... {index}/{items_to_compress}")

    status.text("Compressao finalizada. Colecao pronta para download.")
    invalidate_collection_export_cache()
    refresh_collection_download_state()
    return compressed_count, items_to_compress, total_items


def submit_current_selection_to_collection() -> None:
    color_name = st.session_state.get("color_name_input", "").strip()
    color_hex = st.session_state.get("color_hex_input", "").strip()
    normalized_hex = normalize_hex(color_hex)

    if not color_name or not normalized_hex:
        return

    try:
        generate_recolor_preview(
            normalized_hex,
            float(st.session_state.get("color_strength_slider", DEFAULT_COLOR_STRENGTH)),
            float(st.session_state.get("luminance_strength_slider", DEFAULT_LUMINANCE_STRENGTH)),
            float(st.session_state.get("lightness_offset_slider", DEFAULT_LIGHTNESS_OFFSET)),
            float(st.session_state.get("shadow_protection_slider", DEFAULT_SHADOW_PROTECTION)),
        )
        add_current_image_to_collection(color_name, normalized_hex)
    except ValueError as error:
        st.error(str(error))


def remove_collection_item(index: int) -> None:
    if index < 0 or index >= len(st.session_state.collection):
        return

    item = st.session_state.collection.pop(index)
    delete_binary_asset(item.get("original_processed_image_path"))
    delete_binary_asset(item.get("processed_image_path"))
    delete_binary_asset(item.get("display_image_path"))
    if not st.session_state.collection:
        clear_collection_storage()
        st.session_state.collection_panel_expanded = False

    ensure_collection_page_in_bounds()
    invalidate_collection_export_cache()
    refresh_collection_download_state()


def build_collection_zip() -> bytes:
    buffer = io.BytesIO()
    manifest = []

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        source_image_name = st.session_state.get("collection_source_image_name") or st.session_state.uploaded_image_name or "source_image"
        source_image_path = st.session_state.get("collection_source_image_path")
        source_image_bytes = read_binary_asset(source_image_path)
        if not source_image_bytes and st.session_state.collection:
            source_image_bytes = st.session_state.collection[0].get("original_image_bytes") or b""
        if source_image_bytes:
            archive.writestr(f"originals/{source_image_name}", source_image_bytes)

        for index, item in enumerate(st.session_state.collection, start=1):
            base_name = f"{index:02d}_{item['name'].strip().replace(' ', '_').lower() or 'cor'}"
            processed_extension = item.get("processed_image_extension") or "png"
            processed_bytes = read_binary_asset(item.get("processed_image_path")) or item.get("processed_image_bytes") or b""
            archive.writestr(f"processed/{base_name}.{processed_extension}", processed_bytes)
            manifest.append(
                {
                    "index": index,
                    "name": item["name"],
                    "hex": item["hex"],
                    "image_name": item.get("image_name") or source_image_name,
                    "source_image_name": source_image_name,
                    "processed_name": f"{base_name}.{processed_extension}",
                    "processed_mime": item.get("processed_image_mime") or "image/png",
                    "params": item.get("params") or {},
                    "debug": item.get("debug") or {},
                }
            )

        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=True, indent=2),
        )

    return buffer.getvalue()


def get_collection_zip_bytes() -> bytes:
    if st.session_state.collection_zip_bytes is None:
        st.session_state.collection_zip_bytes = build_collection_zip()
    return st.session_state.collection_zip_bytes

initialize_state()
migrate_collection_items_to_disk()

st.set_page_config(page_title="RazaiColor", layout="wide")

# CSS Brutalista
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

    :root {
        --color-bg: #FAFAFA;
        --color-surface: #FFFFFF;
        --color-surface-alt: #F4F4F5;
        --color-text: #171717;
        --color-text-muted: #737373;
        --color-border: #E5E5E5;
        --color-accent: #000000;
        --color-accent-soft: #F5F5F5;
        --color-success: #15803D;
        --color-success-bg: #F0FDF4;
        --color-error: #B91C1C;
        --color-error-bg: #FEF2F2;
        --radius: 8px;
        --font-size-xs: 0.75rem;
        --font-size-sm: 0.875rem;
        --font-size-base: 1rem;
        --font-size-lg: 1.25rem;
        --font-size-xl: 1.5rem;
        --line-height-tight: 1.2;
        --line-height-normal: 1.5;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', system-ui, sans-serif !important;
        background: var(--color-bg) !important;
        color: var(--color-text) !important;
        line-height: var(--line-height-normal) !important;
    }

    .stApp {
        background: var(--color-bg) !important;
    }

    .block-container {
        padding-top: 4rem !important;
        padding-bottom: 4rem !important;
        max-width: 1000px !important;
    }

    h1, h2, h3 {
        color: var(--color-text) !important;
        letter-spacing: -0.02em !important;
        font-weight: 600 !important;
        line-height: var(--line-height-tight) !important;
    }

    h1 {
        font-size: 2.5rem !important;
        margin-bottom: 0.5rem !important;
    }

    h3 {
        font-size: var(--font-size-base) !important;
        font-weight: 600 !important;
        color: var(--color-text) !important;
        border-bottom: 1px solid var(--color-border);
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem !important;
    }

    p, label, small {
        color: var(--color-text) !important;
    }

    [data-testid="column"] {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: var(--radius);
        padding: 2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    [data-testid="stFileUploader"] > label {
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        color: var(--color-text) !important;
    }

    /* Minimalist Dropzone */
    [data-testid="stFileUploadDropzone"] {
        border: 1px dashed var(--color-border) !important;
        border-radius: var(--radius) !important;
        background: var(--color-surface-alt) !important;
        padding: 3rem 1rem !important;
        transition: all 0.2s ease;
    }

    [data-testid="stFileUploadDropzone"]:hover {
        border-color: var(--color-text-muted) !important;
        background: var(--color-surface) !important;
    }

    [data-testid="stFileUploadDropzone"] * {
        color: var(--color-text-muted) !important;
    }

    /* Refined Buttons */
    .stButton > button {
        width: 100%;
        border-radius: var(--radius) !important;
        border: 1px solid var(--color-border) !important;
        background: var(--color-surface) !important;
        color: var(--color-text) !important;
        font-weight: 500 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }

    .stButton > button:hover {
        background: rgba(0,0,0,0.02) !important;
        border-color: var(--color-text-muted) !important;
    }

    .stButton > button:focus-visible {
        outline: 2px solid var(--color-text) !important;
        outline-offset: 2px !important;
    }

    /* Primary Accent Button */
    .stButton > button:active, 
    .stButton > button[kind="primary"] {
        background: var(--color-text) !important;
        color: var(--color-surface) !important;
        border-color: var(--color-text) !important;
        font-weight: 600 !important;
    }
    
    .stButton > button[kind="primary"] p,
    .stButton > button[kind="primary"] div {
        color: var(--color-surface) !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: var(--color-text-muted) !important;
        border-color: var(--color-text-muted) !important;
    }

    [data-testid="stImage"] {
        border-radius: var(--radius);
        overflow: hidden;
        border: 1px solid var(--color-border);
    }

    [data-testid="stAlertContainer"] {
        border-radius: var(--radius) !important;
        background: var(--color-success-bg) !important;
        border: 1px solid #BBF7D0 !important;
        color: var(--color-success) !important;
        padding: 1rem !important;
    }

    .hero-kicker {
        font-size: 0.875rem;
        color: var(--color-text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
        font-weight: 500;
    }

    .hero-copy {
        font-size: 1.125rem;
        color: var(--color-text-muted) !important;
        max-width: 600px;
        margin-bottom: 3rem;
        line-height: 1.6;
    }

    .preview-empty {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100%;
        min-height: 15rem;
        border: 1px dashed var(--color-border);
        border-radius: var(--radius);
        background: var(--color-surface-alt);
        color: var(--color-text-muted);
        text-align: center;
        font-size: 0.875rem;
    }

    .stage-bar {
        display: flex;
        gap: 2rem;
        margin-bottom: 3rem;
        border-bottom: 1px solid var(--color-border);
        padding-bottom: 1rem;
    }

    .stage-pill {
        color: var(--color-text-muted);
        font-weight: 500;
        font-size: 0.875rem;
    }

    .stage-pill.active {
        color: var(--color-text);
        font-weight: 600;
    }

    .field-caption {
        font-size: var(--font-size-xs);
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--color-text-muted);
        margin-bottom: 0.5rem;
    }

    .color-chip {
        height: 3rem;
        border-radius: var(--radius);
        border: 1px solid var(--color-border);
        margin-bottom: 1rem;
    }

    .collection-shell {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 1.5rem;
        align-items: start;
    }

    .collection-card {
        border-radius: var(--radius);
        border: 1px solid var(--color-border);
        background: var(--color-surface);
        overflow: hidden;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .collection-card:hover {
        border-color: var(--color-text-muted);
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    .collection-card-meta {
        padding: 0.75rem 1rem;
        font-size: var(--font-size-sm);
        border-top: 1px solid var(--color-border);
    }

    .preview-label {
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        color: var(--color-text-muted);
        text-transform: uppercase;
    }

    .preview-debug {
        margin-top: 1rem;
        padding: 1rem;
        border: 1px solid var(--color-border);
        border-radius: var(--radius);
        background: var(--color-surface-alt);
    }

    .preview-debug p {
        margin: 0;
        font-size: 0.8rem;
        color: var(--color-text-muted) !important;
    }

    .collection-card-name {
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .collection-card-hex {
        color: var(--color-text-muted);
        font-family: monospace;
        margin-top: 0.25rem;
    }

    .download-panel {
        margin-top: 3rem;
        padding-top: 3rem;
        border-top: 1px solid var(--color-border);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .stTextInput input {
        border-radius: var(--radius) !important;
        border: 1px solid var(--color-border) !important;
        padding: 0.5rem 1rem !important;
        font-size: var(--font-size-sm) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .stTextInput input:hover {
        border-color: var(--color-text-muted) !important;
    }

    .stTextInput input:focus-visible {
        outline: 2px solid var(--color-text) !important;
        outline-offset: 1px !important;
        border-color: transparent !important;
        box-shadow: none !important;
    }

    @media (max-width: 900px) {
        h1 {
            font-size: 3.2rem !important;
        }

        .block-container {
            padding-top: 2rem !important;
        }

    }

    @media (prefers-reduced-motion: reduce) {
        [data-testid="stFileUploadDropzone"],
        .stButton > button {
            transition-duration: 0.01ms !important;
        }
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-kicker">RazaiColor</div>', unsafe_allow_html=True)
st.title("Extração e Coleção de Cores")
st.markdown(
    '<p class="hero-copy">Faça o upload de imagens, identifique suas cores predominantes e monte uma coleção com preview de tonalidade em poucos passos.</p>',
    unsafe_allow_html=True,
)
st.markdown(
    f'''
    <div class="stage-bar">
        <div class="stage-pill {'active' if st.session_state.stage == 1 else ''}">1. Upload da Imagem</div>
        <div class="stage-pill {'active' if st.session_state.stage == 2 else ''}">2. Montar Coleção</div>
    </div>
    ''',
    unsafe_allow_html=True,
)

if st.session_state.stage == 1:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown("### Arquivo")
        uploaded_file = st.file_uploader(label="Selecione uma imagem", type=["png", "jpg", "jpeg", "webp"])

        if uploaded_file is not None:
            save_uploaded_file(uploaded_file)
            if st.button("Confirmar upload"):
                st.session_state.stage = 2
                st.rerun()

    with col2:
        st.markdown("### Preview")
        if uploaded_file is not None:
            st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
        elif st.session_state.uploaded_image_bytes:
            st.image(
                st.session_state.uploaded_image_bytes,
                caption=st.session_state.uploaded_image_name,
                use_container_width=True,
            )
        else:
            st.markdown(
                """
                <div class="preview-empty">
                    <div>
                        <p style="font-weight: 500; font-size: 1rem; color: var(--color-text);">Nenhuma imagem selecionada</p>
                        <p style="margin-top: 0.25rem;">Preview aparecerá aqui</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

if st.session_state.stage == 2:
    header_col1, header_col2 = st.columns([0.8, 0.2])
    with header_col1:
        st.markdown("### Configuração e Recoloração")
    with header_col2:
        if st.button("← Trocar Imagem"):
            st.session_state.stage = 1
            st.rerun()

    settings_col, preview_col = st.columns([4.0, 6.0], gap="large")

    with settings_col:
        st.markdown('<p class="field-caption" style="margin-top:0;">DADOS DA COR</p>', unsafe_allow_html=True)
        col_name, col_hex = st.columns([3, 2], gap="small")
        with col_name:
            color_name = st.text_input(
                "NOME",
                placeholder="Ex.: Azul Oceano",
                label_visibility="collapsed",
                key="color_name_input",
                autocomplete="off",
            )
        with col_hex:
            color_hex = st.text_input(
                "HEX",
                placeholder="#0055A4",
                max_chars=7,
                label_visibility="collapsed",
                key="color_hex_input",
                autocomplete="off",
            )
        
        normalized_hex = normalize_hex(color_hex)
        swatch_hex = normalized_hex or "transparent"

        st.markdown(
            f'''
            <div style="display: flex; align-items: center; gap: 1rem; margin-top: 0.5rem; margin-bottom: 2rem;">
                <div class="color-chip" style="background:{swatch_hex}; margin: 0; width: 48px; height: 48px; flex-shrink: 0; border: 1px solid var(--color-border); border-radius: var(--radius);"></div>
                <div style="font-size: 0.875rem; color: var(--color-text-muted);">
                    {'Preview da cor alvo' if normalized_hex else 'Aguardando código hex'}
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )

        st.divider()

        header_col, reset_col = st.columns([1, 0.5])
        with header_col:
            st.markdown('<p class="field-caption">AJUSTES FINOS</p>', unsafe_allow_html=True)
        with reset_col:
            if st.button("Reset", use_container_width=True, help="Voltar aos valores padrão"):
                reset_slider_defaults()
                st.rerun()

        color_strength = st.slider(
            "Saturação / Força da Cor",
            min_value=0.0, max_value=3.0, value=DEFAULT_COLOR_STRENGTH, step=0.01,
            key="color_strength_slider",
            help="Controla quanto da cor alvo entra na imagem. Valores acima de 1 forçam a saturação."
        )
        luminance_strength = st.slider(
            "Referência de Luminosidade",
            min_value=0.0, max_value=1.0, value=DEFAULT_LUMINANCE_STRENGTH, step=0.01,
            key="luminance_strength_slider",
            help="Mistura a luminosidade da cor alvo com a do tecido."
        )
        lightness_offset = st.slider(
            "Ajuste Global de Luz",
            min_value=-40.0, max_value=40.0, value=DEFAULT_LIGHTNESS_OFFSET, step=1.0,
            key="lightness_offset_slider",
            help="Escurece (-) ou clareia (+) a imagem final de forma global."
        )
        shadow_protection = st.slider(
            "Proteção de Sombras",
            min_value=0.0, max_value=1.0, value=DEFAULT_SHADOW_PROTECTION, step=0.01,
            key="shadow_protection_slider",
            help="Reduz o efeito do ajuste nas áreas escuras, preservando o volume do tecido."
        )

        st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
        if st.button("Adicionar à Coleção", type="primary", use_container_width=True, on_click=submit_current_selection_to_collection):
            pass

    with preview_col:
        st.markdown(
            '<div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom: 0.5rem;">'
            '<p class="field-caption" style="margin:0;">VISUALIZAÇÃO (LIVE PREVIEW RÁPIDO)</p>'
            '<small style="color:var(--color-text-muted);">A imagem final será gerada em alta resolução ao adicionar à coleção</small>'
            '</div>', 
            unsafe_allow_html=True
        )
        
        if normalized_hex and st.session_state.uploaded_image_bytes:
            update_live_preview(normalized_hex, color_strength, luminance_strength, lightness_offset, shadow_protection)
        else:
            st.session_state.live_preview_rgb = None
            st.session_state.live_preview_signature = None
            st.session_state.live_processing_debug = None

        live_preview_image = st.session_state.live_preview_rgb
        if live_preview_image is None:
            live_preview_image = st.session_state.processed_preview_rgb

        if live_preview_image is not None:
            st.image(
                live_preview_image,
                caption=f"{color_name} ({normalized_hex})" if normalized_hex else "Pré-visualização",
                use_container_width=True,
            )

            # ── Download individual da imagem atual (resolução total) ──
            if normalized_hex and st.session_state.uploaded_image_bytes:
                download_label = f"{color_name}_{normalized_hex.lstrip('#')}.png" if color_name else f"recolor_{normalized_hex.lstrip('#')}.png"
                generate_recolor_preview(
                    normalized_hex, color_strength, luminance_strength,
                    lightness_offset, shadow_protection,
                )
                full_res_bytes = st.session_state.processed_image_bytes
                if full_res_bytes:
                    st.download_button(
                        label="⬇ Baixar imagem atual",
                        data=full_res_bytes,
                        file_name=download_label,
                        mime="image/png",
                        use_container_width=True,
                        key="download_single_image",
                    )
        else:
            st.markdown(
                '<div class="preview-empty" style="min-height: 38rem;">'
                '<div>'
                '<p style="font-weight: 500; font-size: 1rem; color: var(--color-text);">Aguardando cor alvo</p>'
                '<p style="margin-top: 0.25rem;">Insira o código hexadecimal na lateral para iniciar</p>'
                '</div>'
                '</div>',
                unsafe_allow_html=True,
            )

        debug = st.session_state.live_processing_debug or st.session_state.processing_debug
        if debug:
            with st.expander("🛠 Detalhes Técnicos & Depuração do Motor", expanded=False):
                st.markdown(
                    f'''
                    <div class="preview-debug">
                        <p><strong>Clipped Ratio:</strong> {debug.get("clipped_ratio", 0.0):.4f}</p>
                        <p><strong>Max Overflow:</strong> {debug.get("max_overflow", 0.0):.4f}</p>
                        <p><strong>Mean Weight:</strong> {debug.get("mean_weight", 0.0):.4f}</p>
                        <p><strong>Color Strength Base:</strong> {debug.get("base_color_strength", 0.0):.4f}</p>
                        <p><strong>Luminance Impact:</strong> {debug.get("mean_luminance_application", 0.0):.4f}</p>
                        <p><strong>Lightness Offset Mod:</strong> {debug.get("lightness_offset", 0.0):.4f}</p>
                        <p><strong>Protect Threshold:</strong> {debug.get("shadow_protection", 0.0):.4f}</p>
                        <p><strong>Shadow Depth Boost:</strong> {debug.get("mean_shadow_depth_boost", 0.0):.4f}</p>
                    </div>
                    ''',
                    unsafe_allow_html=True,
                )

    st.markdown('<div style="margin-top: 4rem;"></div>', unsafe_allow_html=True)
    collection_header_col, collection_toggle_col = st.columns([2.6, 1.1], gap="large")
    with collection_header_col:
        st.markdown("### Coleção de Cores Exportáveis")
        if st.session_state.collection:
            st.caption(f"{len(st.session_state.collection)} cores armazenadas na coleção.")
    with collection_toggle_col:
        toggle_label = "Ocultar Coleção" if st.session_state.collection_panel_expanded else "Mostrar Coleção"
        if st.button(toggle_label, key="toggle_collection_panel", use_container_width=True, disabled=not st.session_state.collection):
            st.session_state.collection_panel_expanded = not st.session_state.collection_panel_expanded
            st.rerun()

    if not st.session_state.collection:
        st.markdown(
            '<div class="preview-empty" style="min-height: 8rem; border-style: dashed;">'
            '<div><p>A coleção está vazia. Gere e adicione cores na seção acima.</p></div>'
            '</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state.collection_panel_expanded:
        ensure_collection_page_in_bounds()
        total_items = len(st.session_state.collection)
        page_size = st.session_state.collection_page_size
        total_pages = max(1, int(np.ceil(total_items / page_size)))
        page = st.session_state.collection_page

        summary_col, pager_col = st.columns([2.2, 1.4], gap="large")
        with summary_col:
            st.caption(f"{total_items} cores na coleção. Exibindo {page_size} por vez para manter a interface responsiva.")
        with pager_col:
            prev_col, page_info_col, next_col = st.columns([1, 1.4, 1], gap="small")
            with prev_col:
                if st.button("Anterior", key="collection_page_prev", use_container_width=True, disabled=page <= 1):
                    st.session_state.collection_page = max(1, page - 1)
                    st.rerun()
            with page_info_col:
                st.markdown(
                    f'<div style="text-align:center; padding-top:0.4rem; font-size:0.875rem; color:var(--color-text-muted);">Página {page} de {total_pages}</div>',
                    unsafe_allow_html=True,
                )
            with next_col:
                if st.button("Próxima", key="collection_page_next", use_container_width=True, disabled=page >= total_pages):
                    st.session_state.collection_page = min(total_pages, page + 1)
                    st.rerun()

        page_start = (page - 1) * page_size
        page_end = page_start + page_size
        visible_items = st.session_state.collection[page_start:page_end]
        collection_columns_count = 4
        for row_start in range(0, len(visible_items), collection_columns_count):
            row_items = visible_items[row_start : row_start + collection_columns_count]
            row_columns = st.columns(collection_columns_count, gap="large")
            for offset, item in enumerate(row_items):
                item_index = page_start + row_start + offset
                processed_image_ref = item.get("processed_image_path") or item.get("processed_image_bytes")
                image_size_label = bytes_to_mb_label(processed_image_ref)
                display_image_ref = item.get("display_image_path") or item.get("display_image_bytes")
                if not display_image_ref and item.get("processed_image_bytes"):
                    display_image_ref = build_collection_thumbnail_bytes(item["processed_image_bytes"])
                    item["display_image_bytes"] = display_image_ref
                with row_columns[offset]:
                    st.image(display_image_ref, use_container_width=True)
                    st.markdown(f"**{item['name']}**")
                    st.markdown(item["hex"])
                    st.caption(image_size_label)
                    if st.button("Excluir", key=f"delete_collection_item_{item_index}", use_container_width=True):
                        remove_collection_item(item_index)
                        st.rerun()
    else:
        st.caption("Coleção recolhida para reduzir o custo de renderização durante os ajustes de cor.")

    st.markdown('<div style="margin-top: 1.5rem;"></div>', unsafe_allow_html=True)
    compression_info_col, compression_action_col = st.columns([2.3, 1.2], gap="large")
    collection_requires_compression = any(
        collection_item_exceeds_download_limit(item) for item in st.session_state.collection
    )
    with compression_info_col:
        if st.session_state.collection and not collection_requires_compression:
            st.markdown(
                '<p class="field-caption" style="margin-bottom:0.35rem;">PREPARO PARA DOWNLOAD</p>'
                '<p style="font-size:0.875rem; color:var(--color-text-muted); margin:0;">Todas as imagens da colecao ja estao dentro do limite de 2 MB. O ZIP pode ser baixado sem compressao adicional.</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<p class="field-caption" style="margin-bottom:0.35rem;">PREPARO PARA DOWNLOAD</p>'
                '<p style="font-size:0.875rem; color:var(--color-text-muted); margin:0;">A compressao final so sera aplicada nas imagens que ultrapassarem 2 MB. Quando todas estiverem dentro do limite, o ZIP sera liberado.</p>',
                unsafe_allow_html=True,
            )
    with compression_action_col:
        if st.session_state.collection:
            if collection_requires_compression:
                if st.button("Comprimir Colecao para Download", use_container_width=True):
                    compressed_count, items_to_compress, total_items = compress_collection_for_download()
                    st.success(
                        f"Compressao concluida: {compressed_count}/{items_to_compress} imagens processadas. Colecao total: {total_items}."
                    )
            else:
                st.button("Colecao Ja Pronta para Download", disabled=True, use_container_width=True)
        else:
            st.button("Comprimir Colecao para Download", disabled=True, use_container_width=True)

    st.markdown('<div style="margin-top: 3rem; padding-top: 3rem; border-top: 1px solid var(--color-border);"></div>', unsafe_allow_html=True)
    download_info_col, download_action_col = st.columns([2.5, 1.1], gap="large")
    with download_info_col:
        st.markdown("### Download do Pacote de Produção")
        st.caption("Baixe um arquivo ZIP contendo sua coleção renderizada. Se alguma imagem ultrapassar 2 MB, apenas ela precisará ser comprimida antes do download.")
    with download_action_col:
        if st.session_state.collection and st.session_state.collection_ready_for_download:
            if st.session_state.collection_zip_bytes is None:
                if st.button("Preparar ZIP para Download", type="primary", use_container_width=True, key="prepare_collection_zip_button"):
                    with st.spinner("Gerando ZIP da colecao..."):
                        get_collection_zip_bytes()
                    st.rerun()
            else:
                st.download_button(
                    label="Baixar Coleção (.zip)",
                    data=st.session_state.collection_zip_bytes,
                    file_name="razaicolor_collection.zip",
                    mime="application/zip",
                    type="primary",
                    use_container_width=True,
                    key="download_collection_zip_button",
                )
                st.caption(f"ZIP pronto: {bytes_to_mb_label(st.session_state.collection_zip_bytes)}")
        else:
            st.button("Baixar Coleção (.zip) Indisponível", disabled=True, use_container_width=True)
