import base64
import io
from PIL import Image


async def base64_to_images(base64_images):
    """Converts a list of base64 images into a list of file-like objects."""
    image_files = []
    for base64_image in base64_images:
        img_data = base64.b64decode(base64_image)  # Decode base64 string
        img_file = io.BytesIO(img_data)  # Convert to file-like object
        image_files.append(img_file)
    return image_files

def image_to_base64(image_path, width, height):
    image = Image.open(image_path)
    image = image.convert("RGB")
    image = image.resize((width, height))
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")