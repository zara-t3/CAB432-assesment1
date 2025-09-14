from functools import wraps
from flask import Blueprint, request, jsonify, g
from .services.cognito_service import get_cognito

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
                g.user = {"username": result['username'], "role": result['role']}
                return fn(*args, **kwargs)
            else:
                return jsonify({"error": "invalid token"}), 401
        except Exception as e:
            return jsonify({"error": "token verification failed"}), 401
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
    """Replaces old hardcoded login"""
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    if not all([username, password]):
        return jsonify({"error": "username and password required"}), 400
    
    cognito = get_cognito()
    result = cognito.authenticate(username, password)
    
    if result['success']:
        return jsonify({
            "access_token": result['access_token'],
            "token_type": result['token_type']
        }), 200
    else:
        return jsonify({"error": result['error']}), 401