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
        response = self.ssm.get_parameters_by_path(
            Path=self.prefix,
            Recursive=True
        )

        config = {}
        for param in response['Parameters']:
            clean_name = param['Name'].replace(f"{self.prefix}/", "").replace("-", "_")
            config[clean_name] = param['Value']

        print(f"Retrieved {len(config)} parameters from Parameter Store")

        # Require all parameters to be present in Parameter Store
        required_params = ['app_url', 's3_bucket_name', 'dynamodb_images_table', 'dynamodb_jobs_table']
        missing_params = [param for param in required_params if param not in config]

        if missing_params:
            raise ValueError(f"Missing required parameters in Parameter Store: {missing_params}")

        app_config = {
            'app_url': config['app_url'],
            's3_bucket_name': config['s3_bucket_name'],
            'dynamodb_images_table': config['dynamodb_images_table'],
            'dynamodb_jobs_table': config['dynamodb_jobs_table']
        }

        print("Configuration loaded from Parameter Store:")
        for key, value in app_config.items():
            print(f"   {key}: {value}")

        return app_config

_parameter_store = None

def get_parameter_store():
    global _parameter_store
    if _parameter_store is None:
        _parameter_store = ParameterStoreService()
    return _parameter_store

def get_app_config():
    parameter_store = get_parameter_store()
    return parameter_store.get_app_config()