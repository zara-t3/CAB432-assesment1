import os, uuid, time
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from ..auth import auth_required
from ..models.store import IMAGES, JOBS
from ..services.processing import face_blur_and_variants

jobs_bp = Blueprint("jobs", __name__)

@jobs_bp.post("")
@auth_required
def create_job():
    data = request.get_json(force=True, silent=True) or {}
    img_id = data.get("image_id")
    extra_passes = int(data.get("extra_passes", 0))
    blur_strength = int(data.get("blur_strength", 12))  # optional knob

    rec = IMAGES.get(img_id)
    if not rec or (g.user["role"] != "admin" and rec["owner"] != g.user["username"]):
        return jsonify({"error": "image not found"}), 404

    job_id = str(uuid.uuid4())
    start = time.time()

    out_dir = os.path.dirname(rec["orig_path"])
    full, outputs = face_blur_and_variants(
        rec["orig_path"], out_dir,
        blur_strength=blur_strength, extra_passes=extra_passes
    )

    # Save a full-res blurred representative file
    full_path = os.path.join(out_dir, "blurred_full.jpg")
    full.save(full_path, format="JPEG", quality=90, progressive=True, optimize=True)

    rec["processed_path"] = full_path
    rec["variants"] = outputs

    duration_ms = int((time.time() - start) * 1000)

    JOBS[job_id] = {
        "id": job_id,
        "owner": rec["owner"],
        "image_id": img_id,
        "preset": "face_blur",
        "blur_strength": blur_strength,
        "extra_passes": extra_passes,
        "status": "done",
        "duration_ms": duration_ms,
        "outputs": outputs,
        "created_at": datetime.utcnow().isoformat()
    }

    return jsonify({
        "job_id": job_id,
        "status": "done",
        "duration_ms": duration_ms,
        "outputs": outputs
    })

@jobs_bp.get("")
@auth_required
def list_jobs():
    limit  = max(1, int(request.args.get("limit", 10)))
    offset = max(0, int(request.args.get("offset", 0)))
    owner  = (request.args.get("owner") or "").strip()
    image_id = (request.args.get("image_id") or "").strip()
    status = (request.args.get("status") or "").strip()
    sort   = (request.args.get("sort") or "created_at").strip()
    order  = (request.args.get("order") or "desc").lower()

    items = list(JOBS.values())
    if g.user["role"] != "admin":
        items = [j for j in items if j["owner"] == g.user["username"]]
    else:
        if owner in ("me", "mine"):
            owner = g.user["username"]
        if owner:
            items = [j for j in items if j["owner"] == owner]

    if image_id:
        items = [j for j in items if j.get("image_id") == image_id]
    if status:
        items = [j for j in items if j.get("status") == status]

    def keyfn(j):
        if sort == "created_at": return j.get("created_at", "")
        if sort == "duration_ms": return j.get("duration_ms", 0)
        return j.get("created_at", "")
    reverse = (order == "desc")
    items.sort(key=keyfn, reverse=reverse)

    total = len(items)
    items = items[offset: offset + limit]
    return jsonify({"total": total, "limit": limit, "offset": offset, "items": items})
