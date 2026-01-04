from flask import Blueprint, request, jsonify

def create_api_blueprint(gallery_service, analytics_service):
    api_bp = Blueprint('api', __name__, url_prefix='/api')

    @api_bp.route('/photos')
    def api_photos():
        category = request.args.get('category')
        search = request.args.get('search')
        location = request.args.get('location')
        collection = request.args.get('collection')
        limit = request.args.get('limit', 12, type=int)
        offset = request.args.get('offset', 0, type=int)
        photos = gallery_service.get_photos(category=category, search=search, location=location, 
                                          collection=collection, limit=limit, offset=offset)
        return jsonify(photos)

    @api_bp.route('/analytics')
    def api_analytics():
        """API endpoint to get analytics data"""
        days = request.args.get('days', 30, type=int)
        analytics = analytics_service.get_analytics_data(limit=days)
        return jsonify(analytics or [])

    @api_bp.route('/photos/upload', methods=['POST'])
    def upload_photo():
        """API endpoint to upload new photos"""
        return jsonify({"message": "Upload endpoint - implement based on your needs"})

    return api_bp
