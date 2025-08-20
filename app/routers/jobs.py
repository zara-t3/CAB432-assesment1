import os, uuid, time
from datetime import datetime
from flask import Blueprint, request, jsonify, g, current_app
from ..auth import auth_required
from ..models.store import IMAGES, JOBS
from ..services.processing import web_optimize_variants

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.post("")
@auth_required
def create_job():
    data = request.get_json(force=True, silent=True) or {}
    img_id = data.get("image_id")
    extra_passes = int(data.get("extra_passes", 0))  # optional CPU knob

    rec = IMAGES.get(img_id)
    if not rec or (g.user["role"] != "admin" and rec["owner"] != g.user["username"]):
        return jsonify({"error": "image not found"}), 404

    job_id = str(uuid.uuid4())
    start = time.time()

    out_dir = os.path.dirname(rec["orig_path"])
    outputs = web_optimize_variants(rec["orig_path"], out_dir, extra_passes=extra_passes)

    rep = next((v for v in outputs if v["name"] == "fhd_1080.webp"), None) \
          or next((v for v in outputs if v["name"] == "fhd_1080.jpg"), None) \
          or (outputs[0] if outputs else None)
    if rep: rec["processed_path"] = rep["path"]
    rec["variants"] = outputs

    duration_ms = int((time.time() - start) * 1000)

    JOBS[job_id] = {
        "id": job_id, "owner": rec["owner"], "image_id": img_id,
        "preset": "web_optimize", "extra_passes": extra_passes,
        "status": "done", "duration_ms": duration_ms,
        "outputs": outputs, "created_at": datetime.utcnow().isoformat()
    }

    return jsonify({
        "job_id": job_id, "status": "done", "duration_ms": duration_ms,
        "outputs": outputs
    })



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
