# app/routers/images.py
import os, uuid, mimetypes
from datetime import datetime
from flask import Blueprint, current_app, request, jsonify, send_file, g
from PIL import Image
import requests

from ..auth import auth_required
from ..models.store import IMAGES

images_bp = Blueprint("images", __name__)

@images_bp.post("")
@auth_required
def upload():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400
    img_id = str(uuid.uuid4())
    user = g.user["username"]
    folder = os.path.join(current_app.config["DATA_DIR"], "images", user, img_id)
    os.makedirs(folder, exist_ok=True)
    orig_path = os.path.join(folder, "original.jpg")
    f.save(orig_path)
    IMAGES[img_id] = {
        "id": img_id, "owner": user, "orig_path": orig_path,
        "processed_path": None, "created_at": datetime.utcnow().isoformat(),
        "variants": []
    }
    return jsonify({"id": img_id})

@images_bp.get("")
@auth_required
def list_images():
    limit  = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    items = list(IMAGES.values())
    if g.user["role"] != "admin":
        items = [i for i in items if i["owner"] == g.user["username"]]
    total = len(items)
    return jsonify({"total": total, "items": items[offset:offset+limit]})

@images_bp.get("/<img_id>")
@auth_required
def get_meta(img_id):
    rec = IMAGES.get(img_id)
    if not rec or (g.user["role"] != "admin" and rec["owner"] != g.user["username"]):
        return jsonify({"error": "not found"}), 404
    return jsonify(rec)

@images_bp.get("/<img_id>/file")
@auth_required
def get_file(img_id):
    version = request.query_string and request.args.get("version", "original")
    variant_name = request.args.get("variant")  # e.g., 'fhd_1080.webp'
    download = request.args.get("download") in ("1", "true", "yes")

    rec = IMAGES.get(img_id)
    if not rec or (g.user["role"] != "admin" and rec["owner"] != g.user["username"]):
        return jsonify({"error": "not found"}), 404

    base_dir = os.path.dirname(rec["orig_path"])

    # 1) Explicit variant by name
    if variant_name:
        for v in rec.get("variants", []):
            if v.get("name") == variant_name and os.path.exists(v.get("path", "")):
                mime = mimetypes.guess_type(v["path"])[0] or "application/octet-stream"
                return send_file(
                    v["path"], mimetype=mime,
                    as_attachment=download, download_name=os.path.basename(v["path"])
                )
        return jsonify({"error": f"variant '{variant_name}' not found"}), 404

    # 2) Tiny on-demand thumbnail
    if version == "thumb":
        thumb_path = os.path.join(base_dir, "thumb_160.jpg")
        if not os.path.exists(thumb_path):
            img = Image.open(rec["orig_path"]).convert("RGB")
            img.thumbnail((160, 160), Image.Resampling.LANCZOS)
            img.save(thumb_path, quality=80, optimize=True)
        path = thumb_path
    else:
        path = rec["orig_path"] if version == "original" else rec.get("processed_path")

    if not path or not os.path.exists(path):
        return jsonify({"error": "file not ready"}), 404

    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return send_file(
        path, mimetype=mime,
        as_attachment=download, download_name=os.path.basename(path)
    )
