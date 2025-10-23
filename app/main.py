import os
from flask import Flask, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from .auth import auth_bp
from .routers.images import images_bp
from .routers.jobs import jobs_bp
from .services.secrets_manager_service import get_secret 
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static", template_folder="templates")
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.jinja_env.auto_reload = True
    
    try:
        from .services.parameter_store_service import get_app_config
        
        config = get_app_config()
    
        app.config.update({
            'APP_URL': config['app_url'],
            'S3_BUCKET_NAME': config['s3_bucket_name'],
            'DYNAMODB_IMAGES_TABLE': config['dynamodb_images_table'],
            'DYNAMODB_JOBS_TABLE': config['dynamodb_jobs_table'],
            'CLOUDFRONT_DOMAIN': config['cloudfront_domain']
        })
        
        parameter_store_enabled = True
        
    except Exception as e:
        raise Exception(f"Failed to load configuration from Parameter Store. Ensure Parameter Store is properly configured: {e}")

    jwt_secret = get_secret('jwt_secret')
    app.config["JWT_SECRET"] = jwt_secret

    app.config["DATA_DIR"] = "/data"
    app.config['PARAMETER_STORE_ENABLED'] = parameter_store_enabled


    cognito_secret = get_secret('cognito_client_secret')
    app.config['SECRETS_MANAGER_ENABLED'] = bool(cognito_secret)

    CORS(app, resources={r"/api/*": {"origins": "*"}})


    @app.get("/api/v1/ping")
    def ping():
        return jsonify({"message": "pong"})

  
    @app.route("/api/v1/config")
    def get_config():
        return {
            "app_url": app.config.get('APP_URL'),
            "s3_bucket": app.config.get('S3_BUCKET_NAME'),
            "parameter_store": "enabled" if app.config.get('PARAMETER_STORE_ENABLED') else "disabled",
            "secrets_manager": "enabled" if app.config.get('SECRETS_MANAGER_ENABLED') else "disabled"
        }
 
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
    
    @app.get("/profile")
    def page_profile():
        return render_template("profile.html", title="Profile")

    @app.get("/direct-upload")
    def page_direct_upload():
        return render_template("presigned_upload.html", title="Direct Upload")

    @app.get("/presigned-test")
    def page_presigned_test():
        return render_template("presigned_upload.html", title="Direct S3 Upload Test")
    @app.get("/test-mfa")
    def page_test_mfa():
        return render_template("test_mfa.html", title="MFA Test")


    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(images_bp, url_prefix="/api/v1/images")
    app.register_blueprint(jobs_bp, url_prefix="/api/v1/jobs")

    for rule in app.url_map.iter_rules():
        pass

    return app

def run():
    app = create_app()
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    run()