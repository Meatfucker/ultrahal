import base64
import csv
import io
import json
import random
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


def get_csv_tags(csv_path: str, n: int) -> str:
    """
    Loads a CSV file, randomly selects n lines (excluding the header if present),
    and returns the first value from each selected line combined into a single string.

    Args:
        csv_path (str): Path to the CSV file.
        n (int): Number of random lines to select.

    Returns:
        str: Combined string of first values from the selected lines.
    """
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = list(csv.reader(f))

        # If there's a header row, optionally detect and skip it
        # (You can remove this if you always want to include the first line)
        if all(not cell.isdigit() for cell in reader[0]):  # crude header detection
            data = reader[1:]
        else:
            data = reader

        # Handle case where n > available lines
        n = min(n, len(data))

        # Randomly select rows
        selected_rows = random.sample(data, n)

        # Extract first values and join them
        first_values = [row[0] for row in selected_rows if row]
        return ' '.join(first_values)


def get_generic_danbooru_tags(csv_path, num_lines, category="0"):
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        filtered_rows = [row for row in reader if len(row) > 1 and row[1].strip() == category]

    if not filtered_rows:
        return ""

    selected_rows = random.sample(filtered_rows, min(num_lines, len(filtered_rows)))
    print(selected_rows)

    combined_string = " ".join(row[0] for row in selected_rows)

    return combined_string

def get_random_artist_prompt():
    with open('assets/artist.json', 'r') as file:
        data = json.load(file)
        selected_artist = random.choice(data)
        return selected_artist.get('prompt')