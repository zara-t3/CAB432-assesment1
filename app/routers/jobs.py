import os, uuid, json
from datetime import datetime
from flask import Blueprint, request, jsonify, g, current_app
import boto3
from ..auth import auth_required
from ..services.dynamodb_service import get_db_service
from ..services.s3_service import get_s3_service

jobs_bp = Blueprint("jobs", __name__)

def get_sqs_queue_url():
    """Get SQS queue URL from Parameter Store"""
    ssm = boto3.client('ssm')
    response = ssm.get_parameter(Name='/n11544309/imagelab/sqs-queue-url')
    return response['Parameter']['Value']

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

        # create job record with "queued" status
        job_record = db.create_job_record(
            job_id=job_id,
            owner=rec["owner"],
            image_id=img_id,
            extra_passes=extra_passes,
            blur_strength=blur_strength
        )

        # get SQS queue URL from Parameter Store
        queue_url = get_sqs_queue_url()

        # send message to SQS
        sqs = boto3.client('sqs')
        message_body = {
            "job_id": job_id,
            "image_id": img_id,
            "owner": rec["owner"],
            "s3_key": rec["s3_key"],
            "extra_passes": extra_passes,
            "blur_strength": blur_strength
        }

        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )

        # return immediately with queued status
        return jsonify({
            "job_id": job_id,
            "status": "queued"
        })
        
    except Exception as e:
        try:
            if 'job_id' in locals():
                db = get_db_service()
                db.update_job_completion(job_id, 0, [], "failed")
        except:
            pass

        return jsonify({"error": f"Failed to queue job: {str(e)}"}), 500

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