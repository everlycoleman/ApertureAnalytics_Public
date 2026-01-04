from PIL import Image
from PIL.ExifTags import TAGS

# Constants
DEFAULT_IMAGE_PATH = "../Photo_Uploads/New/_EVY2593.jpg"


def display_exif_data(exif_data):
    """Display EXIF metadata in a formatted manner."""
    print("EXIF Data Found:")
    for key, value in exif_data.items():
        print(f"  {key}: {value}")


def extract_exif_from_image(image_path):
    """
    Extract EXIF metadata from an image file.

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary containing EXIF data, or None if no data found

    Raises:
        FileNotFoundError: If image file doesn't exist
        Exception: For other image processing errors
    """
    exif_data = {}

    try:
        with Image.open(image_path) as img:
            # Get the EXIF data
            exif = img._getexif()

            if exif:
                # Iterate through all EXIF data fields
                for tag_id in exif:
                    # Get the tag name, instead of tag id
                    tag = TAGS.get(tag_id, tag_id)
                    data = exif.get(tag_id)

                    # Decode bytes if necessary
                    if isinstance(data, bytes):
                        try:
                            data = data.decode('utf-8')
                        except UnicodeDecodeError:
                            data = data.decode('latin-1')

                    exif_data[tag] = data
                return exif_data
            return None

    except FileNotFoundError:
        return {"error": f"Error: Image file not found at '{image_path}'"}
    except Exception as e:
        return {"error": f"An error occurred while processing the image: {e}"}


def process_image_metadata(image_path=DEFAULT_IMAGE_PATH):
    """
    Process and display EXIF metadata from an image.

    Args:
        image_path: Path to the image file (defaults to DEFAULT_IMAGE_PATH)

    Returns:
        Dictionary containing EXIF data, or error message if failed
    """
    result = extract_exif_from_image(image_path)
    return result if result else {"error": "No EXIF data found in the image."}


if __name__ == "__main__":
    result = process_image_metadata()
    if "error" not in result:
        display_exif_data(result)
    else:
        print(result["error"])
