import drawsvg as dw

def create_basic_shapes_svg(filename="basic_shapes.svg"):
    """
    Creates an SVG file containing a square, circle, and rectangle using drawsvg.

    Args:
        filename (str): The name of the SVG file to create.
    """
    # Create a new Drawing object
    # The width and height define the viewBox of the SVG.
    d = dw.Drawing(400, 300, origin='center')

    # Add a background rectangle (optional)
    d.append(dw.Rectangle(-200, -150, 400, 300, fill='#f0f0f0', stroke='black', stroke_width=2))

    # Add a square
    # x, y: top-left corner relative to the origin (center of the drawing)
    # width, height: dimensions of the square
    # fill: fill color
    # stroke: border color
    # stroke_width: border thickness
    d.append(dw.Rectangle(-100, 50, 80, 80, fill='lightblue', stroke='blue', stroke_width=3))
    # Add text label for the square
    d.append(dw.Text('Square', 20, -100, 100, fill='black'))

    # Add a circle
    # cx, cy: center coordinates relative to the origin
    # r: radius
    # fill: fill color
    # stroke: border color
    # stroke_width: border thickness
    d.append(dw.Circle(0, 0, 60, fill='lightcoral', stroke='red', stroke_width=4))
    # Add text label for the circle
    d.append(dw.Text('Circle', 20, -20, 20, fill='black'))

    # Add a rectangle
    # x, y: top-left corner relative to the origin
    # width, height: dimensions of the rectangle
    # fill: fill color
    # rx, ry: horizontal and vertical radius for rounded corners
    d.append(dw.Rectangle(50, -120, 150, 70, fill='lightgreen', stroke='darkgreen', stroke_width=5, rx=10, ry=10))
    # Add text label for the rectangle
    d.append(dw.Text('Rounded Rectangle', 20, 70, -130, fill='black'))

    # Save the drawing to an SVG file
    d.save_svg(filename)
    print(f"SVG file '{filename}' created successfully!")

# Call the function to create the SVG file
create_basic_shapes_svg()
