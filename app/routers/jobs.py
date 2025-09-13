import os, uuid, time, tempfile
from datetime import datetime
from flask import Blueprint, request, jsonify, g, current_app
from ..auth import auth_required
from ..services.dynamodb_service import get_db_service
from ..services.s3_service import get_s3_service
from ..services.processing import face_blur_and_variants

jobs_bp = Blueprint("jobs", __name__)

@jobs_bp.post("")
@auth_required
def create_job():
    """Create and execute face blur job with S3 storage"""
    data = request.get_json(force=True, silent=True) or {}
    img_id = data.get("image_id")
    extra_passes = int(data.get("extra_passes", 0))
    blur_strength = int(data.get("blur_strength", 12))

    if not img_id:
        return jsonify({"error": "missing image_id"}), 400

    try:
        db = get_db_service()
        s3 = get_s3_service()
        
        # Get image record from DynamoDB
        rec = db.get_image(img_id)
        if not rec:
            return jsonify({"error": "image not found"}), 404
            
        if g.user["role"] != "admin" and rec["owner"] != g.user["username"]:
            return jsonify({"error": "image not found"}), 404

        job_id = str(uuid.uuid4())
        
        # Create job record in DynamoDB
        job_record = db.create_job_record(
            job_id=job_id,
            owner=rec["owner"],
            image_id=img_id,
            extra_passes=extra_passes,
            blur_strength=blur_strength
        )
        
        print(f"Starting face blur job with S3: {job_id}")
        start = time.time()

        # Download image from S3 to temporary file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_input:
            image_data = s3.download_image(rec["s3_key"])
            temp_input.write(image_data)
            temp_input_path = temp_input.name

        try:
            # Create temporary output directory
            with tempfile.TemporaryDirectory() as temp_output_dir:
                # Process the image using existing function
                outputs = face_blur_and_variants(
                    temp_input_path, 
                    temp_output_dir, 
                    blur_strength=blur_strength,
                    extra_passes=extra_passes
                )

                # Upload processed files to S3
                processed_s3_keys = []
                for output in outputs:
                    s3_key = s3.upload_processed_image(
                        output['path'], 
                        rec['owner'], 
                        img_id, 
                        output['name']
                    )
                    processed_s3_keys.append({
                        'name': output['name'],
                        's3_key': s3_key
                    })
                
                # Update image record with primary processed S3 key
                primary_processed = next(
                    (item for item in processed_s3_keys if item['name'] == "fhd_1080.webp"), 
                    processed_s3_keys[0] if processed_s3_keys else None
                )
                
                if primary_processed:
                    db.update_processed_s3_key(img_id, primary_processed['s3_key'])

        finally:
            # Clean up temporary input file
            os.unlink(temp_input_path)

        duration_ms = int((time.time() - start) * 1000)

        # Update job completion
        db.update_job_completion(
            job_id=job_id,
            duration_ms=duration_ms,
            outputs=processed_s3_keys,
            status="done"
        )

        print(f"Face blur job completed with S3: {job_id} in {duration_ms}ms")
        
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
    """List jobs from DynamoDB"""
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    owner = request.args.get("owner")
    
    try:
        db = get_db_service()
        
        if g.user["role"] == "admin":
            if owner:
                items = db.list_jobs_for_user(owner, limit=limit + offset)
            else:
                items = db.list_all_jobs(limit=limit + offset)
        else:
            items = db.list_jobs_for_user(g.user["username"], limit=limit + offset)
        
        total = len(items)
        paginated_items = items[offset:offset+limit]
        
        print(f"Listed {len(paginated_items)} jobs from DynamoDB")
        
        return jsonify({
            "total": total,
            "items": paginated_items
        })
        
    except Exception as e:
        print(f"Failed to list jobs: {e}")
        return jsonify({"error": "Failed to list jobs"}), 500