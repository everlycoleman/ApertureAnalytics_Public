import os
import json
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Set paths relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
dotenv_path = PROJECT_ROOT / 'config' / '.env'
load_dotenv(dotenv_path=dotenv_path)

# Cloudinary configuration
cloudinary.config(
    cloud_name=os.getenv('URL_CLOUDINARY').split('@')[-1],
    api_key=os.getenv('API_KEY_CLOUDINARY'),
    api_secret=os.getenv('API_SECRET_CLOUDINARY'),
    secure=True
)

def cleanup_photos():
    done_dir = PROJECT_ROOT / 'Photo_Uploads' / 'Done'
    url_mapping_file = done_dir / 'photo_urls.json'
    
    if not url_mapping_file.exists():
        print(f"Error: {url_mapping_file} not found. Nothing to cleanup.")
        return

    with open(url_mapping_file, 'r') as f:
        url_mapping = json.load(f)

    # 1. Identify files missing in the Done folder
    filenames_in_mapping = list(url_mapping.keys())
    files_to_remove = []
    
    for filename in filenames_in_mapping:
        file_path = done_dir / filename
        if not file_path.exists():
            files_to_remove.append(filename)

    if not files_to_remove:
        print("No missing files found. Cleanup not needed.")
        return

    print(f"Found {len(files_to_remove)} files missing locally: {files_to_remove}")

    # Database connection
    db_url = os.getenv('DB_External_URL')
    conn = None
    if db_url:
        try:
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
        except Exception as e:
            print(f"Error connecting to database: {e}")
            conn = None

    for filename in files_to_remove:
        print(f"Cleaning up {filename}...")
        
        # 2. Remove from Cloudinary
        # The public_id used in PhotoUpload.py is photo_path.stem and it's in the "Aperture Analytics" folder
        public_id = f"Aperture Analytics/{Path(filename).stem}"
        try:
            result = cloudinary.uploader.destroy(public_id)
            print(f"Cloudinary removal result for {public_id}: {result}")
        except Exception as e:
            print(f"Error removing {public_id} from Cloudinary: {e}")

        # 3. Remove from Database
        if conn:
            try:
                # Use both stem and full filename to ensure it's removed regardless of extension being stored
                cur.execute("DELETE FROM gallery WHERE filename = %s OR filename = %s", (Path(filename).stem, filename))
                print(f"Removed {filename} (and its extension-less version) from database.")
            except Exception as e:
                print(f"Error removing {filename} from database: {e}")

        # 4. Remove from url_mapping
        del url_mapping[filename]

    # Commit database changes
    if conn:
        conn.commit()
        cur.close()
        conn.close()

    # 5. Update photo_urls.json
    with open(url_mapping_file, 'w') as f:
        json.dump(url_mapping, f, indent=2)
    print(f"Updated {url_mapping_file}")

if __name__ == "__main__":
    cleanup_photos()
