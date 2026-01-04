from flask import Blueprint, jsonify
import logging

logger = logging.getLogger(__name__)

def create_admin_blueprint(db_manager, environment_info):
    admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

    @admin_bp.route('/seed-data')
    def seed_data():
        """Admin endpoint to seed sample data"""
        try:
            db_manager.insert_sample_data()
            return jsonify({"message": "Sample data seeded successfully"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @admin_bp.route('/database-info')
    def database_info():
        """Admin endpoint to show database information"""
        try:
            info = {}
            tables = ['gallery', 'site_analytics', 'dashboard_data']

            for table in tables:
                count_result = db_manager.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch=True)
                info[f"{table}_count"] = count_result[0]['count'] if count_result else 0

            info['database_name'] = db_manager.db_config['database']
            info['database_host'] = db_manager.db_config['host']
            info['environment'] = environment_info

            # Check blog_posts table
            try:
                blog_count = db_manager.execute_query("SELECT COUNT(*) as count FROM blog_posts", fetch=True)
                info['blog_posts_count'] = blog_count[0]['count'] if blog_count else 0
            except:
                info['blog_posts_count'] = "Error or Table Missing"

            return jsonify(info)
        except Exception as e:
            logger.error(f"Error in database_info: {e}")
            return jsonify({"error": str(e)}), 500

    return admin_bp
