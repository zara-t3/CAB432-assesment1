import os
from typing import List, Dict, Tuple
from PIL import Image, ImageFilter
from mtcnn import MTCNN
import numpy as np   # ✅ add this

_detector = None

def _get_detector() -> MTCNN:
    global _detector
    if _detector is None:
        _detector = MTCNN()  # Loads MTCNN once (CPU)
    return _detector

def _save_jpg(img: Image.Image, path: str, quality: int = 82):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, format="JPEG", quality=quality, subsampling=2, progressive=True, optimize=True)

def _save_webp(img: Image.Image, path: str, quality: int = 80):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, format="WEBP", quality=quality, method=6)

def _downscale_fit(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    o = img.copy()
    o.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
    return o

def face_blur_and_variants(
    path_in: str,
    out_dir: str,
    blur_strength: int = 12,
    extra_passes: int = 0
) -> Tuple[Image.Image, List[Dict]]:
    base = Image.open(path_in).convert("RGB")
    W, H = base.size

    det = _get_detector()

    
    img_np = np.asarray(base)  # shape=(H,W,3), dtype=uint8
    results = det.detect_faces(img_np)

    work = base.copy()
    for r in results:
        x, y, w, h = r.get("box", [0, 0, 0, 0])
        x = max(0, x); y = max(0, y); w = max(1, w); h = max(1, h)
        x2 = min(W, x + w); y2 = min(H, y + h)
        face = work.crop((x, y, x2, y2))
        passes = max(2, blur_strength // 6)
        for _ in range(passes):
            face = face.filter(ImageFilter.GaussianBlur(radius=6))
        work.paste(face, (x, y))

    for _ in range(int(extra_passes)):
        work = work.filter(ImageFilter.UnsharpMask(radius=0.8, percent=110, threshold=2))

    targets = [
        ("thumb_160", 160, 160, 75),
        ("thumb_320", 320, 320, 75),
        ("hd_720",   1280, 720, 82),
        ("fhd_1080", 1920, 1080, 85),
        ("uhd_4k",   3840, 2160, 90),
    ]

    variants: List[Dict] = []
    for name, tw, th, q in targets:
        vimg = _downscale_fit(work, tw, th)
        jp = os.path.join(out_dir, f"{name}.jpg")
        wp = os.path.join(out_dir, f"{name}.webp")
        _save_jpg(vimg, jp, q)
        _save_webp(vimg, wp, max(q - 5, 70))
        variants.append({"name": f"{name}.jpg",  "path": jp, "mime": "image/jpeg"})
        variants.append({"name": f"{name}.webp", "path": wp, "mime": "image/webp"})

    return work, variants
