class AnalyticsService:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_analytics_data(self, limit=90):
        """Get analytics data from database"""
        query = """
        SELECT date, visitors, page_views, bounce_rate, avg_session_duration, unique_visitors
        FROM site_analytics 
        ORDER BY date DESC 
        LIMIT %s
        """
        return self.db_manager.execute_query(query, (limit,), fetch=True) or []

    def get_dashboard_data(self, dataset_name):
        """Get dashboard data from database"""
        query = """
        SELECT data_point, category, timestamp
        FROM dashboard_data 
        WHERE dataset_name = %s
        ORDER BY timestamp DESC
        """
        return self.db_manager.execute_query(query, (dataset_name,), fetch=True) or []
