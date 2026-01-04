from PIL import Image
import xml.etree.ElementTree as ET
import re
import os
from pathlib import Path
from PIL import IptcImagePlugin
from PIL.ExifTags import TAGS

# Constants
image_path = "../Photo_Uploads/New/_EVY2460-HDR.jpg"


def display_xmp_data(xmp_data, indent=0):
    """Display XMP metadata in a formatted manner."""
    print("XMP Data Found:")
    for key, value in xmp_data.items():
        if isinstance(value, dict):
            print("  " * indent + f"{key}:")
            display_xmp_data(value, indent + 1)
        else:
            print("  " * indent + f"{key}: {value}")


def parse_xml_to_nested_dict(xml_string):
    """Convert XML structure to nested dictionary, preserving hierarchy."""
    if not xml_string:
        return {}

    try:
        # 1. Clean up XML: remove all namespaces and prefixes to simplify parsing
        # Remove namespace declarations
        cleaned_xml = re.sub(r'\sxmlns(:?\w+)?="[^"]*"', '', xml_string)
        # Remove prefixes from tags: <x:xmpmeta -> <xmpmeta, </rdf:RDF -> </RDF
        cleaned_xml = re.sub(r'(</?)\w+:', r'\1', cleaned_xml)
        # Remove prefixes from attributes: exif:ExposureTime -> ExposureTime
        cleaned_xml = re.sub(r'\s\w+:(\w+=")', r' \1', cleaned_xml)
        
        # 2. Parse the simplified XML
        root = ET.fromstring(cleaned_xml)

        def element_to_dict(element):
            """Recursively convert XML element to nested dictionary."""
            result = {}
            
            # Get element attributes - these often contain the metadata we want in XMP
            if element.attrib:
                for attr, val in element.attrib.items():
                    # Strip namespace prefixes from attributes too
                    attr_name = attr.split('}')[-1]
                    result[attr_name] = val
            
            # Get element text if it exists
            if element.text and element.text.strip():
                result['_text'] = element.text.strip()
            
            # Process child elements
            for child in element:
                # Remove namespace from tag
                child_tag = child.tag.split('}')[-1]
                child_data = element_to_dict(child)
                
                # If key already exists, convert to list or append to list
                if child_tag in result:
                    if not isinstance(result[child_tag], list):
                        result[child_tag] = [result[child_tag]]
                    result[child_tag].append(child_data)
                else:
                    result[child_tag] = child_data
            
            # If only text exists and no attributes, return text directly instead of dict
            if len(result) == 1 and '_text' in result:
                return result['_text']
            
            return result if result else None

        # Get root tag name without namespace
        root_tag = root.tag.split('}')[-1]
        return {root_tag: element_to_dict(root)}
        
    except ET.ParseError as e:
        return {'error': f'XML Parse Error: {str(e)}'}


def extract_xmp_from_image(image_path):
    """
    Extract XMP metadata from an image file, including sidecar .xmp files.

    Args:
        image_path: Path to the image file

    Returns:
        Dictionary containing XMP data, or None if no data found
    """
    nested_data = {}
    
    # 1. Try to get embedded XMP from the image itself
    try:
        with Image.open(image_path) as img:
            xmp_data = img.getxmp()
            if xmp_data:
                for key, value in xmp_data.items():
                    if isinstance(value, str):
                        # Parse XML string to nested dictionary
                        parsed_values = parse_xml_to_nested_dict(value)
                        nested_data.update(parsed_values)
                    else:
                        nested_data[key] = value
    except Exception:
        pass

    # 2. Look for sidecar files (common in professional workflows like Lightroom)
    # Check for both 'image.xmp' and 'image.dng.xmp' styles
    path_obj = Path(image_path)
    sidecar_candidates = [
        path_obj.with_suffix('.xmp'),
        Path(str(path_obj) + ".xmp")
    ]
    
    for candidate in sidecar_candidates:
        if candidate.exists() and candidate.is_file():
            try:
                # Read sidecar file content
                with open(candidate, 'r', encoding='utf-8', errors='ignore') as f:
                    xml_content = f.read()
                    # Parse sidecar XML
                    parsed_values = parse_xml_to_nested_dict(xml_content)
                    # Sidecar data often updates/overrides embedded data
                    if parsed_values:
                        nested_data.update(parsed_values)
            except Exception:
                pass

    return nested_data if nested_data else None


def process_image_xmp(image_path):
    """
    Process and return XMP metadata from an image as a flat-ish dictionary.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dictionary containing XMP data, or dictionary with error message
    """
    try:
        xmp_data = extract_xmp_from_image(image_path)

        if not xmp_data:
            return {"error": "No XMP data found in the image."}

        # Flatten the most common structure: xmpmeta -> RDF -> Description
        # In many Adobe-generated XMP, there is one Description tag with many attributes or child tags
        flat_data = {}
        
        def flatten_dict(d, prefix=''):
            if not isinstance(d, dict):
                return
            for k, v in d.items():
                if isinstance(v, dict):
                    flatten_dict(v, f"{prefix}{k}_")
                else:
                    flat_data[f"{prefix}{k}"] = v

        # Try to find the main description(s)
        descriptions = []
        
        # Look for Descriptions in common XMP locations
        potential_rdf_sources = []
        if 'xmpmeta' in xmp_data:
            potential_rdf_sources.append(xmp_data['xmpmeta'].get('RDF', {}))
        if 'RDF' in xmp_data:
            potential_rdf_sources.append(xmp_data['RDF'])
            
        for rdf in potential_rdf_sources:
            if isinstance(rdf, dict):
                desc = rdf.get('Description')
                if isinstance(desc, list):
                    descriptions.extend(desc)
                elif isinstance(desc, dict):
                    descriptions.append(desc)
            elif isinstance(rdf, list):
                for item in rdf:
                    if isinstance(item, dict):
                        desc = item.get('Description')
                        if isinstance(desc, list):
                            descriptions.extend(desc)
                        elif isinstance(desc, dict):
                            descriptions.append(desc)
        
        # Process all descriptions found
        for desc in descriptions:
            if isinstance(desc, dict):
                # 1. Process items in the description
                for k, v in desc.items():
                    if not isinstance(v, (dict, list)):
                        # Direct attribute or simple tag with text
                        if k not in flat_data or not flat_data[k]:
                            flat_data[k] = v
                    elif isinstance(v, dict):
                        # Nested tag
                        # If it has _text, use it as the primary value for this tag
                        if '_text' in v:
                            if k not in flat_data or not flat_data[k]:
                                flat_data[k] = v['_text']
                        
                        # Also flatten sub-items
                        for sub_k, sub_v in v.items():
                            if sub_k == '_text':
                                continue
                            if not isinstance(sub_v, (dict, list)):
                                key_name = f"{k}_{sub_k}"
                                if key_name not in flat_data or not flat_data[key_name]:
                                    flat_data[key_name] = sub_v
                            elif sub_k == 'li' and isinstance(sub_v, (str, list)):
                                if isinstance(sub_v, list):
                                    flat_data[k] = ", ".join([str(x) for x in sub_v if x])
                                else:
                                    flat_data[k] = sub_v
            elif isinstance(desc, list):
                # This case is usually handled by the extend() above, but just in case
                pass 

        # If we didn't get much from description, flatten the whole thing (as a fallback)
        if len(flat_data) < 5:
            flatten_dict(xmp_data)

        return flat_data

    except FileNotFoundError:
        return {"error": f"Error: Image file not found at '{image_path}'."}
    except Exception as e:
        return {"error": f"An error occurred while processing the image: {e}"}


def get_nested_value(data, *keys):
    """
    Safely navigate nested dictionary structure.
    
    Args:
        data: The dictionary to navigate
        *keys: Sequence of keys to traverse
    
    Returns:
        The value at the specified path, or None if path doesn't exist
    """
    result = data
    for key in keys:
        if isinstance(result, dict) and key in result:
            result = result[key]
        else:
            return None
    return result



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


def process_image_exif(image_path):
    """
    Process and display EXIF metadata from an image.

    Args:
        image_path: Path to the image file (defaults to DEFAULT_IMAGE_PATH)

    Returns:
        Dictionary containing EXIF data, or error message if failed
    """
    result = extract_exif_from_image(image_path)
    return result if result else {"error": "No EXIF data found in the image."}







def process_image_iptc(image_path):
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
                        value = decoded_values if len(decoded_values) > 1 else decoded_values[
                            0] if decoded_values else ''

                    iptc_data[tag_name] = value

    except FileNotFoundError:
        print(f"Error: The file at {image_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

    return iptc_data


# --- Example Usage ---
# Replace 'your_image.jpg' with the path to your image file.
if __name__ == "__main__":
    xmp=process_image_xmp(image_path)
    exif = process_image_exif(image_path)
    iptc = process_image_iptc(image_path)
    
    print("=== XMP Data ===")
    if xmp and "error" not in xmp:
        display_xmp_data(xmp)
    else:
        print(xmp)
    
    print("\n=== EXIF Data ===")
    print(exif)
    
    print("\n=== IPTC Data ===")
    print(iptc)
    




