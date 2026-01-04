import math
import os
import json
import argparse
import pandas as pd
from sqlalchemy import create_engine, text
from PIL import Image, IptcImagePlugin
from PIL.ExifTags import TAGS
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import sys

# Set paths relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
dotenv_path = PROJECT_ROOT / 'config' / '.env'
load_dotenv(dotenv_path=dotenv_path)

# Try to import XMP extraction if available
sys.path.append(str(PROJECT_ROOT))

try:
    from Scripts.metadata_extract_xmp import process_image_xmp
except ImportError:
    try:
        from metadata_extract_xmp import process_image_xmp
    except ImportError:
        process_image_xmp = None

def decimal_to_fraction(decimal_number):
    """Convert a decimal number or fraction string to a standard shutter speed string."""
    if decimal_number is None or decimal_number == "":
        return "N/A"
    
    # If it's already a fraction string, try to evaluate it
    if isinstance(decimal_number, str) and "/" in decimal_number:
        try:
            parts = decimal_number.split("/")
            if len(parts) == 2:
                num = float(parts[0])
                den = float(parts[1])
                if den != 0:
                    decimal_number = num / den
                else:
                    return decimal_number
        except (ValueError, TypeError):
            return decimal_number

    try:
        decimal_number = float(decimal_number)
    except (ValueError, TypeError):
        return str(decimal_number)

    if decimal_number <= 0:
        return str(decimal_number)

    # Standard shutter speeds
    standard_speeds = [
        1/8000, 1/6400, 1/5000, 1/4000, 1/3200, 1/2500, 1/2000, 1/1600, 1/1250, 1/1000,
        1/800, 1/640, 1/500, 1/400, 1/320, 1/250, 1/200, 1/160, 1/125, 1/100,
        1/80, 1/60, 1/50, 1/40, 1/30, 1/25, 1/20, 1/15, 1/13, 1/10,
        1/8, 1/6, 1/5, 1/4, 1/3, 0.4, 0.5, 0.6, 0.8, 1,
        1.3, 1.6, 2, 2.5, 3.2, 4, 5, 6, 8, 10,
        13, 15, 20, 25, 30
    ]

    # Find the closest standard speed
    closest_speed = min(standard_speeds, key=lambda x: abs(x - decimal_number))

    # If the difference is small (less than 10% for shutter speeds), use the standard speed
    if abs(closest_speed - decimal_number) / decimal_number < 0.1:
        if closest_speed < 1:
            denominator = round(1 / closest_speed)
            return f"1/{denominator}"
        else:
            if closest_speed == int(closest_speed):
                return str(int(closest_speed))
            return str(closest_speed)

    # Fallback to simplified fraction if not close to any standard speed
    if decimal_number >= 1:
        if decimal_number == int(decimal_number):
            return f"{int(decimal_number)}"
        return f"{decimal_number:.1f}"

    precision = 1000000
    numerator = int(decimal_number * precision)
    denominator = precision
    gcd = math.gcd(numerator, denominator)
    return f"{numerator // gcd}/{denominator // gcd}"

def extract_exif_from_image(image_path):
    """Extract EXIF metadata from an image file including GPS and technical fields."""
    exif_data = {}
    try:
        with Image.open(image_path) as img:
            # Get basic image info
            exif_data['Width'], exif_data['Height'] = img.size
            
            # Use getexif() which is modern and works for both JPEG and TIFF (DNG/NEF)
            exif = img.getexif()
            if exif:
                # 1. Main IFD tags
                for tag_id, data in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if isinstance(data, bytes):
                        try:
                            data = data.decode('utf-8').strip('\x00')
                        except UnicodeDecodeError:
                            data = data.decode('latin-1').strip('\x00')
                    exif_data[tag] = data
                
                # 2. Exif IFD (Technical metadata: Exposure, ISO, Focal Length, etc.)
                # 0x8769 is the tag for ExifOffset which points to the Exif IFD
                try:
                    exif_ifd = exif.get_ifd(0x8769)
                    if exif_ifd:
                        for tag_id, data in exif_ifd.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if isinstance(data, bytes):
                                try:
                                    data = data.decode('utf-8').strip('\x00')
                                except UnicodeDecodeError:
                                    data = data.decode('latin-1').strip('\x00')
                            exif_data[tag] = data
                except Exception:
                    pass

                # 3. GPS IFD
                # 0x8825 is the tag for GPSInfo which points to the GPS IFD
                try:
                    gps_ifd = exif.get_ifd(0x8825)
                    if gps_ifd:
                        from PIL.ExifTags import GPSTAGS
                        gps_data = {}
                        for tag_id, data in gps_ifd.items():
                            tag = GPSTAGS.get(tag_id, tag_id)
                            gps_data[tag] = data
                        exif_data['GPSInfo'] = gps_data
                except Exception:
                    pass

    except Exception as e:
        print(f"Error extracting EXIF from {image_path}: {e}")
    return exif_data

def get_gps_data(exif_data, xmp_data=None):
    """Convert GPSInfo to decimal degrees, with fallback to XMP."""
    gps_info = exif_data.get('GPSInfo')
    
    # Ensure gps_info is a dictionary. Sometimes EXIF might store an offset/int here.
    if not isinstance(gps_info, dict):
        gps_info = None

    def convert_to_degrees(value):
        try:
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        except (TypeError, IndexError, ValueError, ZeroDivisionError):
            return None

    lat, lon, alt = None, None, None

    if gps_info:
        if 'GPSLatitude' in gps_info and 'GPSLatitudeRef' in gps_info:
            lat = convert_to_degrees(gps_info['GPSLatitude'])
            if lat is not None and gps_info['GPSLatitudeRef'] != 'N':
                lat = -lat

        if 'GPSLongitude' in gps_info and 'GPSLongitudeRef' in gps_info:
            lon = convert_to_degrees(gps_info['GPSLongitude'])
            if lon is not None and gps_info['GPSLongitudeRef'] != 'E':
                lon = -lon
                
        if 'GPSAltitude' in gps_info:
            try:
                alt = float(gps_info['GPSAltitude'])
                if gps_info.get('GPSAltitudeRef') == b'\x01': # 1 is below sea level
                    alt = -alt
            except (TypeError, ValueError, ZeroDivisionError):
                pass

    # Fallback to XMP if GPS data is missing
    if xmp_data:
        if lat is None and 'GPSLatitude' in xmp_data:
            try:
                lat = float(xmp_data['GPSLatitude'])
            except (TypeError, ValueError):
                pass
        if lon is None and 'GPSLongitude' in xmp_data:
            try:
                lon = float(xmp_data['GPSLongitude'])
            except (TypeError, ValueError):
                pass
        if alt is None and 'GPSAltitude' in xmp_data:
            try:
                alt = float(xmp_data['GPSAltitude'])
            except (TypeError, ValueError):
                pass

    return lat, lon, alt

def extract_iptc_from_image(image_path):
    """Extract IPTC metadata from an image file."""
    IPTC_TAGS = {
        (2, 5): 'ObjectName',
        (2, 25): 'Keywords',
        (2, 55): 'DateCreated',
        (2, 90): 'City',
        (2, 92): 'SubLocation',
        (2, 95): 'ProvinceState',
        (2, 101): 'CountryName',
        (2, 105): 'Headline',
        (2, 116): 'CopyrightNotice',
        (2, 120): 'Caption',
    }
    iptc_data = {}
    try:
        with Image.open(image_path) as img:
            iptc_raw = IptcImagePlugin.getiptcinfo(img)
            if iptc_raw:
                for tag, value in iptc_raw.items():
                    tag_name = IPTC_TAGS.get(tag, f"IPTC_{tag[0]}_{tag[1]}")
                    if isinstance(value, bytes):
                        value = value.decode('utf-8', errors='replace')
                    elif isinstance(value, list):
                        decoded_values = [v.decode('utf-8', errors='replace') if isinstance(v, bytes) else str(v) for v in value]
                        value = ", ".join(decoded_values)
                    iptc_data[tag_name] = value
    except Exception as e:
        print(f"Error extracting IPTC from {image_path}: {e}")
    return iptc_data

def format_creation_date(date_str):
    """Parse various date formats into a standard MM/DD/YYYY string."""
    if not date_str or not isinstance(date_str, str):
        return date_str
    
    # Clean the date string: take only the first 19 characters for YYYY-MM-DD HH:MM:SS
    # This handles sub-seconds and some timezone formats simply
    clean_date = date_str.replace('T', ' ').split('.')[0].split('+')[0].strip()
    if clean_date.endswith('Z'):
        clean_date = clean_date[:-1]

    # Try common formats
    formats = [
        "%Y:%m:%d %H:%M:%S",  # EXIF standard
        "%Y-%m-%d %H:%M:%S",  # XMP/ISO style
        "%Y:%m:%d",           # Date only (EXIF)
        "%Y-%m-%d",           # Date only (ISO)
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(clean_date, fmt)
            return dt.strftime("%m/%d/%Y")
        except ValueError:
            continue
            
    return date_str

def catalog_images(input_dir, refresh=False):
    input_path = Path(input_dir)
    if not input_path.exists() or not input_path.is_dir():
        print(f"Error: {input_dir} is not a valid directory.")
        return

    # Database connection
    db_url = os.getenv('DB_External_URL')
    if not db_url:
        print("Error: DB_External_URL not found in .env")
        return

    engine = create_engine(db_url)
    table_name = 'catalogdata'

    # Create table if not exists with the full current schema
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
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
        """))
        
    # Robust migration for existing tables: add columns one by one if they don't exist
    # Using a separate connection for each to avoid transaction abortion issues
    new_cols = [
        ("Software", "TEXT"), ("SerialNumber", "TEXT"), ("ExposureBias", "TEXT"),
        ("MeteringMode", "TEXT"), ("Flash", "TEXT"), ("WhiteBalance", "TEXT"),
        ("FocalLength35mm", "TEXT"), ("ExposureProgram", "TEXT"), ("SubjectDistance", "TEXT"),
        ("Latitude", "DOUBLE PRECISION"), ("Longitude", "DOUBLE PRECISION"),
        ("Altitude", "DOUBLE PRECISION"), ("Width", "INTEGER"), ("Height", "INTEGER"),
        ("FileSize", "BIGINT"), ("Rating", "TEXT"), ("Artist", "TEXT"), ("Copyright", "TEXT"),
        ("extension", "TEXT")
    ]
    
    for col_name, col_type in new_cols:
        try:
            with engine.begin() as conn:
                conn.execute(text(f"""
                    DO $$ 
                    BEGIN 
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                       WHERE table_name='{table_name}' AND column_name='{col_name}') THEN
                            ALTER TABLE {table_name} ADD COLUMN "{col_name}" {col_type};
                        END IF;
                    END $$;
                """))
        except Exception as e:
            print(f"Error adding column {col_name}: {e}")

    # Get existing file mtimes from database for change detection
    existing_files = {}
    if not refresh:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT filepath, last_modified FROM {table_name}"))
                for row in result:
                    existing_files[row[0]] = row[1]
        except Exception as e:
            print(f"Note: Could not fetch existing data: {e}")
    else:
        print("Full refresh requested. Ignoring existing database records.")

    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.nef', '.dng'}
    all_metadata = []
    
    print(f"Scanning directory: {input_dir}")
    count = 0
    updated_count = 0
    
    # Use walk for recursion
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() not in image_extensions:
                continue
            
            count += 1
            if count % 1000 == 0:
                print(f"Scanned {count} images...")

            # Change detection
            mtime = file_path.stat().st_mtime
            
            # Also check sidecar mtime for professional workflows (Lightroom)
            # If sidecar is newer than the image, we should re-process
            sidecar_path = file_path.with_suffix('.xmp')
            if not sidecar_path.exists():
                sidecar_path = Path(str(file_path) + ".xmp")
            
            if sidecar_path.exists():
                mtime = max(mtime, sidecar_path.stat().st_mtime)

            filepath_str = str(file_path.absolute())
            
            if not refresh and filepath_str in existing_files and existing_files[filepath_str] == mtime:
                continue
            
            updated_count += 1
            if updated_count % 100 == 0:
                print(f"Processing updated/new image {updated_count}: {file}")

            exif = extract_exif_from_image(file_path)
            iptc = extract_iptc_from_image(file_path)
            
            # Extract XMP if available
            xmp = {}
            if process_image_xmp:
                try:
                    abs_path = file_path.resolve()
                    xmp_raw = process_image_xmp(str(abs_path))
                    xmp = xmp_raw if isinstance(xmp_raw, dict) else {}
                except Exception as e:
                    pass # Silent fail for XMP

            lat, lon, alt = get_gps_data(exif, xmp)

            # Combine all data, prioritizing EXIF but falling back to XMP and IPTC
            # XMP often contains data written by Lightroom/PhotoShop
            data = {
                'filepath': filepath_str,
                'filename': file_path.stem,
                'CameraModel': exif.get('Model') or xmp.get('Model') or xmp.get('CameraModel') or '',
                'LensModel': exif.get('LensModel') or xmp.get('LensModel') or xmp.get('Lens') or xmp.get('LensInfo') or '',
                'FocalLength': str(exif.get('FocalLength') or xmp.get('FocalLength') or xmp.get('focalLength') or ''),
                'shutter': decimal_to_fraction(exif.get('ExposureTime') or xmp.get('ExposureTime') or xmp.get('ShutterSpeedValue') or xmp.get('shutterSpeed') or exif.get('ShutterSpeedValue')),
                'Aperture': str(exif.get('FNumber') or xmp.get('FNumber') or xmp.get('ApertureValue') or xmp.get('aperture') or exif.get('ApertureValue') or ''),
                'ISO': str(exif.get('ISOSpeedRatings') or xmp.get('ISOSpeedRatings') or xmp.get('ISO') or xmp.get('ISOSpeed') or xmp.get('iso') or xmp.get('isoSpeedRatings') or ''),
                'CreationDate': format_creation_date(exif.get('DateTimeOriginal') or xmp.get('DateTimeOriginal') or xmp.get('CreateDate') or xmp.get('DateCreated')),
                'Genre': exif.get('Genre') or xmp.get('genre') or xmp.get('Genre') or '',
                'keywords': iptc.get('Keywords') or xmp.get('Keywords') or xmp.get('subject') or '',
                'ImageDescription': exif.get('ImageDescription') or iptc.get('Caption') or xmp.get('ImageDescription') or xmp.get('description') or xmp.get('title') or '',
                'City': iptc.get('City') or xmp.get('City') or xmp.get('Iptc4xmpCore_City') or xmp.get('city') or '',
                'SubLocation': iptc.get('SubLocation') or xmp.get('Sublocation') or xmp.get('Iptc4xmpCore_Sublocation') or xmp.get('sublocation') or '',
                'ProvinceState': iptc.get('ProvinceState') or xmp.get('ProvinceState') or xmp.get('Iptc4xmpCore_ProvinceState') or xmp.get('state') or '',
                'Software': exif.get('Software') or xmp.get('CreatorTool') or xmp.get('Software') or '',
                'SerialNumber': str(exif.get('BodySerialNumber') or exif.get('SerialNumber') or xmp.get('SerialNumber') or ''),
                'ExposureBias': str(exif.get('ExposureBiasValue') if 'ExposureBiasValue' in exif else (xmp.get('ExposureBiasValue') or '')),
                'MeteringMode': str(exif.get('MeteringMode') if 'MeteringMode' in exif else (xmp.get('MeteringMode') or '')),
                'Flash': str(exif.get('Flash') if 'Flash' in exif else (xmp.get('Flash') or '')),
                'WhiteBalance': str(exif.get('WhiteBalance') if 'WhiteBalance' in exif else (xmp.get('WhiteBalance') or '')),
                'FocalLength35mm': str(exif.get('FocalLengthIn35mmFilm') if 'FocalLengthIn35mmFilm' in exif else (xmp.get('FocalLengthIn35mmFilm') or '')),
                'ExposureProgram': str(exif.get('ExposureProgram') if 'ExposureProgram' in exif else (xmp.get('ExposureProgram') or '')),
                'SubjectDistance': str(exif.get('SubjectDistance') if 'SubjectDistance' in exif else (xmp.get('ApproximateFocusDistance') or '')),
                'Latitude': lat,
                'Longitude': lon,
                'Altitude': alt,
                'Width': exif.get('Width') or exif.get('ExifImageWidth') or xmp.get('PixelXDimension') or xmp.get('ImageWidth'),
                'Height': exif.get('Height') or exif.get('ExifImageHeight') or xmp.get('PixelYDimension') or xmp.get('ImageHeight'),
                'Rating': str(xmp.get('Rating') or exif.get('Rating') or ''),
                'Artist': exif.get('Artist') or xmp.get('Creator') or xmp.get('creator') or '',
                'Copyright': exif.get('Copyright') or xmp.get('Copyright') or xmp.get('Rights') or '',
                'extension': file_path.suffix.lower(),
                'FileSize': file_path.stat().st_size,
                'last_modified': mtime
            }
            all_metadata.append(data)
            
            # Batch upsert every 500 records for efficiency
            if len(all_metadata) >= 500:
                upsert_to_db(all_metadata, engine, table_name)
                all_metadata = []

    # Final upsert for remaining records
    if all_metadata:
        upsert_to_db(all_metadata, engine, table_name)

    print(f"Finished. Total images found: {count}. Updated/New images processed: {updated_count}.")

def upsert_to_db(metadata_list, engine, table_name):
    df = pd.DataFrame(metadata_list)
    
    # Clean string columns of NUL characters which PostgreSQL does not support
    for col in df.select_dtypes([object]):
        df[col] = df[col].apply(lambda x: x.replace('\x00', '') if isinstance(x, str) else x)
        
    # Ensure types for numeric columns in case they are all None (which pandas might make object/text)
    numeric_cols = ['Latitude', 'Longitude', 'Altitude', 'Width', 'Height', 'FileSize', 'last_modified']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    with engine.begin() as conn:
        df.to_sql('temp_catalog', conn, if_exists='replace', index=False)
        
        cols = ", ".join([f'"{c}"' for c in df.columns])
        update_set = ", ".join([f'"{c}" = EXCLUDED."{c}"' for c in df.columns if c != 'filepath'])
        
        insert_query = text(f"""
            INSERT INTO {table_name} ({cols})
            SELECT {cols} FROM temp_catalog
            ON CONFLICT (filepath) DO UPDATE SET
            {update_set};
        """)
        conn.execute(insert_query)
        conn.execute(text("DROP TABLE temp_catalog;"))
    print(f"Batch of {len(metadata_list)} records upserted.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Catalog images from a directory into the database.")
    parser.add_argument("input_dir", help="Directory to scan for images")
    parser.add_argument("-r", "--refresh", action="store_true", help="Perform a full refresh, re-processing all images")
    args = parser.parse_args()
    
    catalog_images(args.input_dir, refresh=args.refresh)
