"""
Renderer Service for generating creative images from layouts.
Uses Pillow for image composition and text rendering.
"""
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import structlog

from app.models import Layout, LayoutElement
from app.utils import (
    ASSETS_DIR, EXPORTS_DIR, parse_canvas_size, 
    percentage_to_pixels, scale_font_size, generate_asset_id
)

logger = structlog.get_logger()

# Font configuration
DEFAULT_FONT = "arial.ttf"
FALLBACK_FONTS = ["Arial", "DejaVuSans.ttf", "FreeSans.ttf", "Helvetica"]


class RendererService:
    """Service for rendering layouts to images."""
    
    def __init__(self):
        self.font_cache: Dict[str, ImageFont.FreeTypeFont] = {}
        self.default_font = self._load_default_font()
    
    def _load_default_font(self) -> Optional[ImageFont.FreeTypeFont]:
        """Load the default font, trying multiple options."""
        for font_name in [DEFAULT_FONT] + FALLBACK_FONTS:
            try:
                return ImageFont.truetype(font_name, 24)
            except (IOError, OSError):
                continue
        
        logger.warning("no_truetype_font_available", message="Using default bitmap font")
        return ImageFont.load_default()
    
    def _get_font(self, size: int, font_family: str = None) -> ImageFont.FreeTypeFont:
        """Get a font at the specified size, using cache."""
        font_name = font_family or DEFAULT_FONT
        cache_key = f"{font_name}_{size}"
        
        if cache_key in self.font_cache:
            return self.font_cache[cache_key]
        
        try:
            font = ImageFont.truetype(font_name, size)
        except (IOError, OSError):
            # Try fallback fonts
            for fallback in FALLBACK_FONTS:
                try:
                    font = ImageFont.truetype(fallback, size)
                    break
                except (IOError, OSError):
                    continue
            else:
                # Last resort: use default font scaled
                font = ImageFont.load_default()
        
        self.font_cache[cache_key] = font
        return font
    
    def render_layout(
        self,
        layout: Layout,
        assets_map: Dict[str, str],
        canvas_size: str = "1080x1920",
        output_path: Optional[str] = None
    ) -> str:
        """
        Render a layout to an image.
        
        Args:
            layout: Layout to render
            assets_map: Map of asset IDs to file paths
            canvas_size: Target canvas size (e.g., "1080x1920")
            output_path: Optional output path. If None, auto-generated.
            
        Returns:
            Path to rendered image
        """
        canvas_width, canvas_height = parse_canvas_size(canvas_size)
        
        # Create canvas
        canvas = Image.new("RGBA", (canvas_width, canvas_height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        
        # Sort elements by z-index
        elements = sorted(
            [e.model_dump() if hasattr(e, 'model_dump') else e for e in layout.elements],
            key=lambda x: x.get("z", 0)
        )
        
        # Render each element
        for elem in elements:
            elem_type = elem.get("type")
            
            if elem_type == "background":
                self._render_background(canvas, draw, elem)
            elif elem_type == "packshot":
                self._render_image_element(canvas, elem, assets_map, canvas_width, canvas_height)
            elif elem_type == "logo":
                self._render_image_element(canvas, elem, assets_map, canvas_width, canvas_height)
            elif elem_type in ["headline", "subhead"]:
                self._render_text_element(canvas, draw, elem, canvas_width, canvas_height)
            elif elem_type == "tesco_tag":
                self._render_tesco_tag(canvas, draw, elem, canvas_width, canvas_height)
            elif elem_type == "value_tile":
                self._render_value_tile(canvas, draw, elem, canvas_width, canvas_height)
            elif elem_type == "drinkaware":
                self._render_drinkaware(canvas, draw, elem, canvas_width, canvas_height)
        
        # Generate output path if not provided
        if output_path is None:
            output_path = EXPORTS_DIR / f"render_{layout.id}_{generate_asset_id()}.png"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to RGB if saving as JPEG
        if output_path.suffix.lower() in [".jpg", ".jpeg"]:
            canvas = canvas.convert("RGB")
        
        canvas.save(str(output_path), optimize=True)
        
        logger.info("layout_rendered", 
                   layout_id=layout.id, 
                   size=canvas_size, 
                   output=str(output_path))
        
        return str(output_path)
    
    def _render_background(
        self, 
        canvas: Image.Image, 
        draw: ImageDraw.Draw, 
        elem: Dict
    ) -> None:
        """Render background color."""
        color = elem.get("color", "#FFFFFF")
        # Convert hex to RGB tuple
        color = self._hex_to_rgb(color)
        draw.rectangle([0, 0, canvas.width, canvas.height], fill=color)
    
    def _render_image_element(
        self,
        canvas: Image.Image,
        elem: Dict,
        assets_map: Dict[str, str],
        canvas_width: int,
        canvas_height: int
    ) -> None:
        """Render an image element (packshot, logo)."""
        asset_id = elem.get("asset", "")
        asset_path = None
        
        logger.debug("render_image_element", asset_id=asset_id, assets_map_keys=list(assets_map.keys())[:5])
        
        # Try multiple ways to find the asset
        # 1. Direct lookup in assets_map
        if asset_id in assets_map:
            asset_path = assets_map[asset_id]
            logger.debug("asset_found_direct", asset_id=asset_id, path=asset_path)
        # 2. Try with /assets/ prefix stripped
        elif asset_id.startswith("/assets/"):
            stripped = asset_id.replace("/assets/", "")
            if stripped in assets_map:
                asset_path = assets_map[stripped]
                logger.debug("asset_found_stripped", asset_id=asset_id, stripped=stripped, path=asset_path)
            else:
                # Direct path in assets dir
                asset_path = ASSETS_DIR / stripped
                logger.debug("asset_trying_direct_path", asset_id=asset_id, path=str(asset_path))
        # 3. Try as filename in ASSETS_DIR
        elif not asset_path:
            asset_path = ASSETS_DIR / f"{asset_id}.png"
            if not Path(asset_path).exists():
                asset_path = ASSETS_DIR / f"{asset_id}_cleaned.png"
                if not Path(asset_path).exists():
                    asset_path = ASSETS_DIR / asset_id
        
        # Ensure it's a Path object
        if isinstance(asset_path, str):
            asset_path = Path(asset_path)
            
        # If path starts with /assets/, look in ASSETS_DIR
        if str(asset_path).startswith("/assets/"):
            asset_path = ASSETS_DIR / str(asset_path).replace("/assets/", "")
        
        # Last resort: scan ASSETS_DIR for matching filename
        if not asset_path or not Path(asset_path).exists():
            # Try to find file by scanning assets directory
            asset_filename = Path(asset_id).name if asset_id else ""
            if asset_filename:
                for f in ASSETS_DIR.glob("*"):
                    if f.name == asset_filename or f.stem == asset_filename.replace('.png', '').replace('.jpg', ''):
                        asset_path = f
                        logger.debug("asset_found_by_scan", asset_id=asset_id, path=str(asset_path))
                        break
        
        if not asset_path or not Path(asset_path).exists():
            logger.warning("asset_not_found", asset_id=asset_id, path=str(asset_path), assets_dir=str(ASSETS_DIR))
            return
        
        try:
            # Load and resize asset
            asset = Image.open(asset_path).convert("RGBA")
            
            # Calculate position and size
            x, y, width, height = percentage_to_pixels(
                elem.get("x", 0), elem.get("y", 0),
                elem.get("width", 10), elem.get("height", 10),
                canvas_width, canvas_height
            )
            
            # Resize asset to fit
            asset = asset.resize((max(1, width), max(1, height)), Image.Resampling.LANCZOS)
            
            # Paste onto canvas (with alpha compositing)
            canvas.paste(asset, (x, y), asset)
            
            logger.debug("rendered_image", asset_id=asset_id, path=str(asset_path), x=x, y=y)
            
        except Exception as e:
            logger.error("render_image_failed", asset_id=asset_id, error=str(e))
    
    def _render_text_element(
        self,
        canvas: Image.Image,
        draw: ImageDraw.Draw,
        elem: Dict,
        canvas_width: int,
        canvas_height: int
    ) -> None:
        """Render a text element (headline, subhead)."""
        text = elem.get("text", "")
        if not text:
            return
        
        # Calculate position and size
        x, y, width, height = percentage_to_pixels(
            elem.get("x", 0), elem.get("y", 0),
            elem.get("width", 50), elem.get("height", 10),
            canvas_width, canvas_height
        )
        
        # Scale font size for current canvas
        base_font_size = elem.get("font_size", 24)
        font_size = scale_font_size(base_font_size, 1920, canvas_height)
        
        font = self._get_font(font_size, elem.get("font_family"))
        color = self._hex_to_rgb(elem.get("color", "#000000"))
        
        # Simple text wrapping
        wrapped_text = self._wrap_text(text, font, width)
        
        # Draw text
        draw.text((x, y), wrapped_text, fill=color, font=font)
    
    def _render_tesco_tag(
        self,
        canvas: Image.Image,
        draw: ImageDraw.Draw,
        elem: Dict,
        canvas_width: int,
        canvas_height: int
    ) -> None:
        """Render Tesco tag element."""
        text = elem.get("text", "Available at Tesco")
        
        x, y, width, height = percentage_to_pixels(
            elem.get("x", 0), elem.get("y", 0),
            elem.get("width", 20), elem.get("height", 5),
            canvas_width, canvas_height
        )
        
        # Tesco red background
        tesco_red = (0, 85, 166)  # Tesco blue actually
        draw.rectangle([x, y, x + width, y + height], fill=tesco_red)
        
        # White text
        font_size = max(12, int(height * 0.6))
        font = self._get_font(font_size)
        
        # Center text in box
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = x + (width - text_width) // 2
        text_y = y + (height - text_height) // 2
        
        draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
    
    def _render_value_tile(
        self,
        canvas: Image.Image,
        draw: ImageDraw.Draw,
        elem: Dict,
        canvas_width: int,
        canvas_height: int
    ) -> None:
        """Render value tile element."""
        x, y, width, height = percentage_to_pixels(
            elem.get("x", 0), elem.get("y", 0),
            elem.get("width", 15), elem.get("height", 8),
            canvas_width, canvas_height
        )
        
        # Yellow background (common for value tiles)
        draw.rectangle([x, y, x + width, y + height], fill=(255, 200, 0))
        
        # Add placeholder text if provided
        text = elem.get("text", "")
        if text:
            font_size = max(12, int(height * 0.5))
            font = self._get_font(font_size)
            draw.text((x + 5, y + 5), text, fill=(0, 0, 0), font=font)
    
    def _render_drinkaware(
        self,
        canvas: Image.Image,
        draw: ImageDraw.Draw,
        elem: Dict,
        canvas_width: int,
        canvas_height: int
    ) -> None:
        """Render Drinkaware lock-up."""
        x, y, width, height = percentage_to_pixels(
            elem.get("x", 0), elem.get("y", 0),
            elem.get("width", 30), elem.get("height", 3),
            canvas_width, canvas_height
        )
        
        color = self._hex_to_rgb(elem.get("color", "#000000"))
        text = "drinkaware.co.uk"
        
        # Draw text
        font_size = max(10, int(height * 0.7))
        font = self._get_font(font_size)
        
        # Center text
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_x = x + (width - text_width) // 2
        
        draw.text((text_x, y), text, fill=color, font=font)
    
    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
        """Simple text wrapping based on available width."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = font.getbbox(test_line)
            line_width = bbox[2] - bbox[0]
            
            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return "\n".join(lines)
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join([c*2 for c in hex_color])
        
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16)
        )
    
    def reformat_layout_for_size(
        self,
        layout: Layout,
        source_size: str,
        target_size: str
    ) -> Layout:
        """
        Reformat a layout for a different canvas size.
        Applies proportional scaling and simple reflow heuristics.
        """
        source_w, source_h = parse_canvas_size(source_size)
        target_w, target_h = parse_canvas_size(target_size)
        
        source_aspect = source_w / source_h
        target_aspect = target_w / target_h
        
        new_elements = []
        
        for elem in layout.elements:
            elem_dict = elem.model_dump() if hasattr(elem, 'model_dump') else elem.copy()
            
            if elem_dict.get("type") == "background":
                new_elements.append(elem_dict)
                continue
            
            # Apply transformation heuristics
            if target_aspect > source_aspect:
                # Target is wider (landscape-ish)
                elem_dict = self._transform_for_landscape(elem_dict, source_aspect, target_aspect)
            elif target_aspect < source_aspect:
                # Target is taller (portrait-ish)
                elem_dict = self._transform_for_portrait(elem_dict, source_aspect, target_aspect)
            
            # Scale font sizes
            if elem_dict.get("font_size"):
                elem_dict["font_size"] = scale_font_size(
                    elem_dict["font_size"], source_h, target_h
                )
            
            new_elements.append(elem_dict)
        
        return Layout(
            id=f"{layout.id}_{target_size.replace('x', '_')}",
            score=layout.score,
            elements=[LayoutElement(**e) for e in new_elements]
        )
    
    def _transform_for_landscape(self, elem: Dict, source_aspect: float, target_aspect: float) -> Dict:
        """Transform element for landscape format."""
        elem_type = elem.get("type")
        
        if elem_type == "packshot":
            # Center packshot horizontally
            elem["x"] = (100 - elem.get("width", 40)) / 2
            # Adjust height to fit
            if elem.get("height", 0) > 60:
                elem["height"] = 60
                elem["y"] = 10
        
        elif elem_type in ["headline", "subhead"]:
            # Move text to the side of packshot if there's room
            elem["x"] = 55
            elem["width"] = 40
        
        return elem
    
    def _transform_for_portrait(self, elem: Dict, source_aspect: float, target_aspect: float) -> Dict:
        """Transform element for portrait format."""
        elem_type = elem.get("type")
        
        if elem_type == "packshot":
            # Center packshot vertically if moving from landscape
            current_y = elem.get("y", 20)
            if current_y < 15:
                elem["y"] = 20
        
        return elem


# Singleton instance
renderer_service = RendererService()
