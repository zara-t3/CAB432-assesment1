import os, uuid, mimetypes, time
from datetime import datetime
from flask import Blueprint, current_app, request, jsonify, send_file, g, Response
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

    try:
        db = get_db_service()
        rec = db.get_image(img_id)
        
        if not rec:
            return jsonify({"error": "not found"}), 404
            
        if g.user["role"] != "admin" and rec["owner"] != g.user["username"]:
            return jsonify({"error": "not found"}), 404

        s3 = get_s3_service()
        

        if version == "thumb":
            s3_key = rec["thumb_s3_key"]
            if not s3_key:
                # Create thumbnail
                s3_key = s3.create_thumbnail(rec["s3_key"], rec["owner"], img_id)
                db.update_thumb_s3_key(img_id, s3_key)
        elif version == "processed":
            s3_key = rec["processed_s3_key"]
        else:  
            s3_key = rec["s3_key"]
        
        if not s3_key:
            return jsonify({"error": "file not ready"}), 404

        # Download from S3 
        try:
            image_data = s3.download_image(s3_key)
            
            filename = s3_key.split('/')[-1]
            mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"

            response = Response(image_data, mimetype=mime)
            
            if download:
                response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            pass
            return jsonify({"error": "file not available"}), 404
        
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
        
        
        metadata = {
            "image_id": rec["id"],
            "name": rec["name"],
            "owner": rec["owner"],
            "created_at": rec["created_at"],
            "status": rec["status"],
            "faces_detected": 0,
            "blur_strength": 12,
            "extra_passes": 0,
            "original_size": [1920, 1080],
            "processing_time": rec["created_at"]
        }
        
    
        if rec["processed_s3_key"]:
            try:
                s3 = get_s3_service()
                metadata_key = f"images/{rec['owner']}/{img_id}/processed/processing_metadata.json"
                metadata_data = s3.download_image(metadata_key)
                import json
                processing_metadata = json.loads(metadata_data.decode('utf-8'))
                
               
                metadata.update({
                    "faces_detected": processing_metadata.get("faces_detected", 0),
                    "blur_strength": processing_metadata.get("blur_strength", 12),
                    "extra_passes": processing_metadata.get("extra_passes", 0),
                    "original_size": processing_metadata.get("original_size", [1920, 1080]),
                    "processing_time": processing_metadata.get("processing_time", rec["created_at"])
                })
            except Exception as e:
                pass
        
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