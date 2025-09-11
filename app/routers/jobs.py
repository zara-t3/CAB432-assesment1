# app/routers/jobs.py - Updated with DynamoDB
import os, uuid, time
from datetime import datetime
from flask import Blueprint, request, jsonify, g, current_app
from ..auth import auth_required
from ..services.dynamodb_service import get_db_service
from ..services.processing import face_blur_and_variants

jobs_bp = Blueprint("jobs", __name__)

@jobs_bp.post("")
@auth_required
def create_job():
    """Create and execute face blur job - now uses DynamoDB"""
    data = request.get_json(force=True, silent=True) or {}
    img_id = data.get("image_id")
    extra_passes = int(data.get("extra_passes", 0))
    blur_strength = int(data.get("blur_strength", 12))

    if not img_id:
        return jsonify({"error": "missing image_id"}), 400

    try:
        db = get_db_service()
        
        # CHANGE: Get image from DynamoDB instead of IMAGES.get()
        rec = db.get_image(img_id)
        
        if not rec:
            return jsonify({"error": "image not found"}), 404
            
        # Check ownership
        if g.user["role"] != "admin" and rec["owner"] != g.user["username"]:
            return jsonify({"error": "image not found"}), 404

        job_id = str(uuid.uuid4())
        
        #CHANGE: Create job record in DynamoDB first
        job_record = db.create_job_record(
            job_id=job_id,
            owner=rec["owner"],
            image_id=img_id,
            extra_passes=extra_passes,
            blur_strength=blur_strength
        )
        
        print(f"Starting face blur job: {job_id}")
        start = time.time()

        # Process the image (same logic as before)
        out_dir = os.path.dirname(rec["orig_path"])
        outputs = face_blur_and_variants(
            rec["orig_path"], 
            out_dir, 
            blur_strength=blur_strength,
            extra_passes=extra_passes
        )

        # Find the best processed image (same logic)
        rep = next((v for v in outputs if v["name"] == "fhd_1080.webp"), None) \
              or next((v for v in outputs if v["name"] == "fhd_1080.jpg"), None) \
              or (outputs[0] if outputs else None)
        
        duration_ms = int((time.time() - start) * 1000)

        # CHANGE: Update both job completion AND image processed path in DynamoDB
        if rep:
            # Update image record with processed path
            db.update_image_processed_path(img_id, rep["path"])
            
        # Update job completion
        db.update_job_completion(
            job_id=job_id,
            duration_ms=duration_ms,
            outputs=outputs,
            status="done"
        )

        print(f"✅ Face blur job completed: {job_id} in {duration_ms}ms")
        
        return jsonify({
            "job_id": job_id,
            "status": "done",
            "duration_ms": duration_ms,
            "outputs": []  # Keep same API response format
        })
        
    except Exception as e:
        print(f"Job failed: {e}")
        
        # Try to update job status to failed
        try:
            if 'job_id' in locals():
                db = get_db_service()
                db.update_job_completion(job_id, 0, [], "failed")
        except:
            pass
            
        return jsonify({"error": f"Job processing failed: {str(e)}"}), 500

@jobs_bp.get("")
@auth_required
def list_jobs():
    """List jobs - now reads from DynamoDB"""
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    owner = request.args.get("owner")  # For admin filtering
    
    try:
        db = get_db_service()
        
        
        if g.user["role"] == "admin":
            if owner:
                items = db.list_jobs_for_user(owner, limit=limit + offset)
            else:
                items = db.list_all_jobs(limit=limit + offset)
        else:
            items = db.list_jobs_for_user(g.user["username"], limit=limit + offset)
        
        # Apply offset (simple pagination)
        total = len(items)
        paginated_items = items[offset:offset+limit]
        
        print(f"✅ Listed {len(paginated_items)} jobs from DynamoDB")
        
        return jsonify({
            "total": total,
            "items": paginated_items
        })
        
    except Exception as e:
        print(f"Failed to list jobs: {e}")
        return jsonify({"error": "Failed to list jobs"}), 500