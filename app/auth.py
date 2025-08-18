import os, time, jwt
from functools import wraps
from flask import Blueprint, current_app, request, jsonify, g

auth_bp = Blueprint("auth", __name__)

USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "zara":  {"password": "zara123",  "role": "user"},
}

def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing bearer token"}), 401
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
        except Exception:
            return jsonify({"error": "invalid token"}), 401
        g.user = {"username": payload["sub"], "role": payload["role"]}
        return fn(*args, **kwargs)
    return wrapper

@auth_bp.post("/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    u = USERS.get(data.get("username"))
    if not u or u["password"] != data.get("password"):
        return jsonify({"error": "invalid credentials"}), 401
    token = jwt.encode(
        {"sub": data["username"], "role": u["role"], "exp": int(time.time()) + 86400},
        current_app.config["JWT_SECRET"], algorithm="HS256"
    )
    return jsonify({"access_token": token, "token_type": "bearer"})
