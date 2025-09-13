# app/routers/images.py 
import os, uuid, mimetypes, time
from datetime import datetime
from flask import Blueprint, current_app, request, jsonify, send_file, g
from PIL import Image
from ..auth import auth_required
from ..services.dynamodb_service import get_db_service

images_bp = Blueprint("images", __name__)

@images_bp.post("")
@auth_required
def upload():
    """Upload image - now saves metadata to DynamoDB"""
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "no file"}), 400
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"error": "missing name"}), 400
    
    img_id = str(uuid.uuid4())
    user = g.user["username"]
    
    # Still save to filesystem for now (will move to S3 in next step)
    folder = os.path.join(current_app.config["DATA_DIR"], "images", user, img_id)
    os.makedirs(folder, exist_ok=True)
    orig_path = os.path.join(folder, "original.jpg")
    f.save(orig_path)
    
    # Save to DynamoDB instead of IMAGES dict
    try:
        db = get_db_service()
        image_record = db.create_image_record(
            image_id=img_id,
            name=name,
            owner=user,
            orig_path=orig_path
        )
        print(f"Image uploaded and saved to DynamoDB: {img_id}")
        
        return jsonify({"id": img_id, "name": name})
        
    except Exception as e:
        # Clean up file if database save fails
        try:
            os.remove(orig_path)
            os.rmdir(folder)
        except:
            pass
        return jsonify({"error": f"Failed to save image metadata: {str(e)}"}), 500

@images_bp.get("")
@auth_required
def list_images():
    """List images - now reads from DynamoDB"""
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    
    try:
        db = get_db_service()
        
      
        if g.user["role"] == "admin":
            items = db.list_all_images(limit=limit + offset)  # Get more for offset
        else:
            items = db.list_images_for_user(g.user["username"], limit=limit + offset)
        
        # Apply offset (simple pagination for now)
        total = len(items)
        paginated_items = items[offset:offset+limit]
        
        # Clean up items for response (same format as before)
        clean_items = [
            {
                "id": i["id"],
                "name": i["name"],
                "owner": i["owner"],
                "created_at": i["created_at"],
                "processed_path": i.get("processed_path"),
            }
            for i in paginated_items
        ]
        
        print(f"✅ Listed {len(clean_items)} images from DynamoDB")
        return jsonify({"total": total, "items": clean_items})
        
    except Exception as e:
        print(f"Failed to list images: {e}")
        return jsonify({"error": "Failed to list images"}), 500

@images_bp.get("/<img_id>")
@auth_required
def get_meta(img_id):
    """Get image metadata - now reads from DynamoDB"""
    try:
        db = get_db_service()
        
       
        rec = db.get_image(img_id)
        
        if not rec:
            return jsonify({"error": "not found"}), 404
            
        # Check ownership (same logic as before)
        if g.user["role"] != "admin" and rec["owner"] != g.user["username"]:
            return jsonify({"error": "not found"}), 404
        
        return jsonify({
            "id": rec["id"],
            "name": rec["name"],
            "owner": rec["owner"],
            "created_at": rec["created_at"],
            "processed_path": rec.get("processed_path"),
        })
        
    except Exception as e:
        print(f"Failed to get image metadata: {e}")
        return jsonify({"error": "Failed to get image"}), 500

@images_bp.get("/<img_id>/file")
@auth_required
def get_file(img_id):
    """Get image file - reads metadata from DynamoDB, file from filesystem"""
    version = request.args.get("version", "original")
    download = request.args.get("download") in ("1", "true", "yes")

    try:
        db = get_db_service()
        
        # CHANGE: Get from DynamoDB instead of IMAGES.get()
        rec = db.get_image(img_id)
        
        if not rec:
            return jsonify({"error": "not found"}), 404
            
        # Check ownership
        if g.user["role"] != "admin" and rec["owner"] != g.user["username"]:
            return jsonify({"error": "not found"}), 404

        # File handling logic stays the same for now
        base_dir = os.path.dirname(rec["orig_path"])

        if version == "thumb":
            thumb_path = os.path.join(base_dir, "thumb_160.jpg")
            if not os.path.exists(thumb_path):
                img = Image.open(rec["orig_path"]).convert("RGB")
                img.thumbnail((160, 160), Image.Resampling.LANCZOS)
                img.save(thumb_path, quality=80, optimize=True)
            path = thumb_path
        elif version == "processed":
            path = rec.get("processed_path")
        else:
            path = rec["orig_path"]

        if not path or not os.path.exists(path):
            return jsonify({"error": "file not ready"}), 404

        mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
        return send_file(
            path, mimetype=mime,
            as_attachment=download,
            download_name=os.path.basename(path)
        )
        
    except Exception as e:
        print(f"❌ Failed to get image file: {e}")
        return jsonify({"error": "Failed to get file"}), 500

@images_bp.get("/<img_id>/metadata")
@auth_required
def get_metadata(img_id):
    """Get processing metadata - reads image record from DynamoDB"""
    try:
        db = get_db_service()
        
        # Get from DynamoDB instead of IMAGES.get()
        rec = db.get_image(img_id)
        
        if not rec:
            return jsonify({"error": "not found"}), 404
            
        # Check ownership
        if g.user["role"] != "admin" and rec["owner"] != g.user["username"]:
            return jsonify({"error": "not found"}), 404
        
        # File reading logic stays the same for now
        base_dir = os.path.dirname(rec["orig_path"])
        metadata_path = os.path.join(base_dir, "processing_metadata.json")
        
        if not os.path.exists(metadata_path):
            return jsonify({"error": "metadata not available"}), 404
        
        import json
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        return jsonify(metadata)
        
    except Exception as e:
        print(f"Failed to get metadata: {e}")
        return jsonify({"error": "Failed to get metadata"}), 500