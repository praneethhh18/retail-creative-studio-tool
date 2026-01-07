"""
Brand Guardian Engine - Advanced compliance and brand identity protection.
Ensures all creatives follow brand identity, logo usage rules, content safety zones,
minimum font contrast, and retailer guidelines.
"""
import colorsys
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

from app.models import Layout, LayoutElement, ValidationIssue, IssueSeverity
from app.utils import (
    parse_canvas_size, percentage_to_pixels, calculate_contrast_ratio,
    check_wcag_aa_contrast
)

logger = structlog.get_logger()


# ============================================================================
# BRAND CONFIGURATION
# ============================================================================

@dataclass
class BrandConfig:
    """Brand-specific configuration for validation."""
    name: str
    primary_colors: List[str]
    secondary_colors: List[str]
    logo_min_size_pct: float = 5.0  # Minimum logo size as % of canvas
    logo_max_size_pct: float = 25.0  # Maximum logo size as % of canvas
    logo_clear_space_pct: float = 2.0  # Clear space around logo
    min_font_size_px: int = 20
    allowed_fonts: List[str] = None
    disallowed_elements: List[str] = None
    requires_tesco_tag: bool = True
    requires_value_tile: bool = False


# Retailer-specific rules
RETAILER_RULES = {
    "tesco": {
        "allowed_tesco_tags": [
            "Only at Tesco",
            "Available at Tesco", 
            "Selected stores. While stocks last"
        ],
        "safe_zone_top_pct": 10.4,  # 200px/1920px
        "safe_zone_bottom_pct": 13.0,  # 250px/1920px
        "min_font_size": 20,
        "drinkaware_min_height": 20,
        "drinkaware_colors": ["#000000", "#FFFFFF"],
        "requires_tesco_tag": True
    },
    "sainsburys": {
        "safe_zone_top_pct": 8.0,
        "safe_zone_bottom_pct": 10.0,
        "min_font_size": 18,
        "requires_brand_tag": True
    },
    "asda": {
        "safe_zone_top_pct": 10.0,
        "safe_zone_bottom_pct": 12.0,
        "min_font_size": 20
    }
}


class BrandGuardian:
    """
    Brand Guardian Engine - Comprehensive brand and compliance validation.
    """
    
    def __init__(self):
        self.brand_configs: Dict[str, BrandConfig] = {}
        self.active_retailer = "tesco"
    
    def register_brand(self, brand_id: str, config: BrandConfig) -> None:
        """Register a brand configuration."""
        self.brand_configs[brand_id] = config
        logger.info("brand_registered", brand_id=brand_id, name=config.name)
    
    def set_retailer(self, retailer: str) -> None:
        """Set the active retailer for validation rules."""
        if retailer.lower() in RETAILER_RULES:
            self.active_retailer = retailer.lower()
        else:
            logger.warning("unknown_retailer", retailer=retailer, using="tesco")
            self.active_retailer = "tesco"
    
    def validate_brand_identity(
        self,
        layout: Layout,
        brand_colors: List[str],
        canvas_size: str = "1080x1920"
    ) -> List[ValidationIssue]:
        """
        Validate brand identity consistency.
        Checks:
        - Color palette consistency
        - Logo sizing and placement
        - Clear space around logo
        - Font consistency
        """
        issues = []
        canvas_width, canvas_height = parse_canvas_size(canvas_size)
        elements = [e.model_dump() if hasattr(e, 'model_dump') else e for e in layout.elements]
        
        # Check color palette consistency
        issues.extend(self._validate_color_palette(elements, brand_colors))
        
        # Check logo rules
        issues.extend(self._validate_logo_rules(elements, canvas_width, canvas_height))
        
        # Check clear space around important elements
        issues.extend(self._validate_clear_space(elements, canvas_width, canvas_height))
        
        return issues
    
    def validate_visual_quality(
        self,
        layout: Layout,
        canvas_size: str = "1080x1920"
    ) -> List[ValidationIssue]:
        """
        Validate visual quality and aesthetics.
        Checks:
        - WCAG contrast compliance
        - Visual hierarchy
        - Element spacing
        - Layout balance
        """
        issues = []
        canvas_width, canvas_height = parse_canvas_size(canvas_size)
        elements = [e.model_dump() if hasattr(e, 'model_dump') else e for e in layout.elements]
        
        # Check WCAG contrast for all text
        issues.extend(self._validate_text_contrast(elements))
        
        # Check visual hierarchy
        issues.extend(self._validate_visual_hierarchy(elements))
        
        # Check element spacing
        issues.extend(self._validate_spacing(elements, canvas_width, canvas_height))
        
        # Check layout balance
        issues.extend(self._validate_layout_balance(elements, canvas_width, canvas_height))
        
        return issues
    
    def validate_retailer_compliance(
        self,
        layout: Layout,
        retailer: str = "tesco",
        is_alcohol: bool = False,
        channel: str = "stories",
        canvas_size: str = "1080x1920"
    ) -> List[ValidationIssue]:
        """
        Validate retailer-specific compliance rules.
        """
        issues = []
        self.set_retailer(retailer)
        rules = RETAILER_RULES.get(self.active_retailer, RETAILER_RULES["tesco"])
        canvas_width, canvas_height = parse_canvas_size(canvas_size)
        elements = [e.model_dump() if hasattr(e, 'model_dump') else e for e in layout.elements]
        
        # Check safe zones for Stories
        if channel == "stories":
            issues.extend(self._validate_safe_zones(
                elements, rules, canvas_width, canvas_height
            ))
        
        # Check required elements
        issues.extend(self._validate_required_elements(elements, rules, is_alcohol))
        
        # Check alcohol-specific rules
        if is_alcohol:
            issues.extend(self._validate_alcohol_compliance(
                elements, rules, canvas_height
            ))
        
        return issues
    
    def _validate_color_palette(
        self,
        elements: List[Dict],
        brand_colors: List[str]
    ) -> List[ValidationIssue]:
        """Check if colors used match brand palette."""
        issues = []
        
        if not brand_colors:
            return issues
        
        brand_colors_normalized = [c.upper() for c in brand_colors]
        
        for elem in elements:
            elem_color = elem.get("color", "")
            if not elem_color or elem.get("type") == "background":
                continue
            
            elem_color_upper = elem_color.upper()
            
            # Check if color is in brand palette (allow neutrals)
            neutrals = ["#000000", "#FFFFFF", "#000", "#FFF", "#333333", "#666666", "#999999"]
            if (elem_color_upper not in brand_colors_normalized and 
                elem_color_upper not in [n.upper() for n in neutrals]):
                
                # Find closest brand color
                closest = self._find_closest_color(elem_color, brand_colors)
                
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARN,
                    code="BRAND_COLOR_MISMATCH",
                    message=f"Color {elem_color} in {elem.get('type')} is not in brand palette",
                    fix_suggestion=f"Consider using brand color {closest}",
                    element_id=elem.get("id")
                ))
        
        return issues
    
    def _validate_logo_rules(
        self,
        elements: List[Dict],
        canvas_width: int,
        canvas_height: int
    ) -> List[ValidationIssue]:
        """Validate logo sizing and placement rules."""
        issues = []
        
        logos = [e for e in elements if e.get("type") == "logo"]
        
        for logo in logos:
            # Check minimum size
            width_pct = logo.get("width", 0)
            height_pct = logo.get("height", 0)
            
            # Logo should be at least 5% of canvas
            if width_pct < 5 or height_pct < 3:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARN,
                    code="LOGO_TOO_SMALL",
                    message=f"Logo is too small ({width_pct}%x{height_pct}%). Minimum 5% width recommended.",
                    fix_suggestion="Increase logo size for better visibility",
                    element_id=logo.get("id")
                ))
            
            # Logo should not be too large
            if width_pct > 30 or height_pct > 20:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARN,
                    code="LOGO_TOO_LARGE",
                    message=f"Logo may be too large ({width_pct}%x{height_pct}%)",
                    fix_suggestion="Consider reducing logo size for better balance",
                    element_id=logo.get("id")
                ))
        
        return issues
    
    def _validate_clear_space(
        self,
        elements: List[Dict],
        canvas_width: int,
        canvas_height: int
    ) -> List[ValidationIssue]:
        """Check clear space around important elements."""
        issues = []
        
        # Find logo and check clear space
        logos = [e for e in elements if e.get("type") == "logo"]
        
        for logo in logos:
            logo_box = self._get_element_box(logo, canvas_width, canvas_height)
            clear_space = canvas_width * 0.02  # 2% clear space
            
            for elem in elements:
                if elem.get("type") in ["logo", "background"]:
                    continue
                
                elem_box = self._get_element_box(elem, canvas_width, canvas_height)
                
                if self._boxes_too_close(logo_box, elem_box, clear_space):
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.WARN,
                        code="LOGO_CLEAR_SPACE",
                        message=f"Logo needs more clear space from {elem.get('type')}",
                        fix_suggestion="Increase spacing between logo and other elements",
                        element_id=elem.get("id")
                    ))
        
        return issues
    
    def _validate_text_contrast(self, elements: List[Dict]) -> List[ValidationIssue]:
        """Validate WCAG AA contrast for text elements."""
        issues = []
        
        # Find background color
        bg_color = "#FFFFFF"
        for elem in elements:
            if elem.get("type") == "background":
                bg_color = elem.get("color", "#FFFFFF")
                break
        
        text_elements = [e for e in elements if e.get("type") in ["headline", "subhead"]]
        
        for text_elem in text_elements:
            text_color = text_elem.get("color", "#000000")
            contrast = calculate_contrast_ratio(text_color, bg_color)
            font_size = text_elem.get("font_size", 16)
            
            # WCAG AA: 4.5:1 for normal text, 3:1 for large text (18pt+)
            required_ratio = 3.0 if font_size >= 24 else 4.5
            
            if contrast < required_ratio:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.HARD,
                    code="WCAG_CONTRAST_FAIL",
                    message=f"Text contrast ratio {contrast:.2f}:1 fails WCAG AA (need {required_ratio}:1)",
                    fix_suggestion=self._suggest_contrast_fix(text_color, bg_color),
                    element_id=text_elem.get("id")
                ))
        
        return issues
    
    def _validate_visual_hierarchy(self, elements: List[Dict]) -> List[ValidationIssue]:
        """Check visual hierarchy (headline > subhead)."""
        issues = []
        
        headline = None
        subhead = None
        
        for elem in elements:
            if elem.get("type") == "headline":
                headline = elem
            elif elem.get("type") == "subhead":
                subhead = elem
        
        if headline and subhead:
            h_size = headline.get("font_size", 48)
            s_size = subhead.get("font_size", 24)
            
            if s_size >= h_size:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARN,
                    code="HIERARCHY_VIOLATION",
                    message="Subhead should be smaller than headline",
                    fix_suggestion=f"Reduce subhead font size below {h_size}px"
                ))
            
            # Recommended ratio is 1.5-2x
            ratio = h_size / s_size if s_size > 0 else 0
            if ratio < 1.2:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARN,
                    code="WEAK_HIERARCHY",
                    message=f"Headline to subhead ratio ({ratio:.1f}x) is too small",
                    fix_suggestion="Increase headline size or decrease subhead for better hierarchy"
                ))
        
        return issues
    
    def _validate_spacing(
        self,
        elements: List[Dict],
        canvas_width: int,
        canvas_height: int
    ) -> List[ValidationIssue]:
        """Check minimum spacing between elements."""
        issues = []
        min_spacing = 10  # pixels
        
        positioned_elements = [
            e for e in elements 
            if e.get("x") is not None and e.get("type") != "background"
        ]
        
        for i, elem1 in enumerate(positioned_elements):
            box1 = self._get_element_box(elem1, canvas_width, canvas_height)
            
            for elem2 in positioned_elements[i+1:]:
                box2 = self._get_element_box(elem2, canvas_width, canvas_height)
                
                if self._boxes_overlap(box1, box2):
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.WARN,
                        code="ELEMENT_OVERLAP",
                        message=f"{elem1.get('type')} overlaps with {elem2.get('type')}",
                        fix_suggestion="Adjust element positions to prevent overlap",
                        element_id=elem1.get("id")
                    ))
        
        return issues
    
    def _validate_layout_balance(
        self,
        elements: List[Dict],
        canvas_width: int,
        canvas_height: int
    ) -> List[ValidationIssue]:
        """Check layout balance (visual weight distribution)."""
        issues = []
        
        # Calculate center of mass for positioned elements
        total_weight = 0
        weighted_x = 0
        weighted_y = 0
        
        for elem in elements:
            if elem.get("x") is None or elem.get("type") == "background":
                continue
            
            x, y, w, h = percentage_to_pixels(
                elem.get("x", 0), elem.get("y", 0),
                elem.get("width", 0), elem.get("height", 0),
                canvas_width, canvas_height
            )
            
            # Weight by area (larger elements have more visual weight)
            weight = w * h
            center_x = x + w / 2
            center_y = y + h / 2
            
            weighted_x += center_x * weight
            weighted_y += center_y * weight
            total_weight += weight
        
        if total_weight > 0:
            balance_x = weighted_x / total_weight / canvas_width * 100
            balance_y = weighted_y / total_weight / canvas_height * 100
            
            # Check horizontal balance (should be near 50%)
            if abs(balance_x - 50) > 25:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARN,
                    code="LAYOUT_UNBALANCED_H",
                    message=f"Layout is horizontally unbalanced (center at {balance_x:.0f}%)",
                    fix_suggestion="Consider redistributing elements for better balance"
                ))
            
            # Vertical balance is less critical but still check extremes
            if balance_y < 20 or balance_y > 80:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARN,
                    code="LAYOUT_UNBALANCED_V",
                    message=f"Layout may be vertically unbalanced (center at {balance_y:.0f}%)",
                    fix_suggestion="Consider adjusting vertical element distribution"
                ))
        
        return issues
    
    def _validate_safe_zones(
        self,
        elements: List[Dict],
        rules: Dict,
        canvas_width: int,
        canvas_height: int
    ) -> List[ValidationIssue]:
        """Validate elements are not in platform safe zones."""
        issues = []
        
        safe_top = rules.get("safe_zone_top_pct", 10.4)
        safe_bottom = rules.get("safe_zone_bottom_pct", 13.0)
        
        safe_top_px = canvas_height * safe_top / 100
        safe_bottom_px = canvas_height * (100 - safe_bottom) / 100
        
        for elem in elements:
            if elem.get("type") in ["background", "drinkaware"]:
                continue
            
            if elem.get("y") is None:
                continue
            
            y_px = elem.get("y", 0) / 100 * canvas_height
            h_px = elem.get("height", 0) / 100 * canvas_height
            
            if y_px < safe_top_px:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.HARD,
                    code="SAFE_ZONE_TOP_VIOLATION",
                    message=f"{elem.get('type')} is in top safe zone (platform UI area)",
                    fix_suggestion=f"Move element below {safe_top:.1f}% from top",
                    element_id=elem.get("id")
                ))
            
            if y_px + h_px > safe_bottom_px:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.HARD,
                    code="SAFE_ZONE_BOTTOM_VIOLATION",
                    message=f"{elem.get('type')} extends into bottom safe zone",
                    fix_suggestion=f"Keep element above {100 - safe_bottom:.1f}% from top",
                    element_id=elem.get("id")
                ))
        
        return issues
    
    def _validate_required_elements(
        self,
        elements: List[Dict],
        rules: Dict,
        is_alcohol: bool
    ) -> List[ValidationIssue]:
        """Check for required elements based on retailer rules."""
        issues = []
        element_types = [e.get("type") for e in elements]
        
        if rules.get("requires_tesco_tag", False):
            if "tesco_tag" not in element_types:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.HARD,
                    code="MISSING_TESCO_TAG",
                    message="Tesco tag is required for this retailer",
                    fix_suggestion="Add 'Available at Tesco' tag element"
                ))
        
        if is_alcohol and "drinkaware" not in element_types:
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="DRINKAWARE_MISSING",
                message="Drinkaware lock-up is required for alcohol campaigns",
                fix_suggestion="Add drinkaware element with black or white color"
            ))
        
        return issues
    
    def _validate_alcohol_compliance(
        self,
        elements: List[Dict],
        rules: Dict,
        canvas_height: int
    ) -> List[ValidationIssue]:
        """Validate alcohol-specific compliance rules."""
        issues = []
        
        drinkaware = None
        for elem in elements:
            if elem.get("type") == "drinkaware":
                drinkaware = elem
                break
        
        if not drinkaware:
            return issues
        
        # Check color
        color = drinkaware.get("color", "").upper()
        allowed_colors = [c.upper() for c in rules.get("drinkaware_colors", ["#000000", "#FFFFFF"])]
        
        if color not in allowed_colors:
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="DRINKAWARE_COLOR_INVALID",
                message=f"Drinkaware color must be black or white, got {color}",
                fix_suggestion="Change drinkaware color to #000000 or #FFFFFF",
                element_id=drinkaware.get("id")
            ))
        
        # Check minimum height
        min_height = rules.get("drinkaware_min_height", 20)
        height_px = drinkaware.get("height", 0) / 100 * canvas_height
        
        if height_px < min_height:
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="DRINKAWARE_TOO_SMALL",
                message=f"Drinkaware height must be at least {min_height}px, currently {height_px:.0f}px",
                fix_suggestion=f"Increase drinkaware height",
                element_id=drinkaware.get("id")
            ))
        
        return issues
    
    # Helper methods
    def _get_element_box(
        self, elem: Dict, canvas_width: int, canvas_height: int
    ) -> Tuple[int, int, int, int]:
        """Get element bounding box in pixels (x1, y1, x2, y2)."""
        x, y, w, h = percentage_to_pixels(
            elem.get("x", 0), elem.get("y", 0),
            elem.get("width", 0), elem.get("height", 0),
            canvas_width, canvas_height
        )
        return (x, y, x + w, y + h)
    
    def _boxes_overlap(
        self, box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]
    ) -> bool:
        """Check if two boxes overlap."""
        return not (
            box1[2] <= box2[0] or  # box1 left of box2
            box1[0] >= box2[2] or  # box1 right of box2
            box1[3] <= box2[1] or  # box1 above box2
            box1[1] >= box2[3]     # box1 below box2
        )
    
    def _boxes_too_close(
        self, box1: Tuple, box2: Tuple, min_distance: float
    ) -> bool:
        """Check if two boxes are too close."""
        # Expand box1 by min_distance
        expanded = (
            box1[0] - min_distance,
            box1[1] - min_distance,
            box1[2] + min_distance,
            box1[3] + min_distance
        )
        return self._boxes_overlap(expanded, box2)
    
    def _find_closest_color(self, color: str, palette: List[str]) -> str:
        """Find the closest color in palette."""
        if not palette:
            return color
        
        def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        def color_distance(c1: str, c2: str) -> float:
            r1, g1, b1 = hex_to_rgb(c1)
            r2, g2, b2 = hex_to_rgb(c2)
            return ((r1-r2)**2 + (g1-g2)**2 + (b1-b2)**2) ** 0.5
        
        return min(palette, key=lambda c: color_distance(color, c))
    
    def _suggest_contrast_fix(self, text_color: str, bg_color: str) -> str:
        """Suggest a color fix for contrast issues."""
        # Simple heuristic: suggest black or white based on background
        def luminance(hex_color: str) -> float:
            hex_color = hex_color.lstrip('#')
            r, g, b = [int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)]
            return 0.299 * r + 0.587 * g + 0.114 * b
        
        bg_lum = luminance(bg_color)
        return "Change text to #000000 (black)" if bg_lum > 0.5 else "Change text to #FFFFFF (white)"


# Singleton instance
brand_guardian = BrandGuardian()
