import boto3
import os
from botocore.exceptions import ClientError

class ParameterStoreService:
    def __init__(self):
        self.region = "ap-southeast-2"
        self.ssm = boto3.client('ssm', region_name=self.region)
        
        student_number = os.getenv('STUDENT_NUMBER', 'n11544309')
        self.prefix = f"/{student_number}/imagelab"
        
        print(f"Parameter Store initialized with prefix: {self.prefix}")

    def get_app_config(self):
        try:
            response = self.ssm.get_parameters_by_path(
                Path=self.prefix,
                Recursive=True
            )
            
            config = {}
            for param in response['Parameters']:
                clean_name = param['Name'].replace(f"{self.prefix}/", "").replace("-", "_")
                config[clean_name] = param['Value']
            
            print(f"Retrieved {len(config)} parameters from Parameter Store")
            
            app_config = {
                'app_url': config.get('app_url', os.getenv('APP_URL', 'http://localhost:8080')),
                's3_bucket_name': config.get('s3_bucket_name', f"{os.getenv('STUDENT_NUMBER', 'default')}-imagelab-bucket"),
                'dynamodb_images_table': config.get('dynamodb_images_table', f"{os.getenv('STUDENT_NUMBER', 'default')}-imagelab-images"),
                'dynamodb_jobs_table': config.get('dynamodb_jobs_table', f"{os.getenv('STUDENT_NUMBER', 'default')}-imagelab-jobs")
            }
            
            print("Configuration loaded:")
            for key, value in app_config.items():
                print(f"   {key}: {value}")
            
            return app_config
            
        except ClientError as error:
            print(f"Failed to get parameters from Parameter Store: {error}")
            print("Falling back to environment variables")
            
            student_number = os.getenv('STUDENT_NUMBER', 'n11544309')
            return {
                'app_url': os.getenv('APP_URL', 'http://localhost:8080'),
                's3_bucket_name': os.getenv('S3_BUCKET_NAME', f"{student_number}-imagelab-bucket"),
                'dynamodb_images_table': os.getenv('DYNAMODB_IMAGES_TABLE', f"{student_number}-imagelab-images"),
                'dynamodb_jobs_table': os.getenv('DYNAMODB_JOBS_TABLE', f"{student_number}-imagelab-jobs")
            }

_parameter_store = None

def get_parameter_store():
    global _parameter_store
    if _parameter_store is None:
        _parameter_store = ParameterStoreService()
    return _parameter_store

def get_app_config():
    parameter_store = get_parameter_store()
    return parameter_store.get_app_config()