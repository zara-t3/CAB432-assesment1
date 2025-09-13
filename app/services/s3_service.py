import boto3
import os
import tempfile
from datetime import datetime
from typing import Dict, Optional, BinaryIO
from botocore.exceptions import ClientError
from PIL import Image
import io

class S3Service:
    def __init__(self):
        self.student_number = "n11544309"
        self.qut_username = "n11544309@qut.edu.au"
        
      
        self.s3_client = boto3.client('s3', region_name='ap-southeast-2')
        
        self.bucket_name = f'{self.student_number}-imagelab-bucket'
        
        print(f"S3 Service initialized for bucket: {self.bucket_name}")
    
    def configure_cors(self):
        """Configure CORS policy for direct browser uploads"""
        cors_configuration = {
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'POST', 'PUT'],
                    'AllowedOrigins': ['*'],  
                    'ExposeHeaders': ['ETag'],
                    'MaxAgeSeconds': 3000
                }
            ]
        }
        
        try:
            self.s3_client.put_bucket_cors(
                Bucket=self.bucket_name,
                CORSConfiguration=cors_configuration
            )
            print(f"Configured CORS for bucket: {self.bucket_name}")
            return True
        except ClientError as e:
            print(f"Failed to configure CORS: {e}")
            return False
    
    def create_bucket_if_not_exists(self):
        """Create S3 bucket with required QUT tags and CORS"""
        try:
            
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            print(f"Bucket {self.bucket_name} already exists")
            
            
            self.configure_cors()
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                
                try:
                    response = self.s3_client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': 'ap-southeast-2'}
                    )
                    print(f"Created bucket: {self.bucket_name}")
                    
                    self.s3_client.put_bucket_tagging(
                        Bucket=self.bucket_name,
                        Tagging={
                            'TagSet': [
                                {'Key': 'qut-username', 'Value': self.qut_username},
                                {'Key': 'purpose', 'Value': 'assessment-2'}
                            ]
                        }
                    )
                    print("Added QUT tags to bucket")
                    
                  
                    self.configure_cors()
                    
                    return True
                    
                except ClientError as create_error:
                    print(f"Failed to create bucket: {create_error}")
                    return False
            else:
                print(f"Error checking bucket: {e}")
                return False
    
    def upload_image(self, file_obj: BinaryIO, user: str, image_id: str, filename: str = "original.jpg") -> str:
        """Upload image file to S3 and return S3 key"""
        try:
            
            s3_key = f"images/{user}/{image_id}/{filename}"
            
          
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': 'image/jpeg',
                    'Metadata': {
                        'user': user,
                        'image_id': image_id,
                        'uploaded_at': datetime.utcnow().isoformat()
                    }
                }
            )
            
            print(f"Uploaded image to S3: {s3_key}")
            return s3_key
            
        except ClientError as e:
            print(f"Failed to upload image to S3: {e}")
            raise Exception(f"S3 upload failed: {e}")
    
    def upload_processed_image(self, local_file_path: str, user: str, image_id: str, filename: str) -> str:
        """Upload processed image from local file to S3"""
        try:
            s3_key = f"images/{user}/{image_id}/processed/{filename}"
            
            self.s3_client.upload_file(
                local_file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': self._get_content_type(filename),
                    'Metadata': {
                        'user': user,
                        'image_id': image_id,
                        'processed_at': datetime.utcnow().isoformat()
                    }
                }
            )
            
            print(f"Uploaded processed image to S3: {s3_key}")
            return s3_key
            
        except ClientError as e:
            print(f"Failed to upload processed image: {e}")
            raise Exception(f"S3 processed upload failed: {e}")
    
    def download_image(self, s3_key: str) -> bytes:
        """Download image from S3 as bytes"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response['Body'].read()
            
        except ClientError as e:
            print(f"Failed to download from S3: {e}")
            raise Exception(f"S3 download failed: {e}")
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600, method: str = 'get_object') -> str:
        """Generate pre-signed URL for direct client access"""
        try:
            url = self.s3_client.generate_presigned_url(
                method,
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
            
        except ClientError as e:
            print(f"Failed to generate pre-signed URL: {e}")
            raise Exception(f"Pre-signed URL generation failed: {e}")
    
    def generate_presigned_upload_url(self, s3_key: str, content_type: str = 'image/jpeg', expiration: int = 3600) -> Dict:
        """Generate pre-signed URL for direct client upload with proper conditions"""
        try:
            conditions = [
                {'Content-Type': content_type},
                ['content-length-range', 1, 10 * 1024 * 1024],
                {'key': s3_key}
            ]
            
            fields = {
                'Content-Type': content_type
            }
            
            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=s3_key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expiration
            )
            
            print(f"Generated pre-signed upload URL for: {s3_key}")
            
            return {
                'url': response['url'],
                'fields': response['fields'],
                'expires_in': expiration
            }
            
        except ClientError as e:
            print(f"Failed to generate pre-signed upload URL: {e}")
            raise Exception(f"Pre-signed upload URL generation failed: {e}")
    
    def create_thumbnail(self, s3_key: str, user: str, image_id: str, size: tuple = (160, 160)) -> str:
        """Download image, create thumbnail, upload back to S3"""
        try:
            
            image_data = self.download_image(s3_key)
            
            with Image.open(io.BytesIO(image_data)) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                thumb_io = io.BytesIO()
                img.save(thumb_io, format='JPEG', quality=80, optimize=True)
                thumb_io.seek(0)
            
                thumb_s3_key = f"images/{user}/{image_id}/thumb_160.jpg"
                self.s3_client.upload_fileobj(
                    thumb_io,
                    self.bucket_name,
                    thumb_s3_key,
                    ExtraArgs={'ContentType': 'image/jpeg'}
                )
                
                print(f"Created thumbnail: {thumb_s3_key}")
                return thumb_s3_key
                
        except Exception as e:
            print(f"Failed to create thumbnail: {e}")
            raise Exception(f"Thumbnail creation failed: {e}")
    
    def delete_image(self, s3_key: str):
        """Delete image from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            print(f"Deleted from S3: {s3_key}")
            
        except ClientError as e:
            print(f"Failed to delete from S3: {e}")
            raise Exception(f"S3 delete failed: {e}")
    
    def verify_object_exists(self, s3_key: str) -> bool:
        """Verify that an object exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise Exception(f"Error checking S3 object: {e}")
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension"""
        ext = filename.lower().split('.')[-1]
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg', 
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        return content_types.get(ext, 'application/octet-stream')

s3_service = None

def get_s3_service() -> S3Service:
    """Get S3 service instance - singleton pattern"""
    global s3_service
    if s3_service is None:
        s3_service = S3Service()
        s3_service.create_bucket_if_not_exists()
    return s3_service