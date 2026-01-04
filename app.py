from flask import Flask
import os
import importlib
import logging
from pathlib import Path

# Modular imports
from database import DatabaseManager, get_db_config
from Services.gallery_service import GalleryService
from Services.blog_service import BlogService
from Services.analytics_service import AnalyticsService
from Services.photo_catalog_service import PhotoCatalogService
from Routes.main import create_main_blueprint
from Routes.api import create_api_blueprint
from Routes.admin import create_admin_blueprint

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
server = app

# Folder Configuration-- For statcic assets not gallery
PHOTO_FOLDER = 'static/photos'
UPLOAD_FOLDER = 'static/uploads'

# Database Initialization
db_config = get_db_config()
db_manager = DatabaseManager(db_config)

# Ensure directories exist
os.makedirs(PHOTO_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Initialize Services
gallery_service = GalleryService(db_manager)
blog_service = BlogService(db_manager)
analytics_service = AnalyticsService(db_manager)
photo_catalog_service = PhotoCatalogService(db_manager)

# Initialize Dash apps dynamically
dash_app_info = []

# DASHBOARD CONFIGURATION
DASHBOARD_CONFIG = [
    ('Dashboards.photo_catalog_dashboard', {'photo_catalog_service': photo_catalog_service})
]

def init_dashboards():
    for module_path, extra_args in DASHBOARD_CONFIG:
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, 'init_dashboard'):
                # server (Flask app) is always passed as first argument
                dash_app = module.init_dashboard(server, **extra_args)
                
                # Collect info for the dashboards listing page
                dash_app_info.append({
                    'name': getattr(module, 'DASH_NAME', module_path.split('.')[-1]),
                    'url': dash_app.config.url_base_pathname,
                    'description': getattr(module, 'DASH_DESCRIPTION', "")
                })
                logger.info(f"Initialized dashboard: {module_path}")
        except Exception as e:
            logger.error(f"Failed to load dashboard {module_path}: {e}")

# Initialization of app components
if db_manager.connect():
    db_manager.create_tables()
    
    # Register Blueprints first (except main which needs dash_app_info)
    app.register_blueprint(create_api_blueprint(gallery_service, analytics_service))
    app.register_blueprint(create_admin_blueprint(db_manager, db_config['environment']))
    
    # Initialize Dashboards
    init_dashboards()
    
    # Register Main Blueprint with collected dash_app_info
    app.register_blueprint(create_main_blueprint(gallery_service, blog_service, dash_app_info))
    
    logger.info("✅ Application initialized successfully")
else:
    logger.error("❌ Failed to initialize database connection")

if __name__ == '__main__':
    print("\n🌐 Starting Flask development server...")
    app.run(debug=True, port=5000)

