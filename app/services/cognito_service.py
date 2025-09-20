import boto3
import hmac, hashlib, base64
import os
from botocore.exceptions import ClientError
from .secrets_manager_service import get_secret 

class CognitoService:
    def __init__(self):
        self.client_id = os.getenv('COGNITO_CLIENT_ID')
        self.user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
        
        self.client_secret = get_secret('cognito_client_secret')
        if not self.client_secret:
            self.client_secret = os.getenv('COGNITO_CLIENT_SECRET', '')
        
        self.cognito_client = boto3.client("cognito-idp", region_name="ap-southeast-2")

    def secret_hash(self, username):
        message = bytes(username + self.client_id, 'utf-8') 
        key = bytes(self.client_secret, 'utf-8') 
        return base64.b64encode(hmac.new(key, message, digestmod=hashlib.sha256).digest()).decode()

    def sign_up(self, username, password, email):
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
        try:
            response = self.cognito_client.confirm_sign_up(
                ClientId=self.client_id,
                Username=username,
                ConfirmationCode=confirmation_code,
                SecretHash=self.secret_hash(username)
            )
            
            try:
                self.add_user_to_group(username, 'user')
            except Exception:
                pass
            
            return {'success': True, 'message': 'Email confirmed'}
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def authenticate(self, username, password):
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
            
            if 'ChallengeName' in response:
                return {
                    'success': True,
                    'challenge_required': True,
                    'challenge_name': response['ChallengeName'],
                    'session': response['Session'],
                    'username': username,
                    'message': 'Please check your email for verification code'
                }
            
            elif 'AuthenticationResult' in response:
                tokens = response["AuthenticationResult"]
                return {
                    'success': True,
                    'challenge_required': False,
                    'access_token': tokens['AccessToken'],
                    'id_token': tokens['IdToken'],
                    'token_type': 'Bearer'
                }
            
            else:
                return {
                    'success': False,
                    'error': 'Unexpected authentication response format'
                }
                
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def respond_to_auth_challenge(self, session, challenge_response, username):
        try:
            response = self.cognito_client.respond_to_auth_challenge(
                ClientId=self.client_id,
                ChallengeName='EMAIL_OTP',
                Session=session,
                ChallengeResponses={
                    'EMAIL_OTP_CODE': challenge_response,
                    'USERNAME': username,
                    'SECRET_HASH': self.secret_hash(username)
                }
            )
            
            if 'AuthenticationResult' in response:
                tokens = response["AuthenticationResult"]
                return {
                    'success': True,
                    'access_token': tokens['AccessToken'],
                    'id_token': tokens['IdToken'],
                    'token_type': 'Bearer'
                }
            else:
                return {'success': False, 'error': 'Challenge response failed'}
                
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def verify_token(self, access_token):
        try:
            response = self.cognito_client.get_user(AccessToken=access_token)
            username = response['Username']
            
            groups = self.get_user_groups(username)
            
            role = self._determine_primary_role(groups)
            
            return {
                'success': True,
                'username': username,
                'role': role,
                'groups': groups
            }
        except ClientError as e:
            try:
                import json
                import base64
                
                parts = access_token.split('.')
                if len(parts) == 3:
                    payload = parts[1]
                    payload += '=' * (4 - len(payload) % 4)
                    decoded = base64.b64decode(payload)
                    token_data = json.loads(decoded)
                    
                    username = token_data.get('cognito:username') or token_data.get('username')
                    
                    if username:
                        groups = self.get_user_groups(username)
                        role = self._determine_primary_role(groups)
                        
                        return {
                            'success': True,
                            'username': username,
                            'role': role,
                            'groups': groups
                        }
                
            except Exception:
                pass

            return {'success': False, 'error': str(e)}

    def _determine_primary_role(self, groups):
        if 'admin' in groups:
            return 'admin'
        elif 'user' in groups:
            return 'user'
        else:
            return 'user'

    def add_user_to_group(self, username, group_name):
        try:
            self.cognito_client.admin_add_user_to_group(
                UserPoolId=self.user_pool_id,
                Username=username,
                GroupName=group_name
            )
            return {'success': True, 'message': f'User added to {group_name} group'}
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def remove_user_from_group(self, username, group_name):
        try:
            self.cognito_client.admin_remove_user_from_group(
                UserPoolId=self.user_pool_id,
                Username=username,
                GroupName=group_name
            )
            return {'success': True, 'message': f'User removed from {group_name} group'}
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def list_groups(self):
        try:
            response = self.cognito_client.list_groups(
                UserPoolId=self.user_pool_id
            )
            return {
                'success': True, 
                'groups': [
                    {
                        'name': group['GroupName'],
                        'description': group.get('Description', ''),
                        'creation_date': group['CreationDate'].isoformat() if 'CreationDate' in group else None
                    }
                    for group in response['Groups']
                ]
            }
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def create_group(self, group_name, description=""):
        try:
            self.cognito_client.create_group(
                GroupName=group_name,
                UserPoolId=self.user_pool_id,
                Description=description
            )
            return {'success': True, 'message': f'Group {group_name} created'}
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def get_user_groups(self, username):
        try:
            response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            return [group['GroupName'] for group in response['Groups']]
        except ClientError:
            return ['user']

    def set_user_mfa_preference(self, access_token, email_enabled=True):
        try:
            self.cognito_client.set_user_mfa_preference(
                AccessToken=access_token,
                EmailMfaSettings={
                    'Enabled': email_enabled,
                    'PreferredMfa': email_enabled
                }
            )
            return {'success': True, 'message': f'Email MFA {"enabled" if email_enabled else "disabled"}'}
        except ClientError as e:
            return {'success': False, 'error': str(e)}

_cognito = None
def get_cognito():
    global _cognito
    if _cognito is None:
        _cognito = CognitoService()
    return _cognito