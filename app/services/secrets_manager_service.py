import boto3
import os
import json
from botocore.exceptions import ClientError

class SecretsManagerService:
    def __init__(self):
        self.region = "ap-southeast-2"
        self.client = boto3.client('secretsmanager', region_name=self.region)
        
        student_number = 'n11544309'
        self.secret_name = f"{student_number}-imagelab-secrets"
        
        self._cached_secrets = None

    def get_secrets(self):
        """Get all secrets from AWS Secrets Manager with caching"""
        if self._cached_secrets is not None:
            return self._cached_secrets
            
        try:
            response = self.client.get_secret_value(SecretId=self.secret_name)
            secret_string = response['SecretString']
            secrets = json.loads(secret_string)
            
            self._cached_secrets = secrets
            pass
            return secrets
            
        except ClientError as e:
            raise Exception(f"Failed to retrieve secrets from Secrets Manager: {e}")
    
    def get_secret(self, key, default=None):
        secrets = self.get_secrets()
        return secrets.get(key, default)


_secrets_manager = None

def get_secrets_manager():
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManagerService()
    return _secrets_manager

def get_secret(key, default=None):
    secrets_manager = get_secrets_manager()
    return secrets_manager.get_secret(key, default)