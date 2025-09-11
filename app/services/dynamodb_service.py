# app/services/dynamodb_service.py 
import boto3
import os
from datetime import datetime
from typing import Dict, List, Optional
from botocore.exceptions import ClientError
import uuid

class DynamoDBService:
    def __init__(self):
        self.qut_username = "n11544309@qut.edu.au" 
        self.student_number = "n11544309" 
        
        self.dynamodb = boto3.client('dynamodb', region_name='ap-southeast-2')
        
        self.images_table_name = f'{self.student_number}-imagelab-images'
        self.jobs_table_name = f'{self.student_number}-imagelab-jobs'
        

    # ========== IMAGE OPERATIONS ==========
    
    def create_image_record(self, image_id: str, name: str, owner: str, orig_path: str) -> Dict:
        """Create image record following QUT DynamoDB pattern"""
        try:
            response = self.dynamodb.put_item(
                TableName=self.images_table_name,
                Item={
                    "qut-username": {"S": self.qut_username},  # Partition key (required)
                    "image_id": {"S": image_id},  # Sort key
                    "name": {"S": name},
                    "owner": {"S": owner},
                    "orig_path": {"S": orig_path},
                    "processed_path": {"S": ""},  # Empty string instead of None
                    "created_at": {"S": datetime.utcnow().isoformat()},
                    "status": {"S": "uploaded"}
                }
            )
            print(f"Created image record: {image_id}")
            
            # Return in same format as before for compatibility
            return {
                'id': image_id,
                'name': name,
                'owner': owner,
                'orig_path': orig_path,
                'processed_path': None,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'uploaded'
            }
        except ClientError as e:
            print(f"Failed to create image: {e}")
            raise Exception(f"Failed to create image record: {e}")

    def get_image(self, image_id: str) -> Optional[Dict]:
        """Get single image following QUT pattern"""
        try:
            response = self.dynamodb.get_item(
                TableName=self.images_table_name,
                Key={
                    "qut-username": {"S": self.qut_username},
                    "image_id": {"S": image_id}
                }
            )
            
            item = response.get('Item')
            if not item:
                return None
                
            # Convert DynamoDB format back to app format
            result = {
                'id': item['image_id']['S'],
                'name': item['name']['S'],
                'owner': item['owner']['S'],
                'orig_path': item['orig_path']['S'],
                'processed_path': item['processed_path']['S'] if item['processed_path']['S'] else None,
                'created_at': item['created_at']['S'],
                'status': item['status']['S']
            }
            print(f"Retrieved image: {image_id}")
            return result
            
        except ClientError as e:
            print(f"Failed to get image {image_id}: {e}")
            return None

    def list_images_for_user(self, owner: str, limit: int = 20) -> List[Dict]:
        """List images for user using QUT query pattern"""
        try:
            # Query all images for this QUT user, then filter by owner
            response = self.dynamodb.query(
                TableName=self.images_table_name,
                KeyConditionExpression="qut-username = :username",
                ExpressionAttributeValues={
                    ":username": {"S": self.qut_username}
                },
                Limit=limit
            )
            
            items = response.get('Items', [])
            
            # Convert and filter by owner
            results = []
            for item in items:
                if item['owner']['S'] == owner:
                    result = {
                        'id': item['image_id']['S'],
                        'name': item['name']['S'],
                        'owner': item['owner']['S'],
                        'orig_path': item['orig_path']['S'],
                        'processed_path': item['processed_path']['S'] if item['processed_path']['S'] else None,
                        'created_at': item['created_at']['S'],
                        'status': item['status']['S']
                    }
                    results.append(result)
            
            # Sort by created_at descending
            results.sort(key=lambda x: x['created_at'], reverse=True)
            print(f"Found {len(results)} images for user {owner}")
            return results
            
        except ClientError as e:
            print(f"Failed to list images for {owner}: {e}")
            return []

    def list_all_images(self, limit: int = 20) -> List[Dict]:
        """List all images for admin users"""
        try:
            response = self.dynamodb.query(
                TableName=self.images_table_name,
                KeyConditionExpression="qut-username = :username",
                ExpressionAttributeValues={
                    ":username": {"S": self.qut_username}
                },
                Limit=limit
            )
            
            items = response.get('Items', [])
            
            # Convert format
            results = []
            for item in items:
                result = {
                    'id': item['image_id']['S'],
                    'name': item['name']['S'],
                    'owner': item['owner']['S'],
                    'orig_path': item['orig_path']['S'],
                    'processed_path': item['processed_path']['S'] if item['processed_path']['S'] else None,
                    'created_at': item['created_at']['S'],
                    'status': item['status']['S']
                }
                results.append(result)
            
            # Sort by created_at descending
            results.sort(key=lambda x: x['created_at'], reverse=True)
            print(f"Found {len(results)} total images")
            return results
            
        except ClientError as e:
            print(f"Failed to list all images: {e}")
            return []

    def update_image_processed_path(self, image_id: str, processed_path: str):
        """Update processed path following QUT pattern"""
        try:
            self.dynamodb.update_item(
                TableName=self.images_table_name,
                Key={
                    "qut-username": {"S": self.qut_username},
                    "image_id": {"S": image_id}
                },
                UpdateExpression="SET processed_path = :path",
                ExpressionAttributeValues={
                    ":path": {"S": processed_path}
                }
            )
            print(f"Updated processed path for {image_id}")
        except ClientError as e:
            print(f"Failed to update processed path: {e}")
            raise

    # ========== JOB OPERATIONS ==========

    def create_job_record(self, job_id: str, owner: str, image_id: str, 
                         extra_passes: int, blur_strength: int = 12) -> Dict:
        """Create job record following QUT pattern"""
        try:
            response = self.dynamodb.put_item(
                TableName=self.jobs_table_name,
                Item={
                    "qut-username": {"S": self.qut_username},  # Partition key
                    "job_id": {"S": job_id},  # Sort key
                    "owner": {"S": owner},
                    "image_id": {"S": image_id},
                    "extra_passes": {"N": str(extra_passes)},
                    "blur_strength": {"N": str(blur_strength)},
                    "status": {"S": "pending"},
                    "duration_ms": {"N": "0"},
                    "created_at": {"S": datetime.utcnow().isoformat()}
                }
            )
            print(f"Created job record: {job_id}")
            
            # Return in app format
            return {
                'id': job_id,
                'owner': owner,
                'image_id': image_id,
                'extra_passes': extra_passes,
                'blur_strength': blur_strength,
                'status': 'pending',
                'duration_ms': None,
                'outputs': [],
                'created_at': datetime.utcnow().isoformat()
            }
        except ClientError as e:
            print(f"Failed to create job: {e}")
            raise Exception(f"Failed to create job record: {e}")

    def update_job_completion(self, job_id: str, duration_ms: int, outputs: List[Dict], status: str = 'done'):
        """Update job completion following QUT pattern"""
        try:
            self.dynamodb.update_item(
                TableName=self.jobs_table_name,
                Key={
                    "qut-username": {"S": self.qut_username},
                    "job_id": {"S": job_id}
                },
                UpdateExpression="SET #status = :status, duration_ms = :duration",
                ExpressionAttributeNames={
                    "#status": "status"  # status is a reserved word
                },
                ExpressionAttributeValues={
                    ":status": {"S": status},
                    ":duration": {"N": str(duration_ms)}
                }
            )
            print(f"Updated job completion: {job_id}")
        except ClientError as e:
            print(f"Failed to update job completion: {e}")
            raise

    def list_jobs_for_user(self, owner: str, limit: int = 20) -> List[Dict]:
        """List jobs for user following QUT pattern"""
        try:
            response = self.dynamodb.query(
                TableName=self.jobs_table_name,
                KeyConditionExpression="qut-username = :username",
                ExpressionAttributeValues={
                    ":username": {"S": self.qut_username}
                },
                Limit=limit
            )
            
            items = response.get('Items', [])
            
            # Convert and filter by owner
            results = []
            for item in items:
                if item['owner']['S'] == owner:
                    result = {
                        'id': item['job_id']['S'],
                        'owner': item['owner']['S'],
                        'image_id': item['image_id']['S'],
                        'extra_passes': int(item['extra_passes']['N']),
                        'blur_strength': int(item['blur_strength']['N']),
                        'status': item['status']['S'],
                        'duration_ms': int(item['duration_ms']['N']) if item['duration_ms']['N'] != '0' else None,
                        'created_at': item['created_at']['S']
                    }
                    results.append(result)
            
            # Sort by created_at descending
            results.sort(key=lambda x: x['created_at'], reverse=True)
            print(f"Found {len(results)} jobs for user {owner}")
            return results
            
        except ClientError as e:
            print(f"Failed to list jobs for {owner}: {e}")
            return []

    def list_all_jobs(self, limit: int = 20) -> List[Dict]:
        """List all jobs for admin users"""
        try:
            response = self.dynamodb.query(
                TableName=self.jobs_table_name,
                KeyConditionExpression="qut-username = :username",
                ExpressionAttributeValues={
                    ":username": {"S": self.qut_username}
                },
                Limit=limit
            )
            
            items = response.get('Items', [])
            
            # Convert format
            results = []
            for item in items:
                result = {
                    'id': item['job_id']['S'],
                    'owner': item['owner']['S'],
                    'image_id': item['image_id']['S'],
                    'extra_passes': int(item['extra_passes']['N']),
                    'blur_strength': int(item['blur_strength']['N']),
                    'status': item['status']['S'],
                    'duration_ms': int(item['duration_ms']['N']) if item['duration_ms']['N'] != '0' else None,
                    'created_at': item['created_at']['S']
                }
                results.append(result)
            
            # Sort by created_at descending
            results.sort(key=lambda x: x['created_at'], reverse=True)
            print(f"Found {len(results)} total jobs")
            return results
            
        except ClientError as e:
            print(f"Failed to list all jobs: {e}")
            return []

# Create global instance
db_service = None

def get_db_service() -> DynamoDBService:
    """Get database service instance - singleton pattern"""
    global db_service
    if db_service is None:
        db_service = DynamoDBService()
    return db_service