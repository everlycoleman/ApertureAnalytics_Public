
# Set your Cloudinary credentials
# ==============================
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Set paths relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
dotenv_path = PROJECT_ROOT / 'config' / '.env'
load_dotenv(dotenv_path=dotenv_path)

# Import the Cloudinary libraries
# ==============================
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Import to format the JSON responses
# ==============================
import json

# Import metadata extraction
try:
    from Scripts.createmetadatatable import createmetadata
except ImportError:
    try:
        from createmetadatatable import createmetadata
    except ImportError:
        createmetadata = None

# Set configuration parameter: return "https" URLs by setting secure=True
# ==============================
cloudinary.config(
    cloud_name=os.getenv('URL_CLOUDINARY').split('@')[-1],
    api_key=os.getenv('API_KEY_CLOUDINARY'),
    api_secret=os.getenv('API_SECRET_CLOUDINARY'),
    secure=True
)

def upload_photos():
    new_dir = PROJECT_ROOT / 'Photo_Uploads' / 'New'
    done_dir = PROJECT_ROOT / 'Photo_Uploads' / 'Done'
    
    if not done_dir.exists():
        done_dir.mkdir(parents=True)
    
    url_mapping_file = done_dir / 'photo_urls.json'
    url_mapping = {}
    
    # Load existing mapping if file exists
    if url_mapping_file.exists():
        with open(url_mapping_file, 'r') as f:
            try:
                raw_mapping = json.load(f)
                # Convert old string format to new dictionary format for consistency
                for key, value in raw_mapping.items():
                    if isinstance(value, str):
                        url_mapping[key] = {
                            "original": value,
                            "thumbnail": value.replace("/upload/", "/upload/w_300,h_300,c_fill/")
                        }
                    else:
                        url_mapping[key] = value
            except json.JSONDecodeError:
                pass

    # Iterate through files in the New directory
    uploaded_files = []
    for photo_path in new_dir.iterdir():
        if photo_path.is_file() and photo_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.nef', '.dng']:
            print(f"Uploading {photo_path.name}...")
            
            try:
                # Upload each photo.
                response = cloudinary.uploader.upload_large(
                    str(photo_path),
                    public_id=photo_path.stem,
                    folder="Aperture Analytics",
                    unique_filename=False,
                    overwrite=True
                )
                
                # Store key value pairs: filename and cloudinary URLs
                #  store the original URL and a thumbnail URL.
                original_url = response.get('secure_url')
                
                # Construct thumbnail URL using Cloudinary's dynamic transformation
                # Example: width=300, height=300, crop="fill"
                thumbnail_url = original_url.replace("/upload/", "/upload/w_300,h_300,c_fill/")
                
                url_mapping[photo_path.name] = {
                    "original": original_url,
                    "thumbnail": thumbnail_url
                }
                
                #  Once the file is uploaded move from  New folder to  Done Folder.
                dest_path = done_dir / photo_path.name
                shutil.move(str(photo_path), str(dest_path))
                print(f"Moved {photo_path.name} to {done_dir}")
                uploaded_files.append(photo_path.name)

                # Update the mapping file progressively
                with open(url_mapping_file, 'w') as f:
                    json.dump(url_mapping, f, indent=2)

            except Exception as e:
                print(f"Failed to upload {photo_path.name}: {e}")

    # Final save to ensure any migrations are captured even if no new uploads occurred
    with open(url_mapping_file, 'w') as f:
        json.dump(url_mapping, f, indent=2)

    print(f"Process completed. URL mapping saved to {url_mapping_file}")

    # Extract metadata for newly uploaded files
    if uploaded_files and createmetadata:
        print(f"Extracting metadata for {len(uploaded_files)} new files...")
        createmetadata(specific_files=uploaded_files)

if __name__ == "__main__":
    upload_photos()