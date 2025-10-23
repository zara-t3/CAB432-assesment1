import os, uuid, mimetypes, time
from datetime import datetime
from urllib.parse import quote, urlencode
from flask import Blueprint, current_app, request, jsonify, send_file, g, Response, redirect
from PIL import Image
from ..auth import auth_required
from ..services.dynamodb_service import get_db_service
from ..services.s3_service import get_s3_service
import io

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
    
    try:
      
        s3 = get_s3_service()
        s3_key = s3.upload_image(f, user, img_id)
    
        db = get_db_service()
        image_record = db.create_image_record(
            image_id=img_id,
            name=name,
            owner=user,
            s3_key=s3_key
        )
        
        pass
        return jsonify({"id": img_id, "name": name})
        
    except Exception as e:
        pass
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

@images_bp.get("")
@auth_required
def list_images():
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    
    try:
        db = get_db_service()
        
        if g.user["role"] == "admin":
            items = db.list_all_images(limit=limit + offset)
        else:
            items = db.list_images_for_user(g.user["username"], limit=limit + offset)
        
        total = len(items)
        paginated_items = items[offset:offset+limit]
        
    
        clean_items = []
        for i in paginated_items:
            clean_item = {
                "id": i["id"],
                "name": i["name"],
                "owner": i["owner"],
                "created_at": i["created_at"],
                "processed_path": i["processed_s3_key"],
            }
            clean_items.append(clean_item)
        
        pass
        return jsonify({"total": total, "items": clean_items})
        
    except Exception as e:
        pass
        return jsonify({"error": "Failed to list images"}), 500

@images_bp.get("/<img_id>")
@auth_required
def get_meta(img_id):
    try:
        db = get_db_service()
        rec = db.get_image(img_id)
        
        if not rec:
            return jsonify({"error": "not found"}), 404
            
        if g.user["role"] != "admin" and rec["owner"] != g.user["username"]:
            return jsonify({"error": "not found"}), 404
        
        return jsonify({
            "id": rec["id"],
            "name": rec["name"],
            "owner": rec["owner"],
            "created_at": rec["created_at"],
            "processed_path": rec["processed_s3_key"],
        })
        
    except Exception as e:
        pass
        return jsonify({"error": "Failed to get image"}), 500

@images_bp.get("/<img_id>/file")
@auth_required
def get_file(img_id):
    version = request.args.get("version", "original")
    download = request.args.get("download") in ("1", "true", "yes")

    # CloudFront distribution domain
    CLOUDFRONT_DOMAIN = current_app.config.get('CLOUDFRONT_DOMAIN', 'd2vmmt2bt8b124.cloudfront.net')

    try:
        db = get_db_service()
        rec = db.get_image(img_id)

        if not rec:
            return jsonify({"error": "not found"}), 404

        if g.user["role"] != "admin" and rec["owner"] != g.user["username"]:
            return jsonify({"error": "not found"}), 404

        s3 = get_s3_service()

        # Determine which S3 key to use based on version
        if version == "thumb":
            s3_key = rec["thumb_s3_key"]
            if not s3_key:
                # Create thumbnail on-demand
                s3_key = s3.create_thumbnail(rec["s3_key"], rec["owner"], img_id)
                db.update_thumb_s3_key(img_id, s3_key)
        elif version == "processed":
            s3_key = rec["processed_s3_key"]
        else:
            s3_key = rec["s3_key"]

        # Check if s3_key exists
        if not s3_key:
            return jsonify({"error": "file not ready"}), 404

        # Verify file exists in S3 before redirecting
        if not s3.verify_object_exists(s3_key):
            return jsonify({"error": "file not available"}), 404

        # Build CloudFront URL
        # URL encode the s3_key to handle special characters
        encoded_s3_key = quote(s3_key, safe='/')
        cloudfront_url = f"https://{CLOUDFRONT_DOMAIN}/{encoded_s3_key}"

        # Handle download parameter using CloudFront's response-content-disposition
        if download:
            filename = s3_key.split('/')[-1]
            query_params = {
                'response-content-disposition': f'attachment; filename="{filename}"'
            }
            cloudfront_url = f"{cloudfront_url}?{urlencode(query_params)}"

        # Redirect to CloudFront URL
        return redirect(cloudfront_url, code=302)

    except Exception as e:
        pass
        return jsonify({"error": "Failed to get file"}), 500

@images_bp.get("/<img_id>/metadata")
@auth_required
def get_metadata(img_id):
    try:
        db = get_db_service()
        rec = db.get_image(img_id)
        
        if not rec:
            return jsonify({"error": "not found"}), 404
            
        if g.user["role"] != "admin" and rec["owner"] != g.user["username"]:
            return jsonify({"error": "not found"}), 404
        
        
        # Get job info for blur_strength and extra_passes
        job_data = None
        try:
            if g.user["role"] == "admin":
                jobs = db.list_all_jobs(limit=100)
            else:
                jobs = db.list_jobs_for_user(g.user["username"], limit=100)

            # Find the most recent job for this image
            image_jobs = [job for job in jobs if job.get('image_id') == img_id]
            if image_jobs:
                job_data = image_jobs[0]  # Most recent due to sorting
        except:
            pass

        metadata = {
            "image_id": rec["id"],
            "name": rec["name"],
            "owner": rec["owner"],
            "created_at": rec["created_at"],
            "status": rec["status"],
            "faces_detected": rec.get("faces_detected", 0),
            "blur_strength": job_data.get("blur_strength", 12) if job_data else 12,
            "extra_passes": job_data.get("extra_passes", 0) if job_data else 0,
            "original_size": [rec.get("original_width", 1920), rec.get("original_height", 1080)],
            "processing_time": rec.get("processing_time", rec["created_at"])
        }
        
        return jsonify(metadata)
        
    except Exception as e:
        pass
        return jsonify({"error": "Failed to get metadata"}), 500
    

@images_bp.post("/presigned-upload")
@auth_required
def get_presigned_upload():
    try:
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        content_type = data.get("content_type", "image/jpeg")
        
        if not name:
            return jsonify({"error": "missing name"}), 400
        
      
        img_id = str(uuid.uuid4())
        user = g.user["username"]
        
       
        s3_key = f"images/{user}/{img_id}/original.jpg"
        
       
        s3 = get_s3_service()
        presigned_data = s3.generate_presigned_upload_url(
            s3_key=s3_key,
            content_type=content_type,
            expiration=3600 
        )
        
        pass
        
        return jsonify({
            "image_id": img_id,
            "name": name,
            "s3_key": s3_key,
            "presigned_upload": presigned_data,
            "expires_in": 3600
        })
        
    except Exception as e:
        pass
        return jsonify({"error": f"Failed to generate upload URL: {str(e)}"}), 500

@images_bp.post("/<img_id>/confirm-upload")
@auth_required
def confirm_upload(img_id):
    try:
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        s3_key = data.get("s3_key", "").strip()
        
        if not name or not s3_key:
            return jsonify({"error": "missing name or s3_key"}), 400
        
        user = g.user["username"]
        
      
        s3 = get_s3_service()
        try:
            
            s3.s3_client.head_object(Bucket=s3.bucket_name, Key=s3_key)
        except Exception as e:
            return jsonify({"error": "Upload not found in S3"}), 400
        
        db = get_db_service()
        image_record = db.create_image_record(
            image_id=img_id,
            name=name,
            owner=user,
            s3_key=s3_key
        )
        
        pass
        
        return jsonify({
            "id": img_id,
            "name": name,
            "status": "uploaded",
            "message": "Upload confirmed successfully"
        })
        
    except Exception as e:
        pass
        return jsonify({"error": f"Failed to confirm upload: {str(e)}"}), 500

@images_bp.get("/upload-methods")
@auth_required
def get_upload_methods():
    return jsonify({
        "methods": [
            {
                "name": "server_upload",
                "description": "Upload through server (traditional)",
                "endpoint": "POST /api/v1/images",
                "method": "multipart/form-data"
            },
            {
                "name": "presigned_upload", 
                "description": "Direct upload to S3 using pre-signed URL",
                "steps": [
                    "1. POST /api/v1/images/presigned-upload to get upload URL",
                    "2. POST directly to S3 using the pre-signed URL",
                    "3. POST /api/v1/images/{id}/confirm-upload to finalize"
                ]
            }
        ]
    })