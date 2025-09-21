import os
import time
import json
from typing import List, Dict
from PIL import Image, ImageFilter
from mtcnn import MTCNN
import numpy as np

_detector = None

def _get_detector() -> MTCNN:
    global _detector
    if _detector is None:
        _detector = MTCNN()  # Loads MTCNN once (CPU)
    return _detector

def face_blur_and_variants(
    path_in: str,
    out_dir: str,
    blur_strength: int = 12,
    extra_passes: int = 0
) -> List[Dict]:
    base = Image.open(path_in).convert("RGB")
    W, H = base.size

    det = _get_detector()

    
    img_np = np.asarray(base)  
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

    # Save output files and create metadata
    outputs = []
    
  
    fhd_webp_path = os.path.join(out_dir, "fhd_1080.webp")
    fhd_work = work.copy()
    if max(W, H) > 1080:
        ratio = 1080 / max(W, H)
        new_w, new_h = int(W * ratio), int(H * ratio)
        fhd_work = fhd_work.resize((new_w, new_h), Image.Resampling.LANCZOS)
    fhd_work.save(fhd_webp_path, "WEBP", quality=85, optimize=True)
    outputs.append({"name": "fhd_1080.webp", "path": fhd_webp_path})
    
 
    fhd_jpg_path = os.path.join(out_dir, "fhd_1080.jpg")
    fhd_work.save(fhd_jpg_path, "JPEG", quality=85, optimize=True)
    outputs.append({"name": "fhd_1080.jpg", "path": fhd_jpg_path})
   
    metadata = {
        "faces_detected": len(results),
        "blur_strength": blur_strength,
        "extra_passes": extra_passes,
        "original_size": [W, H],
        "processing_time": time.time()
    }

    return outputs, metadata
