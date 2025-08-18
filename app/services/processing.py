import os
from PIL import Image, ImageFilter

def run_pipeline(path_in: str, path_out: str, steps: list[str], repeat: int = 1):
    img = Image.open(path_in).convert("RGB")
    for _ in range(int(repeat)):
        for s in steps:
            if s == "resize_4k":
                img = img.resize((3840, 2160))
            elif s == "gaussian_blur":
                img = img.filter(ImageFilter.GaussianBlur(3))
            elif s == "sharpen":
                img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150))
            elif s == "edges":
                img = img.filter(ImageFilter.FIND_EDGES)
    os.makedirs(os.path.dirname(path_out), exist_ok=True)
    img.save(path_out, quality=95)
