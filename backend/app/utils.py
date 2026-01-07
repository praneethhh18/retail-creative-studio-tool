"""
Utility functions for the Retail Media Creative Tool.
"""
import os
import re
import uuid
import math
import hashlib
from pathlib import Path
from typing import Tuple, List, Optional
from PIL import Image
import numpy as np
from sklearn.cluster import KMeans
import structlog

logger = structlog.get_logger()

# Paths
ASSETS_DIR = Path(os.getenv("ASSET_PATH", "./data/assets"))
EXPORTS_DIR = Path(os.getenv("EXPORT_PATH", "./data/exports"))

# Ensure directories exist
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_asset_id() -> str:
    """Generate a unique asset ID."""
    return str(uuid.uuid4())[:12]


def get_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def parse_canvas_size(canvas: str) -> Tuple[int, int]:
    """Parse canvas size string like '1080x1920' into (width, height)."""
    match = re.match(r"(\d+)x(\d+)", canvas)
    if not match:
        raise ValueError(f"Invalid canvas size format: {canvas}")
    return int(match.group(1)), int(match.group(2))


def percentage_to_pixels(
    x_pct: float, y_pct: float, width_pct: float, height_pct: float,
    canvas_width: int, canvas_height: int
) -> Tuple[int, int, int, int]:
    """Convert percentage-based coordinates to pixel values."""
    x = int(x_pct / 100 * canvas_width)
    y = int(y_pct / 100 * canvas_height)
    width = int(width_pct / 100 * canvas_width)
    height = int(height_pct / 100 * canvas_height)
    return x, y, width, height


def pixels_to_percentage(
    x: int, y: int, width: int, height: int,
    canvas_width: int, canvas_height: int
) -> Tuple[float, float, float, float]:
    """Convert pixel coordinates to percentage values."""
    x_pct = (x / canvas_width) * 100
    y_pct = (y / canvas_height) * 100
    width_pct = (width / canvas_width) * 100
    height_pct = (height / canvas_height) * 100
    return x_pct, y_pct, width_pct, height_pct


def scale_font_size(base_font_size: int, base_height: int, target_height: int) -> int:
    """Scale font size proportionally based on canvas height."""
    scale_factor = target_height / base_height
    return max(8, int(base_font_size * scale_factor))


def extract_dominant_colors(image_path: str, n_colors: int = 3) -> List[str]:
    """
    Extract dominant colors from an image using K-means clustering.
    Returns a list of hex color codes.
    """
    try:
        img = Image.open(image_path).convert("RGBA")
        
        # Resize for faster processing
        img.thumbnail((150, 150))
        
        # Convert to numpy array and filter out transparent pixels
        pixels = np.array(img)
        
        # Handle RGBA images - filter out transparent pixels
        if pixels.shape[2] == 4:
            alpha = pixels[:, :, 3]
            mask = alpha > 128  # Only consider non-transparent pixels
            rgb_pixels = pixels[:, :, :3][mask]
        else:
            rgb_pixels = pixels[:, :, :3].reshape(-1, 3)
        
        if len(rgb_pixels) < n_colors:
            return ["#FFFFFF"]
        
        # K-means clustering
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(rgb_pixels)
        
        # Get cluster centers and sort by frequency
        colors = kmeans.cluster_centers_.astype(int)
        labels, counts = np.unique(kmeans.labels_, return_counts=True)
        sorted_indices = np.argsort(-counts)
        
        # Convert to hex
        hex_colors = []
        for idx in sorted_indices:
            r, g, b = colors[idx]
            hex_colors.append(f"#{r:02x}{g:02x}{b:02x}")
        
        return hex_colors
        
    except Exception as e:
        logger.error("color_extraction_failed", error=str(e))
        return ["#FFFFFF", "#000000", "#CCCCCC"]


def calculate_relative_luminance(color: str) -> float:
    """
    Calculate relative luminance of a color for WCAG contrast calculation.
    Color should be in hex format (#RRGGBB).
    """
    # Remove # and parse
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join([c*2 for c in color])
    
    r = int(color[0:2], 16) / 255
    g = int(color[2:4], 16) / 255
    b = int(color[4:6], 16) / 255
    
    # Apply gamma correction
    def adjust(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    
    r = adjust(r)
    g = adjust(g)
    b = adjust(b)
    
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def calculate_contrast_ratio(color1: str, color2: str) -> float:
    """
    Calculate WCAG contrast ratio between two colors.
    Returns a value between 1 and 21.
    """
    l1 = calculate_relative_luminance(color1)
    l2 = calculate_relative_luminance(color2)
    
    lighter = max(l1, l2)
    darker = min(l1, l2)
    
    return (lighter + 0.05) / (darker + 0.05)


def check_wcag_aa_contrast(text_color: str, bg_color: str, is_large_text: bool = False) -> bool:
    """
    Check if text meets WCAG AA contrast requirements.
    Large text: 3:1 ratio
    Normal text: 4.5:1 ratio
    """
    ratio = calculate_contrast_ratio(text_color, bg_color)
    threshold = 3.0 if is_large_text else 4.5
    return ratio >= threshold


def get_suggested_text_color(bg_color: str) -> str:
    """
    Suggest a text color (black or white) that has good contrast with background.
    """
    luminance = calculate_relative_luminance(bg_color)
    return "#000000" if luminance > 0.5 else "#FFFFFF"


def trim_transparent_borders(image: Image.Image) -> Image.Image:
    """
    Trim transparent borders from an RGBA image.
    """
    if image.mode != "RGBA":
        return image
    
    # Get alpha channel
    alpha = np.array(image.split()[3])
    
    # Find bounding box of non-transparent pixels
    rows = np.any(alpha > 0, axis=1)
    cols = np.any(alpha > 0, axis=0)
    
    if not rows.any() or not cols.any():
        return image
    
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    
    return image.crop((cmin, rmin, cmax + 1, rmax + 1))


def is_valid_image_mime(mime_type: str) -> bool:
    """Check if MIME type is an allowed image type."""
    allowed_types = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp"
    ]
    return mime_type in allowed_types


def sanitize_text_for_llm(text: str) -> str:
    """Sanitize user-provided text before passing to LLM."""
    # Remove potential injection patterns
    text = re.sub(r'\{[^}]*\}', '', text)  # Remove template-like patterns
    text = re.sub(r'```[^`]*```', '', text)  # Remove code blocks
    text = re.sub(r'<[^>]*>', '', text)  # Remove HTML-like tags
    text = text.strip()
    # Limit length
    return text[:500]


def create_safe_filename(original: str) -> str:
    """Create a safe filename from an original filename."""
    # Get extension
    ext = Path(original).suffix.lower()
    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]:
        ext = ".png"
    
    # Generate safe name
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', Path(original).stem)[:50]
    return f"{safe_name}_{generate_asset_id()}{ext}"
