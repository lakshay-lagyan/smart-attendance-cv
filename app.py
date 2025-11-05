import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_jwt_extended import JWTManager
from flask_compress import Compress

load_dotenv()

from config import config
from models import db, SuperAdmin, Admin
from face_service import face_service

app = Flask(__name__, static_folder='static', template_folder='templates')

env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])

db.init_app(app)
jwt = JWTManager(app)
compress = Compress(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['FACE_DATA_FOLDER'], exist_ok=True)

def init_database():
    """Initialize database with default users"""
    with app.app_context():
        db.create_all()
        
        if SuperAdmin.query.count() == 0:
            superadmin = SuperAdmin(
                name="Super Admin",
                email="superadmin@admin.com"
            )
            superadmin.set_password("superadmin123")
            db.session.add(superadmin)
            logger.info("Created default super admin")
        
        if Admin.query.count() == 0:
            admin = Admin(
                name="Admin",
                email="admin@admin.com",
                department="IT"
            )
            admin.set_password("admin123")
            db.session.add(admin)
            logger.info("Created default admin")
        
        db.session.commit()
        logger.info("Database initialized")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/superadmin/dashboard')
def superadmin_dashboard():
    return render_template('superadmin/dashboard.html')

@app.route('/superadmin/admins')
def superadmin_admins():
    return render_template('superadmin/admins.html')

@app.route('/superadmin/users')
def superadmin_users():
    return render_template('superadmin/users.html')

@app.route('/superadmin/logs')
def superadmin_logs():
    return render_template('superadmin/logs.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('admin/dashboard.html')

@app.route('/admin/enrollment')
def admin_enrollment():
    return render_template('admin/enrollment.html')

@app.route('/admin/requests')
def admin_requests():
    return render_template('admin/requests.html')

@app.route('/user/dashboard')
def user_dashboard():
    return render_template('user/dashboard.html')

from routes.auth import auth_bp
from routes.admin_api import admin_api_bp
from routes.superadmin_api import superadmin_api_bp
from routes.user_api import user_api_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(admin_api_bp, url_prefix='/api/admin')
app.register_blueprint(superadmin_api_bp, url_prefix='/api/superadmin')
app.register_blueprint(user_api_bp, url_prefix='/api/user')

# Initialize database on startup (works with gunicorn too)
with app.app_context():
    try:
        db.create_all()
        
        # Create default super admin if not exists
        if SuperAdmin.query.count() == 0:
            superadmin = SuperAdmin(
                name="Super Admin",
                email="superadmin@admin.com"
            )
            superadmin.set_password("superadmin123")
            db.session.add(superadmin)
            logger.info("Created default super admin")
        
        # Create default admin if not exists
        if Admin.query.count() == 0:
            admin = Admin(
                name="Admin",
                email="admin@admin.com",
                department="IT"
            )
            admin.set_password("admin123")
            db.session.add(admin)
            logger.info("Created default admin")
        
        db.session.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        # Don't crash on init errors, let the app start

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=(env == 'development'))
