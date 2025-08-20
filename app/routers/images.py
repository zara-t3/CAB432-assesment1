# app/routers/images.py
import os, uuid, mimetypes, time
from datetime import datetime
from flask import Blueprint, current_app, request, jsonify, send_file, g
from PIL import Image
from ..auth import auth_required
from ..models.store import IMAGES

images_bp = Blueprint("images", __name__)

@images_bp.post("")
@auth_required
def upload():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"error": "missing name"}), 400
    img_id = str(uuid.uuid4())
    user = g.user["username"]
    folder = os.path.join(current_app.config["DATA_DIR"], "images", user, img_id)
    os.makedirs(folder, exist_ok=True)
    orig_path = os.path.join(folder, "original.jpg")
    f.save(orig_path)
    IMAGES[img_id] = {
        "id": img_id, "name": name, "owner": user, "orig_path": orig_path,
        "processed_path": None, "created_at": datetime.utcnow().isoformat(),
    }
    return jsonify({"id": img_id, "name": name})

@images_bp.get("")
@auth_required
def list_images():
    limit  = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    items = list(IMAGES.values())
    if g.user["role"] != "admin":
        items = [i for i in items if i["owner"] == g.user["username"]]
    total = len(items)

    # sanitize output: only expose relevant fields
    clean_items = [
        {
            "id": i["id"],
            "name": i["name"],
            "owner": i["owner"],
            "created_at": i["created_at"],
            "processed_path": i.get("processed_path"),
        }
        for i in items[offset:offset+limit]
    ]

    return jsonify({"total": total, "items": clean_items})


@images_bp.get("/<img_id>")
@auth_required
def get_meta(img_id):
    rec = IMAGES.get(img_id)
    if not rec or (g.user["role"] != "admin" and rec["owner"] != g.user["username"]):
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "id": rec["id"],
        "name": rec["name"],
        "owner": rec["owner"],
        "created_at": rec["created_at"],
        "processed_path": rec.get("processed_path"),
    })


@images_bp.get("/<img_id>/file")
@auth_required
def get_file(img_id):
    version = request.args.get("version", "original")
    download = request.args.get("download") in ("1", "true", "yes")

    rec = IMAGES.get(img_id)
    if not rec or (g.user["role"] != "admin" and rec["owner"] != g.user["username"]):
        return jsonify({"error": "not found"}), 404

    base_dir = os.path.dirname(rec["orig_path"])

    if version == "thumb":
        thumb_path = os.path.join(base_dir, "thumb_160.jpg")
        if not os.path.exists(thumb_path):
            img = Image.open(rec["orig_path"]).convert("RGB")
            img.thumbnail((160, 160), Image.Resampling.LANCZOS)
            img.save(thumb_path, quality=80, optimize=True)
        path = thumb_path
    elif version == "processed":
        path = rec.get("processed_path")
    else:
        path = rec["orig_path"]

    if not path or not os.path.exists(path):
        return jsonify({"error": "file not ready"}), 404

    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return send_file(
        path, mimetype=mime,
        as_attachment=download,
        download_name=os.path.basename(path)
    )

