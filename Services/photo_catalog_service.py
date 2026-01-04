class PhotoCatalogService:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_catalog_data(self):
        """Fetch all data from the catalogdata table (kept for backward compatibility if needed)"""
        query = 'SELECT * FROM catalogdata WHERE extension != \'.nef\' AND "CameraModel" ILIKE \'Nikon%%\''
        results = self.db_manager.execute_query(query, fetch=True)
        return results if results else []

    def get_catalog_summary_stats(self):
        """Fetch aggregated summary statistics"""
        query = """
        SELECT 
            COUNT(*) as total_photos,
            SUM(CASE 
                WHEN shutter LIKE '%%/%%' THEN 
                    CAST(SPLIT_PART(shutter, '/', 1) AS FLOAT) / NULLIF(CAST(SPLIT_PART(shutter, '/', 2) AS FLOAT), 0)
                ELSE CAST(NULLIF(shutter, '') AS FLOAT)
            END) as total_exposure_time,
            SUM("FileSize") / 1000000000.0 as total_size_gb
        FROM catalogdata 
        WHERE extension != '.nef' AND "CameraModel" ILIKE 'Nikon%%'
        """
        results = self.db_manager.execute_query(query, fetch=True)
        return results[0] if results else {'total_photos': 0, 'total_exposure_time': 0, 'total_size_gb': 0}

    def get_camera_distribution(self):
        """Fetch camera model distribution for pie chart"""
        query = """
        SELECT "CameraModel", COUNT(*) as count
        FROM catalogdata 
        WHERE extension != '.nef' AND "CameraModel" ILIKE 'Nikon%%'
        GROUP BY "CameraModel"
        """
        return self.db_manager.execute_query(query, fetch=True) or []

    def get_lens_usage(self):
        """Fetch lens usage by camera model"""
        query = """
        WITH filtered_data AS (
            SELECT "LensModel", "CameraModel"
            FROM catalogdata
            WHERE extension != '.nef' 
              AND "CameraModel" ILIKE 'Nikon%%'
              AND "LensModel" IS NOT NULL 
              AND "LensModel" != ''
        ),
        lens_counts AS (
            SELECT "LensModel", COUNT(*) as total_count
            FROM filtered_data
            GROUP BY "LensModel"
            HAVING COUNT(*) > 10
        )
        SELECT f."LensModel", f."CameraModel", COUNT(*) as "Count", lc.total_count
        FROM filtered_data f
        JOIN lens_counts lc ON f."LensModel" = lc."LensModel"
        GROUP BY f."LensModel", f."CameraModel", lc.total_count
        ORDER BY lc.total_count ASC
        """
        return self.db_manager.execute_query(query, fetch=True) or []

    def get_heatmap_data(self):
        """Fetch daily photo counts for the heatmap"""
        query = """
        SELECT 
            TO_CHAR(TO_DATE("CreationDate", 'MM/DD/YYYY'), 'YYYY-MM-DD') as date,
            COUNT(*) as count
        FROM catalogdata
        WHERE extension != '.nef' 
          AND "CameraModel" ILIKE 'Nikon%%'
          AND "CreationDate" IS NOT NULL
          AND "CreationDate" != ''
          AND TO_DATE("CreationDate", 'MM/DD/YYYY') > (CURRENT_DATE - INTERVAL '4 years')
        GROUP BY date
        ORDER BY date
        """
        return self.db_manager.execute_query(query, fetch=True) or []

    def get_interactive_plot_data(self):
        """Fetch minimal data needed for interactive focal length, ISO, and shutter plots"""
        query = """
        SELECT "CameraModel", "FocalLength", "ISO", "shutter"
        FROM catalogdata
        WHERE extension != '.nef' AND "CameraModel" ILIKE 'Nikon%%'
        """
        return self.db_manager.execute_query(query, fetch=True) or []
