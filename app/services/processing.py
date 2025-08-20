# app/services/processing.py
import os
from PIL import Image, ImageFilter

def _save_jpg(img: Image.Image, path: str, quality: int = 82):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, format="JPEG", quality=quality, subsampling=2, progressive=True, optimize=True)

def _save_webp(img: Image.Image, path: str, quality: int = 80):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, format="WEBP", quality=quality, method=6)

def _variant_meta(name: str, path: str, mime: str):
    size = os.path.getsize(path) if os.path.exists(path) else None
    return {"name": name, "path": path, "mime": mime, "size_bytes": size}

def _downscale_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Downscale with LANCZOS, never upscale."""
    w, h = img.size
    if w <= target_w and h <= target_h:
        return img.copy()
    out = img.copy()
    out.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
    # light sharpen to keep it crisp
    out = out.filter(ImageFilter.UnsharpMask(radius=0.6, percent=120, threshold=2))
    return out

def web_optimize_variants(path_in: str, out_dir: str, extra_passes: int = 0):
    """
    Create crisp web-ready variants (JPG + WEBP) without upscaling.
    extra_passes: additional light detail passes for CPU load (doesn't blur).
    """
    base = Image.open(path_in).convert("RGB")

    targets = [
        ("thumb_160", 160, 160, 75),
        ("thumb_320", 320, 320, 75),
        ("hd_720",   1280, 720, 82),
        ("fhd_1080", 1920, 1080, 85),
        ("uhd_4k",   3840, 2160, 90),  # only if original >= 4K
    ]

    variants = []
    for name, W, H, q in targets:
        img = _downscale_fit(base, W, H)
        # optional extra light sharpening passes to increase CPU
        for _ in range(int(extra_passes)):
            img = img.filter(ImageFilter.UnsharpMask(radius=0.8, percent=110, threshold=2))

        jpg_path = os.path.join(out_dir, f"{name}.jpg")
        _save_jpg(img, jpg_path, quality=q)
        variants.append(_variant_meta(name + ".jpg", jpg_path, "image/jpeg"))

        webp_path = os.path.join(out_dir, f"{name}.webp")
        _save_webp(img, webp_path, quality=max(q - 5, 70))
        variants.append(_variant_meta(name + ".webp", webp_path, "image/webp"))

    return variants
