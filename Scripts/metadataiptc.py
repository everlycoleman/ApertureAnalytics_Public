from PIL import Image
from PIL import IptcImagePlugin


def get_iptc_data(image_path):
    """
    Extracts all IPTC data from a JPG file.

    Args:
        image_path (str): The path to the JPG file.

    Returns:
        dict: A dictionary containing the IPTC data.
    """
    # Common IPTC tags mapping (Record 2 - Application Record)
    IPTC_TAGS = {
        (2, 5): 'ObjectName',
        (2, 7): 'EditStatus',
        (2, 10): 'Urgency',
        (2, 15): 'Category',
        (2, 20): 'SupplementalCategories',
        (2, 25): 'Keywords',
        (2, 40): 'SpecialInstructions',
        (2, 55): 'DateCreated',
        (2, 60): 'TimeCreated',
        (2, 80): 'ByLine',
        (2, 85): 'ByLineTitle',
        (2, 90): 'City',
        (2, 92): 'SubLocation',
        (2, 95): 'ProvinceState',
        (2, 100): 'CountryCode',
        (2, 101): 'CountryName',
        (2, 103): 'OriginalTransmissionReference',
        (2, 105): 'Headline',
        (2, 110): 'Credit',
        (2, 115): 'Source',
        (2, 116): 'CopyrightNotice',
        (2, 120): 'Caption',
        (2, 122): 'CaptionWriter',
    }
    
    iptc_data = {}

    try:
        with Image.open(image_path) as img:
            # Get IPTC data from image info
            iptc_raw = IptcImagePlugin.getiptcinfo(img)
            
            if iptc_raw:
                for tag, value in iptc_raw.items():
                    # Get human-readable tag name
                    tag_name = IPTC_TAGS.get(tag, f"IPTC_{tag[0]}_{tag[1]}")
                    
                    # Handle the value - it might be bytes or a list of bytes
                    if isinstance(value, bytes):
                        try:
                            value = value.decode('utf-8', errors='replace')
                        except:
                            value = value.decode('latin-1', errors='replace')
                    elif isinstance(value, list):
                        # Some IPTC fields can have multiple values
                        decoded_values = []
                        for item in value:
                            if isinstance(item, bytes):
                                try:
                                    decoded_values.append(item.decode('utf-8', errors='replace'))
                                except:
                                    decoded_values.append(item.decode('latin-1', errors='replace'))
                            else:
                                decoded_values.append(str(item))
                        value = decoded_values if len(decoded_values) > 1 else decoded_values[0] if decoded_values else ''
                    
                    iptc_data[tag_name] = value

    except FileNotFoundError:
        print(f"Error: The file at {image_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

    return iptc_data


# --- Example Usage ---
# Replace 'your_image.jpg' with the path to your image file.
image_file = '../Photo_Uploads/New/_EVY2593.jpg'
extracted_iptc = get_iptc_data(image_file)

if extracted_iptc:
    print("IPTC Data:")
    for key, value in extracted_iptc.items():
        print(f"  {key}: {value}")
else:
    print("No IPTC data found or an error occurred.")
