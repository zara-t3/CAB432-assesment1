import os, uuid
from datetime import datetime
from flask import Blueprint, current_app, request, jsonify, send_file, g
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
        "processed_path": None, "created_at": datetime.utcnow().isoformat()
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
    version = request.args.get("version", "original")
    rec = IMAGES.get(img_id)
    if not rec or (g.user["role"] != "admin" and rec["owner"] != g.user["username"]):
        return jsonify({"error": "not found"}), 404
    path = rec["orig_path"] if version == "original" else rec["processed_path"]
    if not path or not os.path.exists(path):
        return jsonify({"error": "file not ready"}), 404
    return send_file(path, mimetype="image/jpeg")
