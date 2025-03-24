from PIL import Image

def pixelate_image(input_path, output_path, num_colors=16):
    """
    Convert an image to a pixelated version with reduced colors.

    Args:
        input_path (str): Path to the input image.
        output_path (str): Path to save the output image.
        num_colors (int): Number of colors to reduce the image to.
    """
    # Open the image
    image = Image.open(input_path)

    # Define the pixelation factor (e.g., 10 means reducing resolution by 10x)
    pixelation_factor = 10

    # Convert the image to P mode (palette-based) with the specified number of colors
    pixelated_image = image.convert("P", palette=Image.ADAPTIVE, colors=num_colors)

    # Resize the image to a smaller size
    small_image = image.resize(
        (image.width // pixelation_factor, image.height // pixelation_factor),
        resample=Image.NEAREST
    )

    # Scale it back to the original size
    pixelated_image = small_image.resize(
        (image.width, image.height),
        resample=Image.NEAREST
    )

    # Save the pixelated image
    pixelated_image.save(output_path)
    print(f"Pixelated image saved to {output_path}")

# Example usage
if __name__ == "__main__":
    input_image_path = "input.png"  # Replace with your input image path

    # Open the image
    image = Image.open(input_image_path)

    # Save the pixelated image
    output_image_path = "output.png"  # Replace with your desired output path
    pixelate_image(input_image_path, output_image_path, num_colors=16)
