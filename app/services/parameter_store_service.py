import boto3
import os
from botocore.exceptions import ClientError

class ParameterStoreService:
    def __init__(self):
        self.region = "ap-southeast-2"
        self.ssm = boto3.client('ssm', region_name=self.region)
        
        student_number = 'n11544309'
        self.prefix = f"/{student_number}/imagelab"
        

    def get_app_config(self):
        # define all required parameters
        required_param_names = [
            'app-url', 's3-bucket-name', 'dynamodb-images-table',
            'dynamodb-jobs-table', 'cognito-client-id',
            'cognito-user-pool-id', 'cognito-domain'
        ]

        # Optional parameters with defaults
        optional_param_names = [
            'cloudfront-domain'
        ]

        config = {}

        # Get required parameters
        for param_name in required_param_names:
            full_param_name = f"{self.prefix}/{param_name}"
            try:
                response = self.ssm.get_parameter(Name=full_param_name)
                clean_name = param_name.replace("-", "_")
                config[clean_name] = response['Parameter']['Value']
            except Exception as e:
                raise Exception(f"Failed to get parameter {full_param_name}: {e}")

        # Get optional parameters
        for param_name in optional_param_names:
            full_param_name = f"{self.prefix}/{param_name}"
            try:
                response = self.ssm.get_parameter(Name=full_param_name)
                clean_name = param_name.replace("-", "_")
                config[clean_name] = response['Parameter']['Value']
            except:
                # Optional parameter not found, skip it
                pass

        required_params = ['app_url', 's3_bucket_name', 'dynamodb_images_table', 'dynamodb_jobs_table', 'cognito_client_id', 'cognito_user_pool_id', 'cognito_domain']
        missing_params = [param for param in required_params if param not in config]

        if missing_params:
            raise ValueError(f"Missing required parameters in Parameter Store: {missing_params}")

        app_config = {
            'app_url': config['app_url'],
            's3_bucket_name': config['s3_bucket_name'],
            'dynamodb_images_table': config['dynamodb_images_table'],
            'dynamodb_jobs_table': config['dynamodb_jobs_table'],
            'cognito_client_id': config['cognito_client_id'],
            'cognito_user_pool_id': config['cognito_user_pool_id'],
            'cognito_domain': config['cognito_domain'],
            'cloudfront_domain': config.get('cloudfront_domain', 'd2vmmt2bt8b124.cloudfront.net')
        }

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