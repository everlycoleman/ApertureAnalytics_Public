from datetime import datetime

class GalleryService:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def get_photo_categories(self):
        """Get dynamic photo categories from gallery table"""
        query = 'SELECT DISTINCT "Genre" FROM gallery'
        genres = self.db_manager.execute_query(query, fetch=True)
        
        categories = {}
        if genres:
            for row in genres:
                genre = row['Genre']
                if not genre or genre.strip() == "":
                    key = "Miscellaneous"
                    name = "Miscellaneous"
                else:
                    key = genre
                    name = genre
                categories[key] = name
        
        if not categories:
            categories["Miscellaneous"] = "Miscellaneous"
            
        return categories

    def get_locations(self):
        query = "SELECT DISTINCT \"City\", \"ProvinceState\" FROM gallery WHERE \"City\" IS NOT NULL OR \"ProvinceState\" IS NOT NULL"
        results = self.db_manager.execute_query(query, fetch=True)
        locations = []
        if results:
            for row in results:
                city = row.get("City")
                state = row.get("ProvinceState")
                if city and state: locations.append(f"{city}, {state}")
                elif city: locations.append(city)
                elif state: locations.append(state)
        return sorted(list(set(locations)))

    def get_photos(self, category=None, search=None, location=None, collection=None, limit=None, offset=None):
        """Get photos from database with advanced filtering and pagination"""
        query = 'SELECT * FROM gallery'
        where_clauses = []
        params = []

        if category and category != 'all':
            if category == "Miscellaneous":
                where_clauses.append('("Genre" IS NULL OR "Genre" = \'\' OR "Genre" = \' \')')
            else:
                where_clauses.append('"Genre" = %s')
                params.append(category)

        if search:
            search_term = f'%{search}%'
            where_clauses.append('("filename" ILIKE %s OR "ImageDescription" ILIKE %s OR "Genre" ILIKE %s OR "keywords" ILIKE %s)')
            params.extend([search_term, search_term, search_term, search_term])

        if location:
            if ',' in location:
                parts = [p.strip() for p in location.split(',')]
                for part in parts:
                    loc_term = f'%{part}%'
                    where_clauses.append('("City" ILIKE %s OR "ProvinceState" ILIKE %s OR "SubLocation" ILIKE %s)')
                    params.extend([loc_term, loc_term, loc_term])
            else:
                loc_term = f'%{location}%'
                where_clauses.append('("City" ILIKE %s OR "ProvinceState" ILIKE %s OR "SubLocation" ILIKE %s)')
                params.extend([loc_term, loc_term, loc_term])

        if where_clauses:
            query += ' WHERE ' + ' AND '.join(where_clauses)

        if collection == 'most-viewed':
            query += ' ORDER BY view_count DESC, TO_TIMESTAMP("CreationDate", \'MM/DD/YYYY\') DESC'
        elif collection == 'random':
            query += ' ORDER BY RANDOM()'
        else:
            query += ' ORDER BY TO_TIMESTAMP("CreationDate", \'MM/DD/YYYY\') DESC'

        if limit:
            query += ' LIMIT %s'
            params.append(limit)
        if offset:
            query += ' OFFSET %s'
            params.append(offset)

        photos = self.db_manager.execute_query(query, tuple(params), fetch=True)
        
        if photos:
            for photo in photos:
                if not photo.get('Genre') or photo['Genre'].strip() == "":
                    photo['Genre'] = "Miscellaneous"
                    
        return photos or []

    def increment_photo_view(self, filename):
        """Increment view count for a photo"""
        query = 'UPDATE gallery SET view_count = view_count + 1 WHERE filename = %s'
        return self.db_manager.execute_query(query, (filename,))
