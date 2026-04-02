# utils/downloader.py — Image download & fal.ai upload helpers

import os
from pathlib import Path
import requests
import fal_client


def download_image(url: str, output_path: Path) -> bool:
    """Download a single image from URL to output_path. Returns True on success."""
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        output_path.write_bytes(resp.content)
        return True
    except requests.RequestException as e:
        print(f"    [ERR] Download failed for {url.split('/')[-1]}: {e}")
        return False


def download_product_images(product: dict, inputs_dir: Path) -> list[Path]:
    """
    Download all image_urls from the product definition into inputs_dir.
    Skips files that already exist. Returns list of saved paths.
    """
    saved = []
    urls = product.get("image_urls", [])
    for i, url in enumerate(urls, start=1):
        # Derive extension from URL, default to .jpg
        ext = url.split("?")[0].rsplit(".", 1)[-1].lower()
        if ext not in ("jpg", "jpeg", "png", "webp"):
            ext = "jpg"
        dest = inputs_dir / f"product_{i:02d}.{ext}"

        if dest.exists():
            print(f"    [SKIP] {dest.name} already exists.")
            saved.append(dest)
            continue

        print(f"    [{i}/{len(urls)}] Downloading → {dest.name} ...", end=" ", flush=True)
        if download_image(url, dest):
            print("OK")
            saved.append(dest)
        else:
            print("FAILED")

    return saved


def upload_to_fal(file_path: Path) -> str:
    """
    Upload a local image file to fal.ai CDN and return the hosted URL.
    Use this to pass processed reference images to video generation.
    """
    with open(file_path, "rb") as f:
        # Determine MIME type
        ext = file_path.suffix.lower()
        mime = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(ext, "image/jpeg")
        url = fal_client.upload(f.read(), content_type=mime)
    return url
