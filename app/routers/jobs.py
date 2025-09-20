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
    data = request.get_json(force=True, silent=True) or {}
    img_id = data.get("image_id")
    extra_passes = int(data.get("extra_passes", 0))
    blur_strength = int(data.get("blur_strength", 12))

    if not img_id:
        return jsonify({"error": "missing image_id"}), 400

    try:
        db = get_db_service()
        s3 = get_s3_service()
        
        # get image record
        rec = db.get_image(img_id)
        if not rec:
            return jsonify({"error": "image not found"}), 404
            
        if g.user["role"] != "admin" and rec["owner"] != g.user["username"]:
            return jsonify({"error": "image not found"}), 404

        job_id = str(uuid.uuid4())
        
        # create job record
        job_record = db.create_job_record(
            job_id=job_id,
            owner=rec["owner"],
            image_id=img_id,
            extra_passes=extra_passes,
            blur_strength=blur_strength
        )
        
        pass
        start = time.time()

       
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_input:
            image_data = s3.download_image(rec["s3_key"])
            temp_input.write(image_data)
            temp_input_path = temp_input.name

        try:
            #
            with tempfile.TemporaryDirectory() as temp_output_dir:
               
                outputs = face_blur_and_variants(
                    temp_input_path, 
                    temp_output_dir, 
                    blur_strength=blur_strength,
                    extra_passes=extra_passes
                )
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
                
                metadata_file = os.path.join(temp_output_dir, "processing_metadata.json")
                if os.path.exists(metadata_file):
                    metadata_s3_key = s3.upload_processed_image(metadata_file, rec['owner'], img_id, "processing_metadata.json")
           
                primary_processed = next(
                    (item for item in processed_s3_keys if item['name'] == "fhd_1080.webp"), 
                    processed_s3_keys[0] if processed_s3_keys else None
                )
                
                if primary_processed:
                    db.update_processed_s3_key(img_id, primary_processed['s3_key'])

        finally:
            os.unlink(temp_input_path)

        duration_ms = int((time.time() - start) * 1000)


        db.update_job_completion(
            job_id=job_id,
            duration_ms=duration_ms,
            outputs=processed_s3_keys,
            status="done"
        )

        pass
        
        return jsonify({
            "job_id": job_id,
            "status": "done",
            "duration_ms": duration_ms,
            "outputs": []  
        })
        
    except Exception as e:
        pass
        
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
        
        pass
        
        return jsonify({
            "total": total,
            "items": paginated_items
        })
        
    except Exception as e:
        pass
        return jsonify({"error": "Failed to list jobs"}), 500