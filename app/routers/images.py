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
    """Upload image to S3 and save metadata to DynamoDB"""
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"error": "missing name"}), 400
    
    img_id = str(uuid.uuid4())
    user = g.user["username"]
    
    try:
        # Upload to S3
        s3 = get_s3_service()
        s3_key = s3.upload_image(f, user, img_id)
        
        # Save metadata to DynamoDB with S3 key
        db = get_db_service()
        image_record = db.create_image_record(
            image_id=img_id,
            name=name,
            owner=user,
            s3_key=s3_key
        )
        
        print(f"Image uploaded to S3 and saved to DynamoDB: {img_id}")
        return jsonify({"id": img_id, "name": name})
        
    except Exception as e:
        print(f"Upload failed: {e}")
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

@images_bp.get("")
@auth_required
def list_images():
    """List images from DynamoDB"""
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
        
        # Convert S3 keys to processed_path for frontend compatibility
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
        
        print(f"Listed {len(clean_items)} images from DynamoDB")
        return jsonify({"total": total, "items": clean_items})
        
    except Exception as e:
        print(f"Failed to list images: {e}")
        return jsonify({"error": "Failed to list images"}), 500

@images_bp.get("/<img_id>")
@auth_required
def get_meta(img_id):
    """Get image metadata"""
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
        print(f"Failed to get image metadata: {e}")
        return jsonify({"error": "Failed to get image"}), 500

@images_bp.get("/<img_id>/file")
@auth_required
def get_file(img_id):
    """Get image file from S3"""
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
        
        # Determine which S3 key to use
        if version == "thumb":
            s3_key = rec["thumb_s3_key"]
            if not s3_key:
                # Create thumbnail from original if it doesn't exist
                s3_key = s3.create_thumbnail(rec["s3_key"], rec["owner"], img_id)
                db.update_thumb_s3_key(img_id, s3_key)
        elif version == "processed":
            s3_key = rec["processed_s3_key"]
        else:  # original
            s3_key = rec["s3_key"]
        
        if not s3_key:
            return jsonify({"error": "file not ready"}), 404

        # Download from S3 and serve to client
        try:
            image_data = s3.download_image(s3_key)
            
            # Determine content type
            filename = s3_key.split('/')[-1]
            mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            
            # Create response
            response = Response(image_data, mimetype=mime)
            
            if download:
                response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            print(f"S3 download error: {e}")
            return jsonify({"error": "file not available"}), 404
        
    except Exception as e:
        print(f"Failed to get image file: {e}")
        return jsonify({"error": "Failed to get file"}), 500

@images_bp.get("/<img_id>/metadata")
@auth_required
def get_metadata(img_id):
    """Get processing metadata"""
    try:
        db = get_db_service()
        rec = db.get_image(img_id)
        
        if not rec:
            return jsonify({"error": "not found"}), 404
            
        if g.user["role"] != "admin" and rec["owner"] != g.user["username"]:
            return jsonify({"error": "not found"}), 404
        
        # Return basic metadata from DynamoDB
        metadata = {
            "image_id": rec["id"],
            "name": rec["name"],
            "owner": rec["owner"],
            "created_at": rec["created_at"],
            "status": rec["status"],
            "s3_key": rec["s3_key"],
            "has_processed": bool(rec["processed_s3_key"]),
            "has_thumbnail": bool(rec["thumb_s3_key"])
        }
        
        return jsonify(metadata)
        
    except Exception as e:
        print(f"Failed to get metadata: {e}")
        return jsonify({"error": "Failed to get metadata"}), 500
    

@images_bp.post("/presigned-upload")
@auth_required
def get_presigned_upload():
    """Generate pre-signed URL for direct client upload to S3"""
    try:
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        content_type = data.get("content_type", "image/jpeg")
        
        if not name:
            return jsonify({"error": "missing name"}), 400
        
      
        img_id = str(uuid.uuid4())
        user = g.user["username"]
        
        # Create S3 key for the upload
        s3_key = f"images/{user}/{img_id}/original.jpg"
        
        # Generate pre-signed upload URL
        s3 = get_s3_service()
        presigned_data = s3.generate_presigned_upload_url(
            s3_key=s3_key,
            content_type=content_type,
            expiration=3600 
        )
        
        print(f"Generated pre-signed upload URL for: {img_id}")
        
        return jsonify({
            "image_id": img_id,
            "name": name,
            "s3_key": s3_key,
            "presigned_upload": presigned_data,
            "expires_in": 3600
        })
        
    except Exception as e:
        print(f"Failed to generate pre-signed upload URL: {e}")
        return jsonify({"error": f"Failed to generate upload URL: {str(e)}"}), 500

@images_bp.post("/<img_id>/confirm-upload")
@auth_required
def confirm_upload(img_id):
    """Confirm successful upload and create DynamoDB record"""
    try:
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        s3_key = data.get("s3_key", "").strip()
        
        if not name or not s3_key:
            return jsonify({"error": "missing name or s3_key"}), 400
        
        user = g.user["username"]
        
      
        s3 = get_s3_service()
        try:
            # get object metadata to verify it exists
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
        
        print(f"Confirmed upload and created DynamoDB record: {img_id}")
        
        return jsonify({
            "id": img_id,
            "name": name,
            "status": "uploaded",
            "message": "Upload confirmed successfully"
        })
        
    except Exception as e:
        print(f"Failed to confirm upload: {e}")
        return jsonify({"error": f"Failed to confirm upload: {str(e)}"}), 500

@images_bp.get("/upload-methods")
@auth_required
def get_upload_methods():
    """List available upload methods for client"""
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