import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
import frontmatter
import markdown
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set paths relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
dotenv_path = PROJECT_ROOT / 'config' / '.env'
load_dotenv(dotenv_path=dotenv_path)

def get_db_connection():
    db_url = os.getenv('DB_External_URL') or os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("No database URL found in environment variables.")
        return None
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def create_blog_table(conn):
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS blog_posts (
                slug TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                date TEXT,
                author TEXT,
                tags TEXT,
                image TEXT,
                content TEXT,
                content_html TEXT,
                is_visible BOOLEAN DEFAULT TRUE,
                file_last_modified TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # Also ensure is_visible column exists for existing tables
        cur.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='blog_posts' AND column_name='is_visible') THEN
                    ALTER TABLE blog_posts ADD COLUMN is_visible BOOLEAN DEFAULT TRUE;
                END IF;
            END $$;
        """)
        conn.commit()
        
        cur.close()
        logger.info("blog_posts table verified/created.")
    except Exception as e:
        logger.error(f"Error creating blog_posts table: {e}")
        conn.rollback()

def clean_nul(val):
    """Remove NUL characters from strings, which PostgreSQL does not support."""
    if isinstance(val, str):
        return val.replace('\x00', '')
    return val

def sync_posts(refresh=False):
    conn = get_db_connection()
    if not conn:
        return

    create_blog_table(conn)

    # Find posts directory
    posts_dir = PROJECT_ROOT / 'posts'
    if not posts_dir.exists():
        posts_dir = PROJECT_ROOT / 'Posts'
    
    if not posts_dir.exists():
        logger.error("Posts directory not found.")
        conn.close()
        return

    # Get existing posts metadata from DB
    db_posts = {}
    if not refresh:
        cur = conn.cursor()
        cur.execute("SELECT slug, file_last_modified FROM blog_posts")
        db_posts = {row[0]: row[1] for row in cur.fetchall()}
        cur.close()
    else:
        logger.info("Full refresh requested. Ignoring existing database records for blog posts.")

    md_files = list(posts_dir.glob('*.md'))
    logger.info(f"Found {len(md_files)} markdown files.")

    cur = conn.cursor()
    for md_file in md_files:
        slug = md_file.stem
        file_mtime = datetime.fromtimestamp(md_file.stat().st_mtime)

        # Check if we need to update
        if not refresh and slug in db_posts:
            db_mtime = db_posts[slug]
            # Handle potential None or slight precision differences
            if db_mtime and file_mtime <= db_mtime:
                logger.info(f"Skipping {slug}, no changes detected.")
                continue

        logger.info(f"Processing {slug}...")
        try:
            post = frontmatter.load(md_file)
            metadata = post.metadata
            content = post.content
            content_html = markdown.markdown(content, extensions=['fenced_code', 'tables'])

            # Prepare data for insertion
            title = clean_nul(metadata.get('title'))
            description = clean_nul(metadata.get('description'))
            date = metadata.get('date')
            author = clean_nul(metadata.get('author'))
            tags = metadata.get('tags')
            if isinstance(tags, list):
                tags = ", ".join(tags)
            tags = clean_nul(tags)
            image = clean_nul(metadata.get('image'))
            is_visible = metadata.get('IsVisible', True)
            # Handle string 'false' from frontmatter if it's not already a boolean
            if isinstance(is_visible, str):
                is_visible = is_visible.lower() != 'false'

            cur.execute("""
                INSERT INTO blog_posts (
                    slug, title, description, date, author, tags, image, content, content_html, is_visible, file_last_modified, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (slug) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    date = EXCLUDED.date,
                    author = EXCLUDED.author,
                    tags = EXCLUDED.tags,
                    image = EXCLUDED.image,
                    content = EXCLUDED.content,
                    content_html = EXCLUDED.content_html,
                    is_visible = EXCLUDED.is_visible,
                    file_last_modified = EXCLUDED.file_last_modified,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                slug, title, description, str(date) if date else None, author, tags, image, 
                clean_nul(content), clean_nul(content_html), is_visible, file_mtime
            ))
            logger.info(f"Successfully synced {slug}.")
        except Exception as e:
            logger.error(f"Error processing {md_file}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Sync completed.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync blog posts from markdown files to the database.")
    parser.add_argument("-r", "--refresh", action="store_true", help="Perform a full refresh, re-processing all blog posts")
    args = parser.parse_args()
    
    sync_posts(refresh=args.refresh)
