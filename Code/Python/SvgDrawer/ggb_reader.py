import os
import zipfile
import xml.etree.ElementTree as ET
import math

def extract_geogebra_xml(ggb_path):
    """Extract geogebra.xml content from .ggb file."""
    with zipfile.ZipFile(ggb_path, "r") as z:
        with z.open("geogebra.xml") as f:
            return ET.parse(f)

def parse_point(elem):
    coords = elem.find("coords")
    if coords is not None:
        x = coords.attrib.get("x")
        y = coords.attrib.get("y")
        return f"Point {elem.attrib['label']}: ({x}, {y})"
    return f"Point {elem.attrib['label']}: No coordinates"

def parse_line(elem):
    eqn = elem.find("equation")
    if eqn is not None:
        a = eqn.attrib.get("a")
        b = eqn.attrib.get("b")
        c = eqn.attrib.get("c")
        return f"Line {elem.attrib['label']}: {a}x + {b}y + {c} = 0"
    return f"Line {elem.attrib['label']}: Unknown"

def parse_polygon(elem):
    points = [child.attrib.get("exp") for child in elem.findall("input/arg")]
    return f"Polygon {elem.attrib['label']}: Points = {points}"

def parse_circle(elem):
    """
    Handle GeoGebra conic-as-circle where <matrix> stores A0..A5.
    Uses the convention:
        A0 x^2 + A1 y^2 + 2*A3 xy + 2*A4 x + 2*A5 y + A2 = 0
    """
    label = elem.get("label", "")
    m = elem.find("matrix")
    if m is None:
        return f"Conic {label}: no matrix"

    # Collect coefficients from either attributes or <entry> children
    coeffs = {}
    if m.attrib:  # A0..A5 directly on <matrix>
        for k in ("A0","A1","A2","A3","A4","A5"):
            if k in m.attrib:
                coeffs[k] = float(m.attrib[k])
    else:         # entries as children
        for e in m.findall("entry"):
            name = e.attrib.get("name")
            val  = e.attrib.get("val")
            if name and val is not None:
                coeffs[name] = float(val)

    A0 = coeffs.get("A0", 0.0)  # x^2
    A1 = coeffs.get("A1", 0.0)  # y^2
    A2 = coeffs.get("A2", 0.0)  # constant
    A3 = coeffs.get("A3", 0.0)  # half of xy term
    A4 = coeffs.get("A4", 0.0)  # half of x term
    A5 = coeffs.get("A5", 0.0)  # half of y term

    # Circle test: equal quadratic terms, no xy term (within tolerance)
    if abs(A0 - A1) < 1e-9 and abs(A3) < 1e-9 and A0 != 0:
        cx = -A4 / A0
        cy = -A5 / A1
        r_sq = cx*cx + cy*cy - A2 / A0
        if r_sq >= 0:
            r = math.sqrt(r_sq)
            return f"Circle {label}: center=({cx:.6g}, {cy:.6g}), radius={r:.6g}"
        else:
            return f"Circle {label}: center=({cx:.6g}, {cy:.6g}), radius is imaginary (r^2={r_sq:.6g})"
    else:
        # Not a perfect circle (ellipse / hyperbola / rotated conic)
        # If needed, you could diagonalize to classify, but we just report raw.
        return (f"Conic {label}: not a circle; "
                f"A0={A0}, A1={A1}, A2={A2}, A3={A3}, A4={A4}, A5={A5}")

# Dispatch dictionary
HANDLERS = {
    "point": parse_point,
    "line": parse_line,
    "polygon": parse_polygon,
    "conic": parse_circle,   # circle stored as conic
}

def parse_objects(xml_tree):
    """Iterate through all GeoGebra objects and parse them."""
    root = xml_tree.getroot()
    for elem in root.findall(".//element"):
        obj_type = elem.attrib.get("type")
        label = elem.attrib.get("label", "Unnamed")

        handler = HANDLERS.get(obj_type)
        if handler:
            print(handler(elem))
        else:
            print(f"{obj_type.capitalize()} {label}: Unsupported type")

def main(ggb_file):
    xml_tree = extract_geogebra_xml(ggb_file)
    parse_objects(xml_tree)

if __name__ == "__main__":
    ggb_path = "i5.ggb"  # replace with your .ggb file
    if os.path.exists(ggb_path):
        main(ggb_path)
    else:
        print("File not found:", ggb_path)
