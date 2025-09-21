from functools import wraps
from flask import Blueprint, request, jsonify, g
from .services.cognito_service import get_cognito
import os          # Add this line
import requests  

auth_bp = Blueprint("auth", __name__)

def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing bearer token"}), 401
        
        token = auth.split(" ", 1)[1]
        
        try:
            cognito = get_cognito()
            result = cognito.verify_token(token)
            if result['success']:
                g.user = {
                    "username": result['username'], 
                    "role": result['role'],
                    "groups": result.get('groups', [])
                }
                return fn(*args, **kwargs)
            else:
                return jsonify({"error": "invalid token"}), 401
        except Exception as e:
            return jsonify({"error": "token verification failed"}), 401
    return wrapper

def admin_required(fn):
    @wraps(fn)
    @auth_required
    def wrapper(*args, **kwargs):
        if g.user["role"] != "admin":
            return jsonify({"error": "admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper

@auth_bp.post("/signup")
def signup():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    email = data.get("email", "").strip()
    
    if not all([username, password, email]):
        return jsonify({"error": "username, password, email required"}), 400
    
    cognito = get_cognito()
    result = cognito.sign_up(username, password, email)
    
    if result['success']:
        return jsonify({"message": result['message']}), 201
    else:
        return jsonify({"error": result['error']}), 400

@auth_bp.post("/confirm")
def confirm():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    confirmation_code = data.get("confirmation_code", "").strip()
    
    if not all([username, confirmation_code]):
        return jsonify({"error": "username and confirmation_code required"}), 400
    
    cognito = get_cognito()
    result = cognito.confirm_signup(username, confirmation_code)
    
    if result['success']:
        return jsonify({"message": result['message']}), 200
    else:
        return jsonify({"error": result['error']}), 400

@auth_bp.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    if not all([username, password]):
        return jsonify({"error": "username and password required"}), 400
    
    cognito = get_cognito()
    result = cognito.authenticate(username, password)
    
    if result['success']:
        if result.get('challenge_required'):
            return jsonify({
                "challenge_required": True,
                "challenge_name": result['challenge_name'],
                "session": result['session'],
                "username": result['username'],
                "message": result['message']
            }), 200
        else:
            user_info = cognito.verify_token(result['access_token'])
            
            return jsonify({
                "access_token": result['access_token'],
                "token_type": result['token_type'],
                "challenge_required": False,
                "user": {
                    "username": user_info.get('username'),
                    "role": user_info.get('role'),
                    "groups": user_info.get('groups', [])
                }
            }), 200
    else:
        return jsonify({"error": result['error']}), 401

@auth_bp.post("/mfa/challenge")
def handle_mfa_challenge():
    data = request.get_json(force=True, silent=True) or {}
    session = data.get("session", "").strip()
    code = data.get("code", "").strip()
    username = data.get("username", "").strip()
    
    if not all([session, code, username]):
        return jsonify({"error": "session, code, and username required"}), 400
    
    cognito = get_cognito()
    result = cognito.respond_to_auth_challenge(session, code, username)
    
    if result['success']:
        user_info = cognito.verify_token(result['access_token'])
        
        return jsonify({
            "access_token": result['access_token'],
            "token_type": result['token_type'],
            "user": {
                "username": user_info.get('username'),
                "role": user_info.get('role'),
                "groups": user_info.get('groups', [])
            }
        }), 200
    else:
        return jsonify({"error": result['error']}), 401

@auth_bp.get("/profile")
@auth_required
def get_profile():
    return jsonify({
        "username": g.user["username"],
        "role": g.user["role"],
        "groups": g.user["groups"]
    })


@auth_bp.get("/groups")
@admin_required
def list_groups():
    cognito = get_cognito()
    result = cognito.list_groups()
    
    if result['success']:
        return jsonify({"groups": result['groups']})
    else:
        return jsonify({"error": result['error']}), 500

@auth_bp.post("/groups")
@admin_required
def create_group():
    data = request.get_json(force=True, silent=True) or {}
    group_name = data.get("name", "").strip()
    description = data.get("description", "").strip()
    
    if not group_name:
        return jsonify({"error": "group name required"}), 400
    
    cognito = get_cognito()
    result = cognito.create_group(group_name, description)
    
    if result['success']:
        return jsonify({"message": result['message']}), 201
    else:
        return jsonify({"error": result['error']}), 400

@auth_bp.post("/users/<username>/groups")
@admin_required
def add_user_to_group(username):
    data = request.get_json(force=True, silent=True) or {}
    group_name = data.get("group", "").strip()
    
    if not group_name:
        return jsonify({"error": "group name required"}), 400
    
    cognito = get_cognito()
    result = cognito.add_user_to_group(username, group_name)
    
    if result['success']:
        return jsonify({"message": result['message']})
    else:
        return jsonify({"error": result['error']}), 400

@auth_bp.delete("/users/<username>/groups/<group_name>")
@admin_required
def remove_user_from_group(username, group_name):
    cognito = get_cognito()
    result = cognito.remove_user_from_group(username, group_name)
    
    if result['success']:
        return jsonify({"message": result['message']})
    else:
        return jsonify({"error": result['error']}), 400

@auth_bp.get("/users/<username>/groups")
@admin_required
def get_user_groups(username):
    cognito = get_cognito()
    groups = cognito.get_user_groups(username)
    
    return jsonify({
        "username": username,
        "groups": groups
    })

@auth_bp.post("/mfa/enable")
@auth_required
def enable_mfa():
    try:
        # Get fresh token from header
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.split(" ", 1)[1] if auth_header.startswith("Bearer ") else ""
        
        cognito = get_cognito()
        result = cognito.set_user_mfa_preference(token, True)
        
        if result['success']:
            return jsonify({"message": "MFA enabled successfully"}), 200
        else:
            return jsonify({"error": result['error']}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.post("/mfa/disable") 
@auth_required
def disable_mfa():
    try:
        # Get fresh token from header
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.split(" ", 1)[1] if auth_header.startswith("Bearer ") else ""
        
        cognito = get_cognito()
        result = cognito.set_user_mfa_preference(token, False)
        
        if result['success']:
            return jsonify({"message": "MFA disabled successfully"}), 200
        else:
            return jsonify({"error": result['error']}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@auth_bp.post("/oauth/token")
def exchange_oauth_token():
    data = request.get_json(force=True, silent=True) or {}
    code = data.get("code", "").strip()
    redirect_uri = data.get("redirect_uri", "").strip()
    
    if not all([code, redirect_uri]):
        return jsonify({"error": "code and redirect_uri required"}), 400
    
    try:
        # Get client secret from Secrets Manager (secure)
        from .services.secrets_manager_service import get_secret
        client_secret = get_secret('cognito_client_secret')
        
        if not client_secret:
            return jsonify({"error": "client secret not configured"}), 500
        
        # Server-to-server token exchange
        cognito_domain = os.getenv('COGNITO_DOMAIN', 'ap-southeast-2vt6cuuzgl.auth.ap-southeast-2.amazoncognito.com')
        client_id = os.getenv('COGNITO_CLIENT_ID')
        
        token_url = f"https://{cognito_domain}/oauth2/token"
        
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        # Make secure server-to-server request
        response = requests.post(
            token_url,
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10
        )
        
        if not response.ok:
            pass
            return jsonify({"error": "token exchange failed"}), 400
        
        tokens = response.json()
        
        # Get user info from the access token
        cognito = get_cognito()
        user_info = cognito.verify_token(tokens['access_token'])

        # Move Google users to 'user' group
        username = user_info.get('username')
        groups = user_info.get('groups', [])

        # If user is in Google group but not in 'user' group
        google_groups = [g for g in groups if 'Google' in g]
        if google_groups and 'user' not in groups:
            try:
                # Add to user group
                cognito.add_user_to_group(username, 'user')
                # Remove from Google group
                for google_group in google_groups:
                    cognito.remove_user_from_group(username, google_group)
            except Exception:
                pass

        return jsonify({
            "access_token": tokens['access_token'],
            "token_type": tokens.get('token_type', 'Bearer'),
            "user": {
                "username": user_info.get('username'),
                "role": user_info.get('role', 'user'),
                "groups": user_info.get('groups', ['user'])
            }
        }), 200
        
    except Exception as e:
        pass
        return jsonify({"error": "internal server error"}), 500