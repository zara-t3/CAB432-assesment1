# app/main.py
import os
from flask import Flask, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from .auth import auth_bp
from .routers.images import images_bp
from .routers.jobs import jobs_bp

def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static", template_folder="templates")
    app.config["JWT_SECRET"] = os.getenv("JWT_SECRET", "devsecret")
    app.config["DATA_DIR"]   = os.getenv("DATA_DIR", "/data")

    # Dev CORS for browser tools
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # --- API: health
    @app.get("/api/v1/ping")
    def ping():
        return jsonify({"message": "pong"})

    # --- Pages
    @app.get("/")
    def page_root():
        return redirect(url_for("page_login"))

    @app.get("/login")
    def page_login():
        return render_template("login.html", title="Login")

    @app.get("/upload")
    def page_upload():
        return render_template("upload.html", title="Upload")

    @app.get("/images")
    def page_images():
        return render_template("images.html", title="My Images")

    @app.get("/jobs")
    def page_jobs():
        return render_template("jobs.html", title="Jobs")

    # --- Register blueprints (NOTE the prefixes)
    app.register_blueprint(auth_bp,   url_prefix="/api/v1/auth")
    app.register_blueprint(images_bp, url_prefix="/api/v1/images")
    app.register_blueprint(jobs_bp,   url_prefix="/api/v1/jobs")

    # Debug: print routes so we can verify /api/v1/auth/login exists
    print("== URL MAP ==")
    for rule in app.url_map.iter_rules():
        print(f"{','.join(rule.methods)}  {rule.rule}")

    return app

def run():
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT","8080")))

if __name__ == "__main__":
    run()
