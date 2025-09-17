import boto3
import hmac, hashlib, base64
import os
from botocore.exceptions import ClientError
from .secrets_manager_service import get_secret 

class CognitoService:
    def __init__(self):
        self.client_id = os.getenv('COGNITO_CLIENT_ID')
        
        self.client_secret = get_secret('cognito_client_secret')
        if not self.client_secret:
            print("WARNING: Could not retrieve Cognito client secret from Secrets Manager")
            self.client_secret = os.getenv('COGNITO_CLIENT_SECRET', '')
            
        print(f"Cognito service initialized with secret from Secrets Manager: {'✓' if self.client_secret else '✗'}")
        
        self.cognito_client = boto3.client("cognito-idp", region_name="ap-southeast-2")

    def secret_hash(self, username):
        """From tutorial code"""
        message = bytes(username + self.client_id, 'utf-8') 
        key = bytes(self.client_secret, 'utf-8') 
        return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode()

    def sign_up(self, username, password, email):
        """From tutorial signUp.py"""
        try:
            response = self.cognito_client.sign_up(
                ClientId=self.client_id,
                Username=username,
                Password=password,
                SecretHash=self.secret_hash(username),
                UserAttributes=[{"Name": "email", "Value": email}]
            )
            return {'success': True, 'message': 'Check email for confirmation code'}
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def confirm_signup(self, username, confirmation_code):
        """From tutorial confirm.py"""
        try:
            response = self.cognito_client.confirm_sign_up(
                ClientId=self.client_id,
                Username=username,
                ConfirmationCode=confirmation_code,
                SecretHash=self.secret_hash(username)
            )
            return {'success': True, 'message': 'Email confirmed'}
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def authenticate(self, username, password):
        """From tutorial authenticate.py"""
        try:
            response = self.cognito_client.initiate_auth(
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": username,
                    "PASSWORD": password,
                    "SECRET_HASH": self.secret_hash(username)
                },
                ClientId=self.client_id
            )
            tokens = response["AuthenticationResult"]
            return {
                'success': True,
                'access_token': tokens['AccessToken'],
                'token_type': 'Bearer'
            }
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def verify_token(self, access_token):
        """Verify token and get user info"""
        try:
            response = self.cognito_client.get_user(AccessToken=access_token)
            return {
                'success': True,
                'username': response['Username'],
                'role': 'user'
            }
        except ClientError as e:
            return {'success': False, 'error': str(e)}

# Global instance
_cognito = None
def get_cognito():
    global _cognito
    if _cognito is None:
        _cognito = CognitoService()
    return _cognito