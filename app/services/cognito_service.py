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
            
            # Auto-assign new users to 'user' group
            try:
                self.add_user_to_group(username, 'user')
                print(f"Auto-assigned {username} to 'user' group")
            except Exception as e:
                print(f"Failed to auto-assign user to group: {e}")
            
            return {'success': True, 'message': 'Email confirmed'}
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def authenticate(self, username, password):
        """Enhanced login with required MFA support"""
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
            
            # With required MFA, we should always get a challenge
            if 'ChallengeName' in response:
                return {
                    'success': True,
                    'challenge_required': True,
                    'challenge_name': response['ChallengeName'],
                    'session': response['Session'],
                    'username': username,
                    'message': 'Please check your email for verification code'
                }
            
            # This case should rarely happen with required MFA, but handle gracefully
            elif 'AuthenticationResult' in response:
                tokens = response["AuthenticationResult"]
                return {
                    'success': True,
                    'challenge_required': False,
                    'access_token': tokens['AccessToken'],
                    'id_token': tokens['IdToken'],
                    'token_type': 'Bearer'
                }
            
            # Unexpected response format
            else:
                print(f"Unexpected response format: {response}")
                return {
                    'success': False, 
                    'error': 'Unexpected authentication response format'
                }
                
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def respond_to_auth_challenge(self, session, challenge_response, username):
        """Handle MFA email challenge"""
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
        """Verify token and get user info with groups"""
        try:
            response = self.cognito_client.get_user(AccessToken=access_token)
            username = response['Username']
            
            # Get user's groups
            groups = self.get_user_groups(username)
            
            # Determine primary role (highest priority group)
            role = self._determine_primary_role(groups)
            
            return {
                'success': True,
                'username': username,
                'role': role,
                'groups': groups
            }
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def get_user_groups(self, username):
        """Get all groups for a user"""
        try:
            response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            return [group['GroupName'] for group in response['Groups']]
        except ClientError as e:
            print(f"Failed to get user groups: {e}")
            return ['user']  # Default fallback

    def _determine_primary_role(self, groups):
        """Determine primary role from groups (admin > user)"""
        if 'admin' in groups:
            return 'admin'
        elif 'user' in groups:
            return 'user'
        else:
            return 'user'  # Default

    def add_user_to_group(self, username, group_name):
        """Add user to a group"""
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
        """Remove user from a group"""
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
        """List all available groups"""
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
        """Create a new group"""
        try:
            self.cognito_client.create_group(
                GroupName=group_name,
                UserPoolId=self.user_pool_id,
                Description=description
            )
            return {'success': True, 'message': f'Group {group_name} created'}
        except ClientError as e:
            return {'success': False, 'error': str(e)}

    def set_user_mfa_preference(self, access_token, email_enabled=True):
        """Enable/disable email MFA for a user"""
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

# Global instance
_cognito = None
def get_cognito():
    global _cognito
    if _cognito is None:
        _cognito = CognitoService()
    return _cognito