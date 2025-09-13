import boto3
import os
from datetime import datetime
from typing import Dict, List, Optional
from botocore.exceptions import ClientError
import uuid

class DynamoDBService:
    def __init__(self):
        # CHANGE TO YOUR STUDENT NUMBER
        self.qut_username = "n11544309@qut.edu.au" 
        self.student_number = "n11544309" 
        
        self.dynamodb = boto3.client('dynamodb', region_name='ap-southeast-2')
        
        self.images_table_name = f'{self.student_number}-imagelab-images'
        self.jobs_table_name = f'{self.student_number}-imagelab-jobs'
        
        print(f"DynamoDB service initialized for {self.qut_username}")

    def create_image_record(self, image_id: str, name: str, owner: str, s3_key: str) -> Dict:
        """Create image record with S3 key"""
        try:
            response = self.dynamodb.put_item(
                TableName=self.images_table_name,
                Item={
                    "qut-username": {"S": self.qut_username},
                    "image_id": {"S": image_id},
                    "name": {"S": name},
                    "owner": {"S": owner},
                    "s3_key": {"S": s3_key},
                    "processed_s3_key": {"S": ""},
                    "thumb_s3_key": {"S": ""},
                    "created_at": {"S": datetime.utcnow().isoformat()},
                    "status": {"S": "uploaded"}
                }
            )
            print(f"Created image record with S3: {image_id}")
            
            return {
                'id': image_id,
                'name': name,
                'owner': owner,
                's3_key': s3_key,
                'processed_s3_key': None,
                'thumb_s3_key': None,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'uploaded'
            }
        except ClientError as e:
            print(f"Failed to create image: {e}")
            raise Exception(f"Failed to create image record: {e}")

    def get_image(self, image_id: str) -> Optional[Dict]:
        """Get single image with S3 keys"""
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
                
            result = {
                'id': item['image_id']['S'],
                'name': item['name']['S'],
                'owner': item['owner']['S'],
                's3_key': item.get('s3_key', {}).get('S', ''),
                'processed_s3_key': item.get('processed_s3_key', {}).get('S', '') or None,
                'thumb_s3_key': item.get('thumb_s3_key', {}).get('S', '') or None,
                'created_at': item['created_at']['S'],
                'status': item['status']['S']
            }
            print(f"Retrieved image: {image_id}")
            return result
            
        except ClientError as e:
            print(f"Failed to get image {image_id}: {e}")
            return None

    def list_images_for_user(self, owner: str, limit: int = 20) -> List[Dict]:
        """List images for user with S3 keys"""
        try:
            response = self.dynamodb.query(
                TableName=self.images_table_name,
                KeyConditionExpression="#pk = :username",
                ExpressionAttributeNames={
                    "#pk": "qut-username"
                },
                ExpressionAttributeValues={
                    ":username": {"S": self.qut_username}
                },
                Limit=limit
            )
            
            items = response.get('Items', [])
            
            results = []
            for item in items:
                if item['owner']['S'] == owner:
                    result = self._convert_item_to_dict(item)
                    results.append(result)
            
            results.sort(key=lambda x: x['created_at'], reverse=True)
            print(f"Found {len(results)} images for user {owner}")
            return results
            
        except ClientError as e:
            print(f"Failed to list images for {owner}: {e}")
            return []

    def list_all_images(self, limit: int = 20) -> List[Dict]:
        """List all images with S3 keys"""
        try:
            response = self.dynamodb.query(
                TableName=self.images_table_name,
                KeyConditionExpression="#pk = :username",
                ExpressionAttributeNames={
                    "#pk": "qut-username"
                },
                ExpressionAttributeValues={
                    ":username": {"S": self.qut_username}
                },
                Limit=limit
            )
            
            items = response.get('Items', [])
            
            results = []
            for item in items:
                result = self._convert_item_to_dict(item)
                results.append(result)
            
            results.sort(key=lambda x: x['created_at'], reverse=True)
            print(f"Found {len(results)} total images")
            return results
            
        except ClientError as e:
            print(f"Failed to list all images: {e}")
            return []

    def update_processed_s3_key(self, image_id: str, processed_s3_key: str):
        """Update processed S3 key"""
        try:
            self.dynamodb.update_item(
                TableName=self.images_table_name,
                Key={
                    "qut-username": {"S": self.qut_username},
                    "image_id": {"S": image_id}
                },
                UpdateExpression="SET processed_s3_key = :key",
                ExpressionAttributeValues={
                    ":key": {"S": processed_s3_key}
                }
            )
            print(f"Updated processed S3 key for {image_id}")
        except ClientError as e:
            print(f"Failed to update processed S3 key: {e}")
            raise

    def update_thumb_s3_key(self, image_id: str, thumb_s3_key: str):
        """Update thumbnail S3 key"""
        try:
            self.dynamodb.update_item(
                TableName=self.images_table_name,
                Key={
                    "qut-username": {"S": self.qut_username},
                    "image_id": {"S": image_id}
                },
                UpdateExpression="SET thumb_s3_key = :key",
                ExpressionAttributeValues={
                    ":key": {"S": thumb_s3_key}
                }
            )
            print(f"Updated thumbnail S3 key for {image_id}")
        except ClientError as e:
            print(f"Failed to update thumbnail S3 key: {e}")
            raise

    def _convert_item_to_dict(self, item: Dict) -> Dict:
        """Convert DynamoDB item to app format"""
        return {
            'id': item['image_id']['S'],
            'name': item['name']['S'],
            'owner': item['owner']['S'],
            's3_key': item.get('s3_key', {}).get('S', ''),
            'processed_s3_key': item.get('processed_s3_key', {}).get('S', '') or None,
            'thumb_s3_key': item.get('thumb_s3_key', {}).get('S', '') or None,
            'created_at': item['created_at']['S'],
            'status': item['status']['S']
        }

    # Job operations (same as before but keeping for completeness)
    def create_job_record(self, job_id: str, owner: str, image_id: str, 
                         extra_passes: int, blur_strength: int = 12) -> Dict:
        try:
            response = self.dynamodb.put_item(
                TableName=self.jobs_table_name,
                Item={
                    "qut-username": {"S": self.qut_username},
                    "job_id": {"S": job_id},
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
        try:
            self.dynamodb.update_item(
                TableName=self.jobs_table_name,
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
            print(f"Updated job completion: {job_id}")
        except ClientError as e:
            print(f"Failed to update job completion: {e}")
            raise

    def list_jobs_for_user(self, owner: str, limit: int = 20) -> List[Dict]:
        try:
            response = self.dynamodb.query(
                TableName=self.jobs_table_name,
                KeyConditionExpression="#pk = :username",
                ExpressionAttributeNames={
                    "#pk": "qut-username"
                },
                ExpressionAttributeValues={
                    ":username": {"S": self.qut_username}
                },
                Limit=limit
            )
            
            items = response.get('Items', [])
            
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
            
            results.sort(key=lambda x: x['created_at'], reverse=True)
            print(f"Found {len(results)} jobs for user {owner}")
            return results
            
        except ClientError as e:
            print(f"Failed to list jobs for {owner}: {e}")
            return []

    def list_all_jobs(self, limit: int = 20) -> List[Dict]:
        try:
            response = self.dynamodb.query(
                TableName=self.jobs_table_name,
                KeyConditionExpression="#pk = :username",
                ExpressionAttributeNames={
                    "#pk": "qut-username"
                },
                ExpressionAttributeValues={
                    ":username": {"S": self.qut_username}
                },
                Limit=limit
            )
            
            items = response.get('Items', [])
            
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
            
            results.sort(key=lambda x: x['created_at'], reverse=True)
            print(f"Found {len(results)} total jobs")
            return results
            
        except ClientError as e:
            print(f"Failed to list all jobs: {e}")
            return []

# Global instance
db_service = None

def get_db_service() -> DynamoDBService:
    """Get database service instance"""
    global db_service
    if db_service is None:
        db_service = DynamoDBService()
    return db_service