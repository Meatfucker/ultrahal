import base64
import colorsys
import csv
import io
import json
import random

from PIL import Image


def lighten_color(hex_color, amount=0.5):
    """Lighten a given hex color by a given amount (0–1)."""
    hex_color = hex_color.lstrip('#')
    r, g, b = [int(hex_color[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = max(0, min(1, l * amount))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return '#{:02x}{:02x}{:02x}'.format(int(r * 255), int(g * 255), int(b * 255))

def generate_distinct_colors(n):
    """Generate n visually distinct hex colors around the HSV color wheel."""
    colors = []
    for i in range(n):
        hue = i / n
        r, g, b = colorsys.hsv_to_rgb(hue, 0.65, 0.3)  # S=0.65, V=0.5 for darker base
        colors.append('#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255)))
    return colors


def build_palette():
    """Build a dictionary of model → color based on built-in model types."""
    model_map = {
        "Ace": ["ACERequest"],
        "AuraFlow": ["AuraFlowRequest"],
        "Chroma": ["ChromaRequest", "ChromaI2IRequest"],
        "Flux": ["FluxRequest", "FluxI2IRequest", "FluxKontextRequest", "FluxInpaintRequest", "FluxFillRequest"],
        "Framepack": ["FramepackRequest"],
        "HiDream": ["HiDreamRequest"],
        "Hunyuan Video": ["HunyuanVideoRequest"],
        "Processors": ["RealESRGANRequest", "Swin2SRRequest"],
        "Kandinsky5": ["Kandinsky5Request"],
        "LLM": ["LLMRequest", "LLMRerollRequest"],
        "Lumina 2": ["Lumina2Request"],
        "Qwen Image": ["QwenRequest", "QwenI2IRequest", "QwenEditRequest", "QwenInpaintRequest", "QwenEditPlusRequest"],
        "Sana Sprint": ["SanaSprintRequest", "SanaSprintI2IRequest"],
        "SD 1.5": ["SD15Request", "SD15I2IRequest", "SD15InpaintRequest"],
        "SDXL": ["SDXLRequest", "SDXLI2IRequest", "SDXLInpaintRequest"],
        "Wan": ["WanRequest", "WanV2VRequest", "WanVACERequest"]
    }
    types = list(model_map.keys())
    base_colors = generate_distinct_colors(len(types))
    palette = {}

    for i, model_type in enumerate(types):
        base_color = base_colors[i]
        models = model_map[model_type]

        if len(models) == 1:
            palette[models[0]] = base_color
        else:
            for j, model in enumerate(models):
                # Gradually lighten
                lighten_factor = 1 + (j / (len(models) * 1.2))
                variant = lighten_color(base_color, lighten_factor)
                palette[model] = variant
    return palette

MODEL_COLOR_PALETTE = build_palette()

def get_model_color(model_name):
    """Return a hex color for the given model name."""
    return MODEL_COLOR_PALETTE.get(model_name, "#808080")

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