"""
Adaptive Resizer - Intelligent multi-format layout adaptation.
Converts designs into compliant Story, Square, and Landscape formats
without distortion while maintaining visual hierarchy and compliance.
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import structlog
import copy

from app.models import Layout, LayoutElement
from app.utils import parse_canvas_size

logger = structlog.get_logger()


# ============================================================================
# FORMAT CONFIGURATIONS
# ============================================================================

@dataclass
class FormatConfig:
    """Configuration for a target format."""
    name: str
    width: int
    height: int
    aspect_ratio: float
    platform: str
    safe_zone_top_pct: float = 0
    safe_zone_bottom_pct: float = 0
    safe_zone_left_pct: float = 0
    safe_zone_right_pct: float = 0


# Supported export formats
FORMATS = {
    # Social Media - Stories
    "1080x1920": FormatConfig(
        name="Instagram/Facebook Story",
        width=1080, height=1920,
        aspect_ratio=9/16,
        platform="stories",
        safe_zone_top_pct=10.4,  # 200px for Stories UI
        safe_zone_bottom_pct=13.0  # 250px for CTA
    ),
    # Social Media - Square
    "1080x1080": FormatConfig(
        name="Instagram/Facebook Square",
        width=1080, height=1080,
        aspect_ratio=1.0,
        platform="feed"
    ),
    # Social Media - Landscape
    "1200x628": FormatConfig(
        name="Facebook Feed Landscape",
        width=1200, height=628,
        aspect_ratio=1200/628,
        platform="facebook"
    ),
    # Display Ads
    "300x250": FormatConfig(
        name="Medium Rectangle",
        width=300, height=250,
        aspect_ratio=300/250,
        platform="display"
    ),
    "728x90": FormatConfig(
        name="Leaderboard",
        width=728, height=90,
        aspect_ratio=728/90,
        platform="display"
    ),
    "160x600": FormatConfig(
        name="Wide Skyscraper",
        width=160, height=600,
        aspect_ratio=160/600,
        platform="display"
    ),
    # In-store
    "2480x3508": FormatConfig(
        name="A4 Portrait (300 DPI)",
        width=2480, height=3508,
        aspect_ratio=2480/3508,
        platform="in_store"
    ),
    "3508x2480": FormatConfig(
        name="A4 Landscape (300 DPI)",
        width=3508, height=2480,
        aspect_ratio=3508/2480,
        platform="in_store"
    )
}


class LayoutStrategy(Enum):
    """Strategy for adapting layout to new format."""
    SCALE_FIT = "scale_fit"  # Scale entire layout to fit
    REFLOW = "reflow"  # Reposition elements intelligently
    CROP_CENTER = "crop_center"  # Center crop
    STACK = "stack"  # Stack elements vertically
    SIDE_BY_SIDE = "side_by_side"  # Arrange side by side


class AdaptiveResizer:
    """
    Adaptive Resizer - Intelligent format conversion.
    
    Converts layouts between formats while:
    - Maintaining visual hierarchy
    - Respecting safe zones
    - Preserving aspect ratios of images
    - Ensuring text readability
    - Keeping compliance elements
    """
    
    def __init__(self):
        self.formats = FORMATS
    
    def get_available_formats(self) -> Dict[str, FormatConfig]:
        """Get all available export formats."""
        return self.formats
    
    def determine_strategy(
        self,
        source_format: str,
        target_format: str
    ) -> LayoutStrategy:
        """
        Determine the best adaptation strategy based on format change.
        """
        source = self.formats.get(source_format)
        target = self.formats.get(target_format)
        
        if not source or not target:
            return LayoutStrategy.SCALE_FIT
        
        source_ar = source.aspect_ratio
        target_ar = target.aspect_ratio
        
        # Similar aspect ratios - simple scale
        if abs(source_ar - target_ar) < 0.1:
            return LayoutStrategy.SCALE_FIT
        
        # Portrait to landscape - need to reflow
        if source_ar < 1 and target_ar > 1:
            return LayoutStrategy.REFLOW
        
        # Landscape to portrait - stack elements
        if source_ar > 1 and target_ar < 1:
            return LayoutStrategy.STACK
        
        # Extreme aspect ratio (banner) - reflow
        if target_ar > 3 or target_ar < 0.3:
            return LayoutStrategy.REFLOW
        
        return LayoutStrategy.SCALE_FIT
    
    def adapt_layout(
        self,
        layout: Layout,
        source_format: str,
        target_format: str,
        strategy: Optional[LayoutStrategy] = None
    ) -> Layout:
        """
        Adapt a layout from source format to target format.
        
        Args:
            layout: Original layout
            source_format: Source format (e.g., "1080x1920")
            target_format: Target format (e.g., "1080x1080")
            strategy: Optional strategy override
            
        Returns:
            Adapted layout for target format
        """
        if source_format == target_format:
            return layout
        
        if strategy is None:
            strategy = self.determine_strategy(source_format, target_format)
        
        logger.info(
            "adapting_layout",
            layout_id=layout.id,
            source=source_format,
            target=target_format,
            strategy=strategy.value
        )
        
        # Deep copy layout
        adapted = self._deep_copy_layout(layout)
        adapted.id = f"{layout.id}_{target_format}"
        
        source_config = self.formats.get(source_format, FORMATS["1080x1920"])
        target_config = self.formats.get(target_format, FORMATS["1080x1080"])
        
        if strategy == LayoutStrategy.SCALE_FIT:
            adapted = self._scale_fit(adapted, source_config, target_config)
        elif strategy == LayoutStrategy.REFLOW:
            adapted = self._reflow(adapted, source_config, target_config)
        elif strategy == LayoutStrategy.STACK:
            adapted = self._stack(adapted, source_config, target_config)
        elif strategy == LayoutStrategy.CROP_CENTER:
            adapted = self._crop_center(adapted, source_config, target_config)
        elif strategy == LayoutStrategy.SIDE_BY_SIDE:
            adapted = self._side_by_side(adapted, source_config, target_config)
        
        # Apply safe zones for target format
        adapted = self._apply_safe_zones(adapted, target_config)
        
        # Ensure minimum sizes for text
        adapted = self._ensure_text_readability(adapted, target_config)
        
        return adapted
    
    def batch_adapt(
        self,
        layout: Layout,
        source_format: str,
        target_formats: List[str]
    ) -> Dict[str, Layout]:
        """
        Adapt a layout to multiple target formats.
        
        Returns:
            Dictionary mapping format to adapted layout
        """
        results = {}
        
        for target_format in target_formats:
            try:
                adapted = self.adapt_layout(layout, source_format, target_format)
                results[target_format] = adapted
            except Exception as e:
                logger.error(
                    "batch_adapt_failed",
                    layout_id=layout.id,
                    target=target_format,
                    error=str(e)
                )
        
        return results
    
    def _deep_copy_layout(self, layout: Layout) -> Layout:
        """Create a deep copy of a layout."""
        layout_dict = layout.model_dump() if hasattr(layout, 'model_dump') else dict(layout)
        return Layout(**layout_dict)
    
    def _scale_fit(
        self,
        layout: Layout,
        source: FormatConfig,
        target: FormatConfig
    ) -> Layout:
        """
        Scale entire layout to fit target format.
        Maintains relative positions of all elements.
        """
        # Scale factors
        scale_x = target.width / source.width
        scale_y = target.height / source.height
        
        # Use uniform scale to prevent distortion
        uniform_scale = min(scale_x, scale_y)
        
        # Offset to center the scaled layout
        offset_x = (target.width - source.width * uniform_scale) / 2 / target.width * 100
        offset_y = (target.height - source.height * uniform_scale) / 2 / target.height * 100
        
        new_elements = []
        for elem in layout.elements:
            elem_dict = elem.model_dump() if hasattr(elem, 'model_dump') else dict(elem)
            
            if elem_dict.get("type") == "background":
                new_elements.append(LayoutElement(**elem_dict))
                continue
            
            # Scale position and size
            if elem_dict.get("x") is not None:
                elem_dict["x"] = elem_dict["x"] * uniform_scale + offset_x
            if elem_dict.get("y") is not None:
                elem_dict["y"] = elem_dict["y"] * uniform_scale + offset_y
            if elem_dict.get("width") is not None:
                elem_dict["width"] = elem_dict["width"] * uniform_scale
            if elem_dict.get("height") is not None:
                elem_dict["height"] = elem_dict["height"] * uniform_scale
            
            new_elements.append(LayoutElement(**elem_dict))
        
        layout.elements = new_elements
        return layout
    
    def _reflow(
        self,
        layout: Layout,
        source: FormatConfig,
        target: FormatConfig
    ) -> Layout:
        """
        Intelligently reflow elements for different aspect ratio.
        Used for portrait-to-landscape conversions.
        """
        # Categorize elements
        elements_dict = {}
        for elem in layout.elements:
            elem_dict = elem.model_dump() if hasattr(elem, 'model_dump') else dict(elem)
            elem_type = elem_dict.get("type")
            elements_dict[elem_type] = elem_dict
        
        new_elements = []
        
        # Keep background
        if "background" in elements_dict:
            new_elements.append(LayoutElement(**elements_dict["background"]))
        
        # For landscape: arrange left-to-right
        if target.aspect_ratio > 1:
            # Image/packshot on left (40% width)
            if "packshot" in elements_dict:
                packshot = elements_dict["packshot"].copy()
                packshot["x"] = 5
                packshot["y"] = 10
                packshot["width"] = 35
                packshot["height"] = 60
                new_elements.append(LayoutElement(**packshot))
            
            # Text content on right (55% width)
            text_x = 45
            current_y = 15
            
            if "headline" in elements_dict:
                headline = elements_dict["headline"].copy()
                headline["x"] = text_x
                headline["y"] = current_y
                headline["width"] = 50
                headline["height"] = 20
                # Adjust font size for landscape
                if headline.get("font_size"):
                    headline["font_size"] = int(headline["font_size"] * 0.7)
                new_elements.append(LayoutElement(**headline))
                current_y += 25
            
            if "subhead" in elements_dict:
                subhead = elements_dict["subhead"].copy()
                subhead["x"] = text_x
                subhead["y"] = current_y
                subhead["width"] = 50
                subhead["height"] = 15
                if subhead.get("font_size"):
                    subhead["font_size"] = int(subhead["font_size"] * 0.7)
                new_elements.append(LayoutElement(**subhead))
                current_y += 20
            
            # Logo in corner
            if "logo" in elements_dict:
                logo = elements_dict["logo"].copy()
                logo["x"] = text_x
                logo["y"] = 70
                logo["width"] = 15
                logo["height"] = 20
                new_elements.append(LayoutElement(**logo))
            
            # Compliance elements at bottom right
            if "tesco_tag" in elements_dict:
                tag = elements_dict["tesco_tag"].copy()
                tag["x"] = 70
                tag["y"] = 85
                tag["width"] = 25
                tag["height"] = 10
                new_elements.append(LayoutElement(**tag))
            
            if "drinkaware" in elements_dict:
                drinkaware = elements_dict["drinkaware"].copy()
                drinkaware["x"] = 5
                drinkaware["y"] = 85
                drinkaware["width"] = 30
                drinkaware["height"] = 10
                new_elements.append(LayoutElement(**drinkaware))
        
        layout.elements = new_elements
        return layout
    
    def _stack(
        self,
        layout: Layout,
        source: FormatConfig,
        target: FormatConfig
    ) -> Layout:
        """
        Stack elements vertically for narrow/tall formats.
        Used for landscape-to-portrait conversions.
        """
        elements_dict = {}
        for elem in layout.elements:
            elem_dict = elem.model_dump() if hasattr(elem, 'model_dump') else dict(elem)
            elem_type = elem_dict.get("type")
            elements_dict[elem_type] = elem_dict
        
        new_elements = []
        
        # Background
        if "background" in elements_dict:
            new_elements.append(LayoutElement(**elements_dict["background"]))
        
        current_y = 12  # Start below safe zone
        
        # Logo at top
        if "logo" in elements_dict:
            logo = elements_dict["logo"].copy()
            logo["x"] = 10
            logo["y"] = current_y
            logo["width"] = 20
            logo["height"] = 8
            new_elements.append(LayoutElement(**logo))
            current_y += 10
        
        # Headline
        if "headline" in elements_dict:
            headline = elements_dict["headline"].copy()
            headline["x"] = 10
            headline["y"] = current_y
            headline["width"] = 80
            headline["height"] = 12
            new_elements.append(LayoutElement(**headline))
            current_y += 14
        
        # Packshot (large, centered)
        if "packshot" in elements_dict:
            packshot = elements_dict["packshot"].copy()
            packshot["x"] = 15
            packshot["y"] = current_y
            packshot["width"] = 70
            packshot["height"] = 40
            new_elements.append(LayoutElement(**packshot))
            current_y += 42
        
        # Subhead
        if "subhead" in elements_dict:
            subhead = elements_dict["subhead"].copy()
            subhead["x"] = 10
            subhead["y"] = current_y
            subhead["width"] = 80
            subhead["height"] = 8
            new_elements.append(LayoutElement(**subhead))
            current_y += 10
        
        # Tesco tag
        if "tesco_tag" in elements_dict:
            tag = elements_dict["tesco_tag"].copy()
            tag["x"] = 5
            tag["y"] = 80
            tag["width"] = 30
            tag["height"] = 5
            new_elements.append(LayoutElement(**tag))
        
        # Drinkaware at bottom
        if "drinkaware" in elements_dict:
            drinkaware = elements_dict["drinkaware"].copy()
            drinkaware["x"] = 35
            drinkaware["y"] = 92
            drinkaware["width"] = 30
            drinkaware["height"] = 3
            new_elements.append(LayoutElement(**drinkaware))
        
        layout.elements = new_elements
        return layout
    
    def _crop_center(
        self,
        layout: Layout,
        source: FormatConfig,
        target: FormatConfig
    ) -> Layout:
        """
        Center crop the layout for the target format.
        Simple scaling with centered viewport.
        """
        # Calculate crop area
        source_ar = source.aspect_ratio
        target_ar = target.aspect_ratio
        
        if source_ar > target_ar:
            # Source is wider, crop sides
            new_width_pct = (target_ar / source_ar) * 100
            offset_x = (100 - new_width_pct) / 2
            offset_y = 0
            scale_x = 100 / new_width_pct
            scale_y = 1
        else:
            # Source is taller, crop top/bottom
            new_height_pct = (source_ar / target_ar) * 100
            offset_x = 0
            offset_y = (100 - new_height_pct) / 2
            scale_x = 1
            scale_y = 100 / new_height_pct
        
        new_elements = []
        for elem in layout.elements:
            elem_dict = elem.model_dump() if hasattr(elem, 'model_dump') else dict(elem)
            
            if elem_dict.get("type") == "background":
                new_elements.append(LayoutElement(**elem_dict))
                continue
            
            if elem_dict.get("x") is not None:
                elem_dict["x"] = (elem_dict["x"] - offset_x) * scale_x
            if elem_dict.get("y") is not None:
                elem_dict["y"] = (elem_dict["y"] - offset_y) * scale_y
            if elem_dict.get("width") is not None:
                elem_dict["width"] = elem_dict["width"] * scale_x
            if elem_dict.get("height") is not None:
                elem_dict["height"] = elem_dict["height"] * scale_y
            
            new_elements.append(LayoutElement(**elem_dict))
        
        layout.elements = new_elements
        return layout
    
    def _side_by_side(
        self,
        layout: Layout,
        source: FormatConfig,
        target: FormatConfig
    ) -> Layout:
        """
        Arrange elements side by side for wide formats.
        """
        # Similar to reflow but optimized for very wide formats
        return self._reflow(layout, source, target)
    
    def _apply_safe_zones(
        self,
        layout: Layout,
        target: FormatConfig
    ) -> Layout:
        """
        Ensure elements respect safe zones in target format.
        """
        if target.safe_zone_top_pct == 0 and target.safe_zone_bottom_pct == 0:
            return layout
        
        safe_top = target.safe_zone_top_pct
        safe_bottom = 100 - target.safe_zone_bottom_pct
        
        new_elements = []
        for elem in layout.elements:
            elem_dict = elem.model_dump() if hasattr(elem, 'model_dump') else dict(elem)
            
            if elem_dict.get("type") in ["background", "drinkaware"]:
                new_elements.append(LayoutElement(**elem_dict))
                continue
            
            y = elem_dict.get("y", 0)
            h = elem_dict.get("height", 0)
            
            # Push elements out of top safe zone
            if y < safe_top:
                elem_dict["y"] = safe_top
            
            # Push elements out of bottom safe zone
            if y + h > safe_bottom:
                elem_dict["y"] = safe_bottom - h
            
            new_elements.append(LayoutElement(**elem_dict))
        
        layout.elements = new_elements
        return layout
    
    def _ensure_text_readability(
        self,
        layout: Layout,
        target: FormatConfig
    ) -> Layout:
        """
        Ensure text is readable in target format.
        Adjusts font sizes based on canvas size.
        """
        # Minimum font sizes based on canvas height
        min_headline_size = max(20, int(target.height * 0.025))
        min_subhead_size = max(14, int(target.height * 0.015))
        
        new_elements = []
        for elem in layout.elements:
            elem_dict = elem.model_dump() if hasattr(elem, 'model_dump') else dict(elem)
            elem_type = elem_dict.get("type")
            
            if elem_type == "headline":
                if elem_dict.get("font_size", 0) < min_headline_size:
                    elem_dict["font_size"] = min_headline_size
            elif elem_type == "subhead":
                if elem_dict.get("font_size", 0) < min_subhead_size:
                    elem_dict["font_size"] = min_subhead_size
            
            new_elements.append(LayoutElement(**elem_dict))
        
        layout.elements = new_elements
        return layout


# Singleton instance
adaptive_resizer = AdaptiveResizer()
