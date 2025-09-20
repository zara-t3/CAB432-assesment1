import boto3
import os
import json
from botocore.exceptions import ClientError

class SecretsManagerService:
    def __init__(self):
        self.region = "ap-southeast-2"
        self.client = boto3.client('secretsmanager', region_name=self.region)
        
        student_number = os.getenv('STUDENT_NUMBER', 'n11544309')
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
            pass
            pass
            
            # Fallback to environment variables
            fallback_secrets = {
                'cognito_client_secret': os.getenv('COGNITO_CLIENT_SECRET', ''),
                'jwt_secret': os.getenv('JWT_SECRET', 'devsecret')
            }
            return fallback_secrets
    
    def get_secret(self, key, default=None):
        """Get a specific secret by key"""
        secrets = self.get_secrets()
        return secrets.get(key, default)

# Global instance
_secrets_manager = None

def get_secrets_manager():
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManagerService()
    return _secrets_manager

def get_secret(key, default=None):
    """Convenience function to get a secret"""
    secrets_manager = get_secrets_manager()
    return secrets_manager.get_secret(key, default)