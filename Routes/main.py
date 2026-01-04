from flask import Blueprint, render_template, request, send_from_directory, current_app
import os

def create_main_blueprint(gallery_service, blog_service, dash_app_info):
    main_bp = Blueprint('main', __name__)

    @main_bp.route('/')
    def index():
        return render_template('index.html')

    @main_bp.route('/photography')
    def photography():
        category = request.args.get('category', 'all')
        search = request.args.get('search')
        location = request.args.get('location')
        collection = request.args.get('collection')

        photos = gallery_service.get_photos(category=category if category != 'all' else None,
                                           search=search,
                                           location=location,
                                           collection=collection,
                                           limit=12)

        return render_template('photography.html',
                               photos=photos,
                               categories=gallery_service.get_photo_categories(),
                               locations=gallery_service.get_locations(),
                               current_category=category,
                               current_search=search,
                               current_location=location,
                               current_collection=collection)

    @main_bp.route('/photography/<photo_id>')
    def photo_detail(photo_id):
        # Find photo by filename
        query = 'SELECT * FROM gallery WHERE filename = %s'
        params = (photo_id,)

        photo = gallery_service.db_manager.execute_query(query, params, fetch=True)

        if not photo:
            return "Photo not found", 404

        photo = photo[0]
        # Post-process for display
        if not photo.get('Genre') or photo['Genre'].strip() == "":
            photo['Genre'] = "Miscellaneous"
            
        gallery_service.increment_photo_view(photo['filename'])

        return render_template('photo_detail.html', photo=photo)

    @main_bp.route('/dashboards')
    def dashboards():
        return render_template('dashboards.html', dash_apps=dash_app_info)

    @main_bp.route('/articles')
    def blog():
        """Blog index page"""
        posts = blog_service.get_blog_posts()
        return render_template('blog.html', posts=posts)

    @main_bp.route('/blog/<slug>')
    def blog_post(slug):
        """Individual blog post page"""
        post = blog_service.get_blog_post(slug)
        if not post:
            return "Post not found", 404
        return render_template('post.html', post=post)

    @main_bp.route('/static/photos/<filename>')
    def serve_photo(filename):
        """Serve photos from the photos directory"""
        return send_from_directory('static/photos', filename)

    return main_bp
