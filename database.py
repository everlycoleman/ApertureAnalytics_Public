import os
import logging
import tomllib
import urllib.parse as urlparse
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from datetime import datetime, timedelta
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_config():
    # Load environment variables from .env
    load_dotenv(dotenv_path="config/.env")
    
    # set Environment
    environment = os.getenv('Environment', 'local')

    # Support various DB URL environment variable names commonly used in deployment
    db_url = os.getenv('DATABASE_URL') or os.getenv('DB_External_URL') or os.getenv('db_connection')

    if db_url:
        url = urlparse.urlparse(db_url)
        database = url.path[1:]
        user = url.username
        password = url.password
        host = url.hostname
        port = url.port
        logger.info(f"Using database connection from URL: {host}/{database}")

    elif environment == "local":
        # Fall back to config.toml for local dev if no URL is provided
        try:
            with open("config/config.toml", "rb") as f:
                config = tomllib.load(f)
            host = config["local"]["host"]
            database = config["local"]["database"]
            user = config["local"]["user"]
            password = config["local"]["password"]
            port = config["local"]["port"]
            logger.info(f"Using local database config from config.toml: {host}/{database}")
        except Exception as e:
            logger.error(f"Failed to load local config: {e}")
            host = database = user = password = port = None
    else:
        database = os.environ.get('Database')
        user = os.environ.get('User')
        password = os.environ.get('Password')
        host = os.environ.get('Host')
        port = os.environ.get('Port')
        logger.info("Using individual environment variables for database config")

    return {
        'host': host,
        'database': database,
        'user': user,
        'password': password,
        'port': port,
        'environment': environment
    }

class DatabaseManager:
    def __init__(self, db_config):
        self.db_config = db_config
        self.connection_pool = None

    def connect(self):
        """Create database connection pool"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                host=self.db_config['host'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                port=self.db_config['port']
            )
            logger.info(f"Successfully connected to PostgreSQL database: {self.db_config['database']}")
            return True
        except psycopg2.Error as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
            return False

    def get_connection(self):
        """Get a connection from the pool"""
        if self.connection_pool:
            return self.connection_pool.getconn()
        return None

    def return_connection(self, conn):
        """Return a connection to the pool"""
        if self.connection_pool:
            self.connection_pool.putconn(conn)

    def disconnect(self):
        """Close all database connections"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("PostgreSQL connection pool closed")

    def execute_query(self, query, params=None, fetch=False):
        """Execute a database query"""
        conn = None
        try:
            conn = self.get_connection()
            if not conn:
                logger.error("Could not get database connection")
                return None if fetch else False

            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params or ())

            if fetch:
                result = [dict(row) for row in cursor.fetchall()]
                cursor.close()
                self.return_connection(conn)
                return result
            else:
                conn.commit()
                cursor.close()
                self.return_connection(conn)
                return True

        except psycopg2.Error as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
                self.return_connection(conn)
            return None if fetch else False

    def create_tables(self):
        """Create necessary tables if they don't exist"""

        # Gallery table (consolidated)
        gallery_table = """
        CREATE TABLE IF NOT EXISTS gallery (
            filename TEXT PRIMARY KEY,
            title TEXT,
            original_url TEXT,
            thumbnail_url TEXT,
            "CameraModel" TEXT,
            "LensModel" TEXT,
            "FocalLength" TEXT,
            shutter TEXT,
            "Aperture" TEXT,
            "ISO" TEXT,
            "CreationDate" TEXT,
            "Genre" TEXT,
            "ImageDescription" TEXT,
            "City" TEXT,
            "SubLocation" TEXT,
            "ProvinceState" TEXT,
            "Latitude" DOUBLE PRECISION,
            "Longitude" DOUBLE PRECISION,
            "Altitude" DOUBLE PRECISION,
            "keywords" TEXT,
            "extension" TEXT,
            view_count INTEGER DEFAULT 0
        )
        """

        # Analytics data table
        analytics_table = """
        CREATE TABLE IF NOT EXISTS site_analytics (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL UNIQUE,
            visitors INTEGER DEFAULT 0,
            page_views INTEGER DEFAULT 0,
            bounce_rate REAL DEFAULT 0,
            avg_session_duration INTEGER DEFAULT 0,
            unique_visitors INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # Dashboard data table (flexible for different datasets)
        dashboard_data_table = """
        CREATE TABLE IF NOT EXISTS dashboard_data (
            id SERIAL PRIMARY KEY,
            dataset_name VARCHAR(100) NOT NULL,
            data_point JSONB NOT NULL,
            category VARCHAR(100),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # Blog posts table
        blog_posts_table = """
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
        """

        # Photo Catalog table
        catalogdata_table = """
        CREATE TABLE IF NOT EXISTS catalogdata (
            filepath TEXT PRIMARY KEY,
            filename TEXT,
            "CameraModel" TEXT,
            "LensModel" TEXT,
            "FocalLength" TEXT,
            shutter TEXT,
            "Aperture" TEXT,
            "ISO" TEXT,
            "CreationDate" TEXT,
            "Genre" TEXT,
            keywords TEXT,
            "ImageDescription" TEXT,
            "City" TEXT,
            "SubLocation" TEXT,
            "ProvinceState" TEXT,
            "Software" TEXT,
            "SerialNumber" TEXT,
            "ExposureBias" TEXT,
            "MeteringMode" TEXT,
            "Flash" TEXT,
            "WhiteBalance" TEXT,
            "FocalLength35mm" TEXT,
            "ExposureProgram" TEXT,
            "SubjectDistance" TEXT,
            "Latitude" DOUBLE PRECISION,
            "Longitude" DOUBLE PRECISION,
            "Altitude" DOUBLE PRECISION,
            "Width" INTEGER,
            "Height" INTEGER,
            "FileSize" BIGINT,
            "Rating" TEXT,
            "Artist" TEXT,
            "Copyright" TEXT,
            "extension" TEXT,
            last_modified DOUBLE PRECISION
        )
        """

        # Create indexes for better performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_gallery_genre ON gallery(\"Genre\")",
            "CREATE INDEX IF NOT EXISTS idx_analytics_date ON site_analytics(date)",
            "CREATE INDEX IF NOT EXISTS idx_dashboard_dataset ON dashboard_data(dataset_name)",
            "CREATE INDEX IF NOT EXISTS idx_dashboard_category ON dashboard_data(category)",
            "CREATE INDEX IF NOT EXISTS idx_blog_posts_date ON blog_posts(date)",
            "CREATE INDEX IF NOT EXISTS idx_blog_posts_visibility ON blog_posts(is_visible)",
            "CREATE INDEX IF NOT EXISTS idx_catalog_cameramodel ON catalogdata(\"CameraModel\")"
        ]

        tables = [gallery_table, analytics_table, dashboard_data_table, blog_posts_table, catalogdata_table]

        for table_query in tables:
            if self.execute_query(table_query):
                logger.info("Table created/verified successfully")
            else:
                logger.error("Failed to create table")

        # Create indexes
        for index_query in indexes:
            self.execute_query(index_query)

        # Insert sample data if tables are empty
        self.insert_sample_data()

    def insert_sample_data(self):
        """Insert sample data if tables are empty"""

        # Check if analytics table is empty and populate with sample data
        analytics_count = self.execute_query("SELECT COUNT(*) as count FROM site_analytics", fetch=True)
        if analytics_count and analytics_count[0]['count'] == 0:
            # Generate 30 days of sample analytics data
            start_date = datetime.now() - timedelta(days=30)
            for i in range(30):
                current_date = start_date + timedelta(days=i)
                visitors = np.random.poisson(100) + 50
                page_views = visitors * np.random.randint(2, 8)
                bounce_rate = np.random.beta(2, 5)
                session_duration = np.random.randint(60, 300)  # seconds

                query = """
                INSERT INTO site_analytics 
                (date, visitors, page_views, bounce_rate, avg_session_duration, unique_visitors)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (date) DO NOTHING
                """
                params = (
                    current_date.date().isoformat(),
                    int(visitors),
                    int(page_views),
                    float(bounce_rate),
                    int(session_duration),
                    int(visitors * 0.8)  # unique visitors ~80% of total
                )
                self.execute_query(query, params)
