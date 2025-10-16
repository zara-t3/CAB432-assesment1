import boto3
import os
from datetime import datetime
from typing import Dict, List, Optional
from flask import current_app
from botocore.exceptions import ClientError
import uuid

class DynamoDBService:
    def __init__(self):
        self.qut_username = "n11544309@qut.edu.au" 
        self.student_number = "n11544309" 
        
        self.dynamodb = boto3.client('dynamodb', region_name='ap-southeast-2')
        self.dynamodb_resource = boto3.resource('dynamodb', region_name='ap-southeast-2')
        
        try:
            self.images_table_name = current_app.config.get('DYNAMODB_IMAGES_TABLE')
            self.jobs_table_name = current_app.config.get('DYNAMODB_JOBS_TABLE')
            if self.images_table_name and self.jobs_table_name:
                source = "Parameter Store" if current_app.config.get('PARAMETER_STORE_ENABLED') else "Environment Variables"
            else:
                self.images_table_name = f'{self.student_number}-imagelab-images'
                self.jobs_table_name = f'{self.student_number}-imagelab-jobs'
        except RuntimeError:
            self.images_table_name = f'{self.student_number}-imagelab-images'
            self.jobs_table_name = f'{self.student_number}-imagelab-jobs'
        
        self.images_table = self.dynamodb_resource.Table(self.images_table_name)
        self.jobs_table = self.dynamodb_resource.Table(self.jobs_table_name)

    def create_image_record(self, image_id: str, name: str, owner: str, s3_key: str) -> Dict:
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
                    "faces_detected": {"N": "0"},
                    "original_width": {"N": "0"},
                    "original_height": {"N": "0"},
                    "processing_time": {"S": ""},
                    "created_at": {"S": datetime.utcnow().isoformat()},
                    "status": {"S": "uploaded"}
                }
            )
            pass
            
            return {
                'id': image_id,
                'name': name,
                'owner': owner,
                's3_key': s3_key,
                'processed_s3_key': None,
                'thumb_s3_key': None,
                'faces_detected': 0,
                'original_width': 0,
                'original_height': 0,
                'processing_time': '',
                'created_at': datetime.utcnow().isoformat(),
                'status': 'uploaded'
            }
        except ClientError as e:
            pass
            raise Exception(f"Failed to create image record: {e}")

    def get_image(self, image_id: str) -> Optional[Dict]:
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
                'faces_detected': int(item.get('faces_detected', {}).get('N', '0')),
                'original_width': int(item.get('original_width', {}).get('N', '0')),
                'original_height': int(item.get('original_height', {}).get('N', '0')),
                'processing_time': item.get('processing_time', {}).get('S', ''),
                'created_at': item['created_at']['S'],
                'status': item['status']['S']
            }
            pass
            return result
            
        except ClientError as e:
            pass
            return None

    def list_images_for_user(self, owner: str, limit: int = 20) -> List[Dict]:
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
            pass
            return results
            
        except ClientError as e:
            pass
            return []

    def list_all_images(self, limit: int = 20) -> List[Dict]:
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
            pass
            return results
            
        except ClientError as e:
            pass
            return []

    def update_processed_s3_key(self, image_id: str, processed_s3_key: str):
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
            pass
        except ClientError as e:
            pass
            raise

    def update_thumb_s3_key(self, image_id: str, thumb_s3_key: str):
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
            pass
        except ClientError as e:
            pass
            raise

    def update_processing_metadata(self, image_id: str, faces_detected: int,
                                 original_width: int, original_height: int, processing_time: str):
        try:
            self.dynamodb.update_item(
                TableName=self.images_table_name,
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
            pass
        except ClientError as e:
            pass
            raise

    def _convert_item_to_dict(self, item: Dict) -> Dict:
        return {
            'id': item['image_id']['S'],
            'name': item['name']['S'],
            'owner': item['owner']['S'],
            's3_key': item.get('s3_key', {}).get('S', ''),
            'processed_s3_key': item.get('processed_s3_key', {}).get('S', '') or None,
            'thumb_s3_key': item.get('thumb_s3_key', {}).get('S', '') or None,
            'faces_detected': int(item.get('faces_detected', {}).get('N', '0')),
            'original_width': int(item.get('original_width', {}).get('N', '0')),
            'original_height': int(item.get('original_height', {}).get('N', '0')),
            'processing_time': item.get('processing_time', {}).get('S', ''),
            'created_at': item['created_at']['S'],
            'status': item['status']['S']
        }

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
                    "status": {"S": "queued"},
                    "duration_ms": {"N": "0"},
                    "created_at": {"S": datetime.utcnow().isoformat()}
                }
            )
            pass

            return {
                'id': job_id,
                'owner': owner,
                'image_id': image_id,
                'extra_passes': extra_passes,
                'blur_strength': blur_strength,
                'status': 'queued',
                'duration_ms': None,
                'outputs': [],
                'created_at': datetime.utcnow().isoformat()
            }
        except ClientError as e:
            pass
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
            pass
        except ClientError as e:
            pass
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
            pass
            return results
            
        except ClientError as e:
            pass
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
            pass
            return results
            
        except ClientError as e:
            pass
            return []

    def store_image_metadata(self, user_id, image_id, filename, s3_key):
        try:
            return self.create_image_record(image_id, filename, user_id, s3_key)
        except:
            return False

    def get_user_images(self, user_id):
        return self.list_images_for_user(user_id)

    def store_job_record(self, user_id, job_id, job_type, input_s3_key, status='pending'):
        try:
            return self.create_job_record(job_id, user_id, "unknown", 0, 12)
        except:
            return False

    def get_user_jobs(self, user_id):
        return self.list_jobs_for_user(user_id)


db_service = None

def get_db_service() -> DynamoDBService:
    global db_service
    if db_service is None:
        db_service = DynamoDBService()
    return db_service

def get_dynamodb_service():
    return get_db_service()

__all__ = ['get_db_service', 'get_dynamodb_service', 'DynamoDBService']