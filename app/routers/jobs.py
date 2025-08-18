import os, uuid, time
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from ..auth import auth_required
from ..models.store import IMAGES, JOBS
from ..services.processing import run_pipeline

jobs_bp = Blueprint("jobs", __name__)

@jobs_bp.post("")
@auth_required
def create_job():
    data = request.get_json(force=True, silent=True) or {}
    img_id = data.get("image_id")
    steps  = data.get("pipeline", ["resize_4k","gaussian_blur","sharpen"])
    repeat = int(data.get("repeat", 5))

    rec = IMAGES.get(img_id)
    if not rec or (g.user["role"] != "admin" and rec["owner"] != g.user["username"]):
        return jsonify({"error": "image not found"}), 404

    job_id = str(uuid.uuid4())
    out_path = os.path.join(os.path.dirname(rec["orig_path"]), "processed.jpg")
    start = time.time()
    # CPU-bound work inline (single-process requirement)
    run_pipeline(rec["orig_path"], out_path, steps, repeat)
    duration_ms = int((time.time() - start) * 1000)

    rec["processed_path"] = out_path
    JOBS[job_id] = {
        "id": job_id, "owner": rec["owner"], "image_id": img_id,
        "steps": steps, "repeat": repeat, "status": "done",
        "output_path": out_path, "duration_ms": duration_ms,
        "created_at": datetime.utcnow().isoformat()
    }
    return jsonify({"job_id": job_id, "status": "done", "duration_ms": duration_ms})

@jobs_bp.get("")
@auth_required
def list_jobs():
    limit  = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    owner  = request.args.get("owner")
    items = list(JOBS.values())
    if g.user["role"] != "admin":
        items = [j for j in items if j["owner"] == g.user["username"]]
    if owner:
        items = [j for j in items if j["owner"] == owner]
    total = len(items)
    return jsonify({"total": total, "items": items[offset:offset+limit]})
