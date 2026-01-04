from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BlogService:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_blog_posts(self):
        """Get all blog posts from the database that are visible and published"""
        # Get current date in YYYY-MM-DD format for comparison
        today = datetime.now().strftime('%Y-%m-%d')
        
        query = """
            SELECT * FROM blog_posts 
            WHERE is_visible = TRUE AND date <= %s
            ORDER BY date DESC
        """
        posts = self.db_manager.execute_query(query, (today,), fetch=True)
        
        if posts is None:
            logger.error("Failed to fetch blog posts from database.")
            return []
        
        # Post-process posts (e.g., convert tags string to list)
        for post in posts:
            if post.get('tags') and isinstance(post['tags'], str):
                post['tags'] = [t.strip() for t in post['tags'].split(',') if t.strip()]
        
        logger.info(f"Returning {len(posts)} blog posts from database")
        return posts

    def get_blog_post(self, slug):
        """Get a specific blog post by slug from the database if it's visible and published"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        query = """
            SELECT * FROM blog_posts 
            WHERE slug = %s AND is_visible = TRUE AND date <= %s
        """
        posts = self.db_manager.execute_query(query, (slug, today), fetch=True)
        
        if not posts:
            logger.warning(f"Blog post NOT found, invisible, or future-dated: {slug}")
            return None
            
        post = posts[0]
        # Convert tags string to list if it exists
        if post.get('tags'):
            if isinstance(post['tags'], str):
                post['tags'] = [t.strip() for t in post['tags'].split(',') if t.strip()]
                
        return post
