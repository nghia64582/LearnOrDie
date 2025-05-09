from PIL import Image
import os

def cut_image_grid(image_path, num_rows, num_cols, output_dir="output_tiles", output_format="png"):
    """
    Cuts an image into a grid of tiles based on the specified number of rows and columns.

    Args:
        image_path (str): Path to the input image file (.png, .jpg, etc.).
        num_rows (int): Number of rows in the grid.
        num_cols (int): Number of columns in the grid.
        output_dir (str, optional): Directory to save the output tiles. Defaults to "output_tiles".
        output_format (str, optional): Format to save the tiles ("png", "jpg", etc.). Defaults to "png".
    """
    try:
        img = Image.open(image_path)
        width, height = img.size
        tile_width = width // num_cols
        tile_height = height // num_rows

        os.makedirs(output_dir, exist_ok=True)

        for row in range(num_rows):
            for col in range(num_cols):
                left = col * tile_width
                top = row * tile_height
                right = (col + 1) * tile_width
                bottom = (row + 1) * tile_height

                # Ensure the last tiles capture any remaining pixels due to integer division
                if col == num_cols - 1 and width % num_cols != 0:
                    right = width
                if row == num_rows - 1 and height % num_rows != 0:
                    bottom = height

                tile = img.crop((left, top, right, bottom))
                tile_filename = f"tile_{row:02d}_{col:02d}.{output_format.lower()}"
                tile_path = os.path.join(output_dir, tile_filename)
                tile.save(tile_path)
                print(f"Saved tile: {tile_path}")

        print(f"Image '{image_path}' successfully cut into {num_rows}x{num_cols} grid tiles in '{output_dir}'.")

    except FileNotFoundError:
        print(f"Error: Image file not found at '{image_path}'.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    image_file = input("Enter the path to the image file: ")
    try:
        rows = int(input("Enter the number of rows: "))
        cols = int(input("Enter the number of columns: "))
        if rows <= 0 or cols <= 0:
            print("Error: Number of rows and columns must be positive integers.")
        else:
            output_directory = input("Enter the output directory (leave blank for 'output_tiles'): ")
            if not output_directory:
                output_directory = "output_tiles"
            output_format = input("Enter the output format (png, jpg, etc., leave blank for 'png'): ").lower()
            if not output_format:
                output_format = "png"
            cut_image_grid(image_file, rows, cols, output_directory, output_format)
    except ValueError:
        print("Error: Invalid input for number of rows or columns. Please enter integers.")