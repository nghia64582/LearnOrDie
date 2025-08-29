import zipfile
import xml.etree.ElementTree as ET
import os

def read_geogebra_elements(ggb_filepath):
    """
    Reads a GeoGebra (.ggb) file, extracts 'geogebra.xml', and returns a
    list of geometric elements in a simplified string format.

    Args:
        ggb_filepath (str): The path to the .ggb file.

    Returns:
        list: A list of strings, where each string represents a geometric
              element (e.g., "point(1,1)", "circle(1,1,3)").
              Returns an empty list if the file cannot be processed or
              'geogebra.xml' is not found/valid.
    """
    elements = []
    temp_dir = "temp_ggb_extract"

    try:
        # Create a temporary directory to extract contents
        os.makedirs(temp_dir, exist_ok=True)

        # 1. Unzip the .ggb file
        with zipfile.ZipFile(ggb_filepath, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            print(f"Extracted '{ggb_filepath}' to '{temp_dir}'")

        # 2. Locate and parse geogebra.xml
        xml_path = os.path.join(temp_dir, 'geogebra.xml')
        if not os.path.exists(xml_path):
            print(f"Error: 'geogebra.xml' not found in '{ggb_filepath}'")
            return []

        tree = ET.parse(xml_path)
        root = tree.getroot()

        for element_tag in root.iter('element'):
            # Get common attributes
            element_type = element_tag.get('type')
            label = element_tag.get('label')

            if element_type == 'point':
                # Points have <coords> tag
                coords_tag = element_tag.find('coords')
                if coords_tag is not None:
                    x = coords_tag.get('x')
                    y = coords_tag.get('y')
                    z = coords_tag.get('z')
                    elements.append(f"point({label}, {x}, {y})")
            elif element_type == 'circle':
                definition_tag = element_tag.find('definition')
                if definition_tag is not None:
                    if definition_tag.get('type') == 'circle_point_radius':
                        center_ref = definition_tag.find('center').get('exp')
                        radius_exp = definition_tag.find('radius').get('exp')
                        elements.append(f"circle({label}, center={center_ref}, radius={radius_exp})")
                    else:
                        elements.append(f"circle({label}, {definition_tag.get('type', 'unknown_definition')})")
                else:
                    elements.append(f"circle({label}, unknown_definition)")

            elif element_type == 'segment':
                # Segments are often defined by two points
                definition_tag = element_tag.find('definition')
                if definition_tag is not None and definition_tag.get('type') == 'segment_two_points':
                    point1_ref = definition_tag.get('p1')
                    point2_ref = definition_tag.get('p2')
                    elements.append(f"segment({label}, {point1_ref}, {point2_ref})")
            elif element_type == 'line':
                # Lines can be defined by two points, or a point and a direction vector, etc.
                definition_tag = element_tag.find('definition')
                if definition_tag is not None and definition_tag.get('type') == 'line_two_points':
                    point1_ref = definition_tag.get('p1')
                    point2_ref = definition_tag.get('p2')
                    elements.append(f"line({label}, {point1_ref}, {point2_ref})")
            else:
                elements.append(f"{element_type}({label})") # Generic catch-all

    except zipfile.BadZipFile:
        print(f"Error: '{ggb_filepath}' is not a valid zip file.")
    except ET.ParseError:
        print(f"Error: 'geogebra.xml' in '{ggb_filepath}' is not a valid XML file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Clean up the temporary directory
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory '{temp_dir}'.")
    return elements

# --- Example Usage ---
if __name__ == "__main__":
    dummy_ggb_filename = "image3.ggb"

    print(f"\nCreated dummy GGB file: '{dummy_ggb_filename}'")

    # Read elements from the dummy file
    parsed_elements = read_geogebra_elements(dummy_ggb_filename)

    print("\n--- Parsed GeoGebra Elements ---")
    if parsed_elements:
        for element_str in parsed_elements:
            print(element_str)
    else:
        print("No elements found or an error occurred.")
