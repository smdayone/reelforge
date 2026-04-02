# utils/image_processor.py — Image pre-processing for video generation
#
# Capabilities:
#   1. Background removal (rembg + ONNX)
#   2. Text / watermark detection & inpainting (OpenCV)
#   3. Image normalization and resize for optimal fal.ai input

from pathlib import Path
from PIL import Image, ImageFilter
import io

# rembg is imported lazily so startup is fast even if model isn't cached yet
_rembg_remove = None


def _get_rembg():
    global _rembg_remove
    if _rembg_remove is None:
        try:
            from rembg import remove
            _rembg_remove = remove
        except ImportError:
            raise ImportError(
                "rembg is not installed. Run: pip3 install rembg onnxruntime"
            )
    return _rembg_remove


# ---------------------------------------------------------------------------
# Background removal
# ---------------------------------------------------------------------------

def remove_background(
    input_path: Path,
    output_path: Path,
    bg_color: tuple | None = (0, 0, 0, 0),  # transparent by default
    white_bg: bool = False,
) -> Path:
    """
    Remove the background from an image and save the result.

    Args:
        input_path:  Source image path.
        output_path: Destination path (PNG recommended for transparency).
        bg_color:    RGBA tuple for background fill (None = keep transparent).
        white_bg:    If True, composite result on pure white background.

    Returns:
        output_path on success.
    """
    remove = _get_rembg()

    with open(input_path, "rb") as f:
        raw = f.read()

    # Run background removal (downloads ONNX model on first run ~170MB)
    print(f"    [BG]  Removing background: {input_path.name} ...", end=" ", flush=True)
    result_bytes = remove(raw)
    img = Image.open(io.BytesIO(result_bytes)).convert("RGBA")

    if white_bg:
        # Composite on white
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background.convert("RGB")
        output_path = output_path.with_suffix(".jpg")
    elif bg_color:
        background = Image.new("RGBA", img.size, bg_color)
        background.paste(img, mask=img.split()[3])
        img = background

    img.save(output_path)
    print("OK")
    return output_path


# ---------------------------------------------------------------------------
# Text / watermark inpainting
# ---------------------------------------------------------------------------

def remove_text_watermarks(input_path: Path, output_path: Path) -> Path:
    """
    Detect and inpaint text/watermark regions using OpenCV.

    This uses a simple heuristic: detects near-white semi-transparent regions
    with sharp edges (typical of CJ Dropshipping URL overlays) and fills them
    via cv2.inpaint (Telea algorithm).

    Note: For complex watermarks, consider using fal-ai/imageutils/rembg or
    a dedicated inpainting model. This covers most supplier-logo overlays.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("    [WARN] opencv-python not available, skipping text removal.")
        import shutil
        shutil.copy2(input_path, output_path)
        return output_path

    print(f"    [TXT] Detecting text/watermarks: {input_path.name} ...", end=" ", flush=True)

    img = cv2.imread(str(input_path))
    if img is None:
        print("SKIP (unreadable)")
        import shutil
        shutil.copy2(input_path, output_path)
        return output_path

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # --- Strategy 1: detect near-white text overlays (typical supplier watermarks)
    _, white_mask = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY)

    # Morphological cleanup: remove tiny noise, keep text-shaped blobs
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_DILATE, kernel, iterations=2)

    # --- Strategy 2: detect high-frequency text edges (Canny)
    edges = cv2.Canny(gray, 100, 200)
    edge_mask = cv2.dilate(edges, kernel, iterations=1)

    # Combine masks only in regions that are also bright (avoid product edges)
    combined = cv2.bitwise_and(white_mask, edge_mask)

    # Check if mask is non-trivial (>0.1% of image area)
    mask_area = cv2.countNonZero(combined)
    total_area = img.shape[0] * img.shape[1]

    if mask_area / total_area > 0.001:
        result = cv2.inpaint(img, combined, inpaintRadius=5, flags=cv2.INPAINT_TELEA)
    else:
        result = img  # nothing significant detected

    cv2.imwrite(str(output_path), result)
    print(f"OK (masked {mask_area} px)")
    return output_path


# ---------------------------------------------------------------------------
# Full pipeline: input → reference
# ---------------------------------------------------------------------------

def process_reference_image(
    input_path: Path,
    references_dir: Path,
    remove_bg: bool = True,
    remove_text: bool = True,
    white_bg: bool = False,
) -> Path:
    """
    Full processing pipeline for a single input image:
      1. Optionally remove background
      2. Optionally remove text/watermarks
      3. Save as reference image

    Returns the path to the saved reference image.
    """
    stem = input_path.stem
    # PNG for transparency, JPG for white-bg
    ext = ".jpg" if white_bg else ".png"
    output_path = references_dir / f"{stem}_ref{ext}"

    if output_path.exists():
        print(f"    [SKIP] {output_path.name} already exists.")
        return output_path

    current_path = input_path

    # Step 1: background removal
    if remove_bg:
        tmp_bg = references_dir / f"{stem}_nobg.png"
        current_path = remove_background(current_path, tmp_bg, white_bg=white_bg)

    # Step 2: text / watermark removal
    if remove_text:
        tmp_txt = references_dir / f"{stem}_clean{ext}"
        current_path = remove_text_watermarks(current_path, tmp_txt)

    # Rename final result to reference filename
    if current_path != output_path:
        output_path.write_bytes(current_path.read_bytes())
        # Clean up intermediary temp files
        for tmp in [
            references_dir / f"{stem}_nobg.png",
            references_dir / f"{stem}_clean{ext}",
        ]:
            if tmp.exists() and tmp != output_path:
                tmp.unlink()

    return output_path


def process_all_references(
    inputs_dir: Path,
    references_dir: Path,
    remove_bg: bool = True,
    remove_text: bool = True,
    white_bg: bool = False,
) -> list[Path]:
    """Process all images in inputs_dir and return list of reference paths."""
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    images = [p for p in inputs_dir.iterdir() if p.suffix.lower() in exts]

    if not images:
        print("    [WARN] No images found in inputs/")
        return []

    refs = []
    for i, img_path in enumerate(sorted(images), start=1):
        print(f"  [{i}/{len(images)}] Processing: {img_path.name}")
        ref = process_reference_image(
            img_path, references_dir,
            remove_bg=remove_bg,
            remove_text=remove_text,
            white_bg=white_bg,
        )
        refs.append(ref)

    return refs
