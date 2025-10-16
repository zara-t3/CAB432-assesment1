import os
import sys
import json
import time
import signal
import tempfile
import logging
from typing import Dict, Optional
import boto3
from botocore.exceptions import ClientError

# Import face blur processing from standalone module
from processor import face_blur_and_variants

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for graceful shutdown
running = True
current_message = None


class ProcessingService:
    """Service for processing image blur jobs from SQS"""

    def __init__(self):
        """Initialize the processing service"""
        self.qut_username = "n11544309@qut.edu.au"
        self.student_number = "n11544309"

        # Load configuration from environment variables
        self.queue_url = os.environ.get('QUEUE_URL')
        self.s3_bucket = os.environ.get('S3_BUCKET', f'{self.student_number}-imagelab-bucket')
        self.images_table = os.environ.get('DYNAMODB_IMAGES_TABLE', f'{self.student_number}-imagelab-images')
        self.jobs_table = os.environ.get('DYNAMODB_JOBS_TABLE', f'{self.student_number}-imagelab-jobs')

        if not self.queue_url:
            raise ValueError("QUEUE_URL environment variable is required")

        # Initialize AWS clients
        self.sqs = boto3.client('sqs', region_name='ap-southeast-2')
        self.s3 = boto3.client('s3', region_name='ap-southeast-2')
        self.dynamodb = boto3.client('dynamodb', region_name='ap-southeast-2')

        logger.info(f"Initialized ProcessingService")
        logger.info(f"Queue URL: {self.queue_url}")
        logger.info(f"S3 Bucket: {self.s3_bucket}")
        logger.info(f"Images Table: {self.images_table}")
        logger.info(f"Jobs Table: {self.jobs_table}")

    def update_job_status(self, job_id: str, status: str):
        """Update job status in DynamoDB"""
        try:
            self.dynamodb.update_item(
                TableName=self.jobs_table,
                Key={
                    "qut-username": {"S": self.qut_username},
                    "job_id": {"S": job_id}
                },
                UpdateExpression="SET #status = :status",
                ExpressionAttributeNames={
                    "#status": "status"
                },
                ExpressionAttributeValues={
                    ":status": {"S": status}
                }
            )
            logger.info(f"Updated job {job_id} status to {status}")
        except ClientError as e:
            logger.error(f"Failed to update job status: {e}")
            raise

    def update_job_completion(self, job_id: str, duration_ms: int, outputs: list, status: str = 'done'):
        """Update job completion details in DynamoDB"""
        try:
            self.dynamodb.update_item(
                TableName=self.jobs_table,
                Key={
                    "qut-username": {"S": self.qut_username},
                    "job_id": {"S": job_id}
                },
                UpdateExpression="SET #status = :status, duration_ms = :duration",
                ExpressionAttributeNames={
                    "#status": "status"
                },
                ExpressionAttributeValues={
                    ":status": {"S": status},
                    ":duration": {"N": str(duration_ms)}
                }
            )
            logger.info(f"Updated job {job_id} completion: {status}, {duration_ms}ms")
        except ClientError as e:
            logger.error(f"Failed to update job completion: {e}")
            raise

    def update_processed_s3_key(self, image_id: str, processed_s3_key: str):
        """Update processed S3 key in images table"""
        try:
            self.dynamodb.update_item(
                TableName=self.images_table,
                Key={
                    "qut-username": {"S": self.qut_username},
                    "image_id": {"S": image_id}
                },
                UpdateExpression="SET processed_s3_key = :key",
                ExpressionAttributeValues={
                    ":key": {"S": processed_s3_key}
                }
            )
            logger.info(f"Updated image {image_id} processed_s3_key")
        except ClientError as e:
            logger.error(f"Failed to update processed S3 key: {e}")
            raise

    def update_processing_metadata(self, image_id: str, faces_detected: int,
                                  original_width: int, original_height: int, processing_time: str):
        """Update processing metadata in images table"""
        try:
            self.dynamodb.update_item(
                TableName=self.images_table,
                Key={
                    "qut-username": {"S": self.qut_username},
                    "image_id": {"S": image_id}
                },
                UpdateExpression="SET faces_detected = :faces, original_width = :width, original_height = :height, processing_time = :time",
                ExpressionAttributeValues={
                    ":faces": {"N": str(faces_detected)},
                    ":width": {"N": str(original_width)},
                    ":height": {"N": str(original_height)},
                    ":time": {"S": processing_time}
                }
            )
            logger.info(f"Updated image {image_id} processing metadata")
        except ClientError as e:
            logger.error(f"Failed to update processing metadata: {e}")
            raise

    def download_image_from_s3(self, s3_key: str) -> bytes:
        """Download image from S3"""
        try:
            response = self.s3.get_object(Bucket=self.s3_bucket, Key=s3_key)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Failed to download image from S3: {e}")
            raise

    def upload_processed_image(self, local_file_path: str, user: str, image_id: str, filename: str) -> str:
        """Upload processed image to S3"""
        try:
            s3_key = f"images/{user}/{image_id}/processed/{filename}"

            # Determine content type
            ext = filename.lower().split('.')[-1]
            content_types = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'webp': 'image/webp'
            }
            content_type = content_types.get(ext, 'application/octet-stream')

            self.s3.upload_file(
                local_file_path,
                self.s3_bucket,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )

            logger.info(f"Uploaded processed image to {s3_key}")
            return s3_key
        except ClientError as e:
            logger.error(f"Failed to upload processed image: {e}")
            raise

    def process_job(self, message_body: Dict):
        """Process a single job"""
        job_id = message_body.get('job_id')
        image_id = message_body.get('image_id')
        owner = message_body.get('owner')
        s3_key = message_body.get('s3_key')
        extra_passes = message_body.get('extra_passes', 0)
        blur_strength = message_body.get('blur_strength', 12)

        logger.info(f"Processing job {job_id} for image {image_id}")

        start_time = time.time()

        try:
            # Update job status to processing
            self.update_job_status(job_id, "processing")

            # Download image from S3
            logger.info(f"Downloading image from S3: {s3_key}")
            image_data = self.download_image_from_s3(s3_key)

            # Create temporary files for processing
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_input:
                temp_input.write(image_data)
                temp_input_path = temp_input.name

            try:
                with tempfile.TemporaryDirectory() as temp_output_dir:
                    # Process image
                    logger.info(f"Processing image with blur_strength={blur_strength}, extra_passes={extra_passes}")
                    outputs, processing_metadata = face_blur_and_variants(
                        temp_input_path,
                        temp_output_dir,
                        blur_strength=blur_strength,
                        extra_passes=extra_passes
                    )

                    # Upload processed images to S3
                    processed_s3_keys = []
                    for output in outputs:
                        s3_key_uploaded = self.upload_processed_image(
                            output['path'],
                            owner,
                            image_id,
                            output['name']
                        )
                        processed_s3_keys.append({
                            'name': output['name'],
                            's3_key': s3_key_uploaded
                        })

                    # Find primary processed image (fhd_1080.webp)
                    primary_processed = next(
                        (item for item in processed_s3_keys if item['name'] == "fhd_1080.webp"),
                        processed_s3_keys[0] if processed_s3_keys else None
                    )

                    # Update images table with processed S3 key
                    if primary_processed:
                        self.update_processed_s3_key(image_id, primary_processed['s3_key'])

                    # Update processing metadata in images table
                    self.update_processing_metadata(
                        image_id,
                        processing_metadata['faces_detected'],
                        processing_metadata['original_size'][0],  # width
                        processing_metadata['original_size'][1],  # height
                        str(processing_metadata['processing_time'])
                    )

            finally:
                # Clean up temporary input file
                if os.path.exists(temp_input_path):
                    os.unlink(temp_input_path)

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Update job status to done
            self.update_job_completion(
                job_id=job_id,
                duration_ms=duration_ms,
                outputs=processed_s3_keys,
                status="done"
            )

            logger.info(f"Successfully processed job {job_id} in {duration_ms}ms")

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}", exc_info=True)

            # Update job status to failed
            try:
                duration_ms = int((time.time() - start_time) * 1000)
                self.update_job_completion(job_id, duration_ms, [], "failed")
            except Exception as update_error:
                logger.error(f"Failed to update job status to failed: {update_error}")

            raise

    def poll_and_process(self):
        """Main polling loop"""
        global running, current_message

        logger.info("Starting SQS polling loop...")

        while running:
            try:
                # Poll SQS queue with long polling (20 seconds)
                response = self.sqs.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=20,  # Long polling
                    VisibilityTimeout=300  # 5 minutes to process
                )

                messages = response.get('Messages', [])

                if not messages:
                    if running:
                        logger.debug("No messages received, continuing to poll...")
                    continue

                for message in messages:
                    if not running:
                        logger.info("Shutdown requested, stopping processing")
                        break

                    current_message = message
                    receipt_handle = message['ReceiptHandle']

                    try:
                        # Parse message body
                        message_body = json.loads(message['Body'])
                        logger.info(f"Received message: {message_body.get('job_id')}")

                        # Process the job
                        self.process_job(message_body)

                        # Delete message from queue on success
                        self.sqs.delete_message(
                            QueueUrl=self.queue_url,
                            ReceiptHandle=receipt_handle
                        )
                        logger.info(f"Deleted message from queue")

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse message body: {e}")
                        # Delete malformed message
                        self.sqs.delete_message(
                            QueueUrl=self.queue_url,
                            ReceiptHandle=receipt_handle
                        )
                    except Exception as e:
                        logger.error(f"Error processing message: {e}", exc_info=True)
                        # Message will become visible again after visibility timeout
                    finally:
                        current_message = None

            except ClientError as e:
                if running:
                    logger.error(f"AWS client error: {e}")
                    time.sleep(5)  # Wait before retrying
            except Exception as e:
                if running:
                    logger.error(f"Unexpected error in polling loop: {e}", exc_info=True)
                    time.sleep(5)  # Wait before retrying

        logger.info("Polling loop stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global running
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    running = False


def main():
    """Main entry point"""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Create and start the processing service
        service = ProcessingService()
        service.poll_and_process()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Service shutdown complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
