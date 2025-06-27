import os
from PIL import Image
from typing import List

def cut_image_to_grid(image_path: str, rows: int, cols: int, output_dir: str = "cut_output") -> List[str]:
    """
    Cuts an image into a grid of (rows x cols) and saves each cell as a separate image.

    Args:
        image_path (str): Path to the input image.
        rows (int): Number of rows.
        cols (int): Number of columns.
        output_dir (str): Directory to save the cut images.

    Returns:
        List[str]: List of file paths to the saved images.
    """
    os.makedirs(output_dir, exist_ok=True)
    image = Image.open(image_path)
    width, height = image.size
    cell_width = width // cols
    cell_height = height // rows
    output_files = []

    for row in range(rows):
        for col in range(cols):
            left = col * cell_width
            top = row * cell_height
            right = left + cell_width
            bottom = top + cell_height
            cell = image.crop((left, top, right, bottom))
            filename = os.path.join(output_dir, f"card_{col*3+row+6}.png")
            cell.save(filename)
            output_files.append(filename)

    return output_files

cut_image_to_grid("bobai.jpg", 3, 9)