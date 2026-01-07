"""
Validator Service implementing Appendix B / Tesco rules.
Provides comprehensive validation for retail media creatives.
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog

from app.models import (
    Layout, LayoutElement, ValidationResult, ValidationIssue, IssueSeverity
)
from app.utils import (
    parse_canvas_size, percentage_to_pixels, calculate_contrast_ratio,
    check_wcag_aa_contrast, scale_font_size
)

logger = structlog.get_logger()


# ============================================================================
# CONFIGURATION
# ============================================================================

# Allowed Tesco tag texts
ALLOWED_TESCO_TAGS = [
    "Only at Tesco",
    "Available at Tesco",
    "Selected stores. While stocks last"
]

# Safe zones for Stories (in pixels for 1080x1920)
STORIES_SAFE_ZONE_TOP = 200  # pixels from top
STORIES_SAFE_ZONE_BOTTOM = 250  # pixels from bottom

# Minimum font sizes (in pixels for 1080x1920)
MIN_FONT_SIZE_BRAND = 20  # Brand/Social channels
MIN_FONT_SIZE_SAYS = 12  # SAYS channel override

# Drinkaware minimum height (pixels for 1080x1920)
DRINKAWARE_MIN_HEIGHT = 20
DRINKAWARE_ALLOWED_COLORS = ["#000000", "#FFFFFF", "#000", "#FFF", "#ffffff", "#fff"]

# Safe gap from CTA (pixels)
CTA_SAFE_GAP_DOUBLE_DENSITY = 24
CTA_SAFE_GAP_SINGLE_DENSITY = 12

# WCAG contrast thresholds
WCAG_AA_NORMAL_TEXT = 4.5
WCAG_AA_LARGE_TEXT = 3.0

# Channel configurations
CHANNEL_CONFIG = {
    "facebook": {"min_font_size": 20, "has_safe_zones": False},
    "instagram": {"min_font_size": 20, "has_safe_zones": False},
    "stories": {"min_font_size": 20, "has_safe_zones": True},
    "in_store": {"min_font_size": 20, "has_safe_zones": False},
    "says": {"min_font_size": 12, "has_safe_zones": False}
}


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_tesco_tag(element: Dict[str, Any]) -> Optional[ValidationIssue]:
    """
    Validate Tesco tag text is one of the allowed options.
    HARD FAIL if invalid.
    """
    if element.get("type") != "tesco_tag":
        return None
    
    text = element.get("text", "").strip()
    if text not in ALLOWED_TESCO_TAGS:
        return ValidationIssue(
            severity=IssueSeverity.HARD,
            code="TESCO_TAG_INVALID",
            message=f"Tesco tag text '{text}' is not allowed. Must be one of: {', '.join(ALLOWED_TESCO_TAGS)}",
            fix_suggestion=f"Change text to '{ALLOWED_TESCO_TAGS[1]}'",
            element_id=element.get("id")
        )
    return None


def validate_drinkaware(
    elements: List[Dict[str, Any]], 
    is_alcohol: bool,
    canvas_height: int
) -> List[ValidationIssue]:
    """
    Validate Drinkaware lock-up for alcohol campaigns.
    HARD FAIL if missing or invalid color/size.
    """
    issues = []
    
    if not is_alcohol:
        return issues
    
    # Find drinkaware element
    drinkaware = None
    for elem in elements:
        if elem.get("type") == "drinkaware":
            drinkaware = elem
            break
    
    if not drinkaware:
        issues.append(ValidationIssue(
            severity=IssueSeverity.HARD,
            code="DRINKAWARE_MISSING",
            message="Drinkaware lock-up is required for alcohol campaigns",
            fix_suggestion="Add drinkaware element with black or white color"
        ))
        return issues
    
    # Validate color
    color = drinkaware.get("color", "").upper()
    if color not in [c.upper() for c in DRINKAWARE_ALLOWED_COLORS]:
        issues.append(ValidationIssue(
            severity=IssueSeverity.HARD,
            code="DRINKAWARE_COLOR_INVALID",
            message=f"Drinkaware color must be black (#000000) or white (#FFFFFF), got {color}",
            fix_suggestion="Change drinkaware color to #000000 or #FFFFFF",
            element_id=drinkaware.get("id")
        ))
    
    # Validate height (convert percentage to pixels)
    height_pct = drinkaware.get("height", 0)
    height_px = int(height_pct / 100 * canvas_height)
    
    if height_px < DRINKAWARE_MIN_HEIGHT:
        issues.append(ValidationIssue(
            severity=IssueSeverity.HARD,
            code="DRINKAWARE_TOO_SMALL",
            message=f"Drinkaware height must be at least {DRINKAWARE_MIN_HEIGHT}px, currently {height_px}px",
            fix_suggestion=f"Increase drinkaware height to at least {DRINKAWARE_MIN_HEIGHT / canvas_height * 100:.1f}%",
            element_id=drinkaware.get("id")
        ))
    
    return issues


def validate_no_terms_and_conditions(
    headline: str, 
    subhead: str
) -> List[ValidationIssue]:
    """
    Validate no T&Cs in copy.
    HARD FAIL if detected.
    """
    issues = []
    text = f"{headline} {subhead}".lower()
    
    tc_patterns = [
        r"terms\s*(and|&)\s*conditions",
        r"t\s*&\s*c",
        r"t&cs",
        r"subject to",
        r"see\s+website\s+for\s+details",
        r"see\s+in\s*-?\s*store\s+for\s+details"
    ]
    
    for pattern in tc_patterns:
        if re.search(pattern, text):
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="TERMS_AND_CONDITIONS",
                message="Terms and conditions are not allowed in creative copy",
                fix_suggestion="Remove T&Cs reference from copy"
            ))
            break
    
    return issues


def validate_no_competition_copy(headline: str, subhead: str) -> List[ValidationIssue]:
    """
    Validate no competition/giveaway wording.
    HARD FAIL if detected.
    """
    issues = []
    text = f"{headline} {subhead}".lower()
    
    patterns = [
        r"\b(win|enter|contest|prize|giveaway|competition|raffle|lottery)\b",
        r"\b(chance\s+to\s+win|enter\s+now|enter\s+to\s+win)\b"
    ]
    
    for pattern in patterns:
        if re.search(pattern, text):
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="COMPETITION_COPY",
                message="Competition or prize wording is not allowed",
                fix_suggestion="Remove competition-related language"
            ))
            break
    
    return issues


def validate_no_sustainability_claims(headline: str, subhead: str) -> List[ValidationIssue]:
    """
    Validate no sustainability/green claims.
    HARD FAIL if detected.
    """
    issues = []
    text = f"{headline} {subhead}".lower()
    
    patterns = [
        r"\b(sustainable|sustainability|eco|eco-friendly|green|carbon|net\s*zero)\b",
        r"\b(environmental|planet|recycle|recyclable|biodegradable)\b",
        r"\b(organic|natural|clean|pure)\b"  # Can be subjective, flag as warning
    ]
    
    if re.search(patterns[0], text) or re.search(patterns[1], text):
        issues.append(ValidationIssue(
            severity=IssueSeverity.HARD,
            code="SUSTAINABILITY_CLAIM",
            message="Sustainability or environmental claims are not allowed without approval",
            fix_suggestion="Remove sustainability claims or obtain approval"
        ))
    
    return issues


def validate_no_charity_copy(headline: str, subhead: str) -> List[ValidationIssue]:
    """
    Validate no charity partnership copy.
    HARD FAIL if detected.
    """
    issues = []
    text = f"{headline} {subhead}".lower()
    
    patterns = [
        r"\b(charity|charitable|donate|donation|fundrais|nonprofit)\b",
        r"\b(support\s+(a\s+)?cause|giving\s+back|community)\b"
    ]
    
    for pattern in patterns:
        if re.search(pattern, text):
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="CHARITY_PARTNERSHIP",
                message="Charity partnership copy is not allowed",
                fix_suggestion="Remove charity-related messaging"
            ))
            break
    
    return issues


def validate_no_price_callouts(headline: str, subhead: str) -> List[ValidationIssue]:
    """
    Validate no price call-outs in copy.
    HARD FAIL if detected.
    """
    issues = []
    text = f"{headline} {subhead}".lower()
    
    patterns = [
        r"£\d+",
        r"\$\d+",
        r"\d+%\s*off",
        r"\b(price|discount|sale|deal|offer|save|saving|reduced|clearance)\b",
        r"\b(buy\s+one\s+get|bogof|2\s*for|3\s*for)\b"
    ]
    
    for pattern in patterns:
        if re.search(pattern, text):
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="PRICE_CALLOUT",
                message="Price call-outs are not allowed in copy",
                fix_suggestion="Remove pricing language from copy"
            ))
            break
    
    return issues


def validate_no_money_back_guarantee(headline: str, subhead: str) -> List[ValidationIssue]:
    """
    Validate no money-back guarantees.
    HARD FAIL if detected.
    """
    issues = []
    text = f"{headline} {subhead}".lower()
    
    patterns = [
        r"money\s*-?\s*back",
        r"\b(guarantee|guaranteed|refund|return)\b",
        r"satisfaction\s+(or|guaranteed)"
    ]
    
    for pattern in patterns:
        if re.search(pattern, text):
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="MONEY_BACK_GUARANTEE",
                message="Money-back guarantees are not allowed",
                fix_suggestion="Remove guarantee language"
            ))
            break
    
    return issues


def validate_no_claims(headline: str, subhead: str) -> List[ValidationIssue]:
    """
    Validate no unsubstantiated claims.
    HARD FAIL if detected.
    """
    issues = []
    text = f"{headline} {subhead}".lower()
    
    patterns = [
        r"#\s*1\b",
        r"\bnumber\s+(one|1)\b",
        r"\b(best|leading|top|favourite|favorite)\b",
        r"\b(clinically|scientifically|proven|tested)\b",
        r"\b(survey|study|studies|research)\s+(shows?|proves?|found)\b",
        r"\b(award|awarded|winning)\b"
    ]
    
    for pattern in patterns:
        if re.search(pattern, text):
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="UNSUBSTANTIATED_CLAIM",
                message="Claims like '#1', 'best', 'clinically proven' require substantiation",
                fix_suggestion="Remove claim or provide substantiation documentation"
            ))
            break
    
    return issues


def validate_value_tile_position(
    elements: List[Dict[str, Any]],
    canvas_width: int,
    canvas_height: int
) -> List[ValidationIssue]:
    """
    Validate value tile is not overlapping with other elements and is in allowed position.
    HARD FAIL if invalid.
    """
    issues = []
    
    value_tile = None
    for elem in elements:
        if elem.get("type") == "value_tile":
            value_tile = elem
            break
    
    if not value_tile:
        return issues
    
    # Convert to pixels for overlap checking
    vt_x, vt_y, vt_w, vt_h = percentage_to_pixels(
        value_tile.get("x", 0), value_tile.get("y", 0),
        value_tile.get("width", 0), value_tile.get("height", 0),
        canvas_width, canvas_height
    )
    vt_box = (vt_x, vt_y, vt_x + vt_w, vt_y + vt_h)
    
    # Check for overlaps
    for elem in elements:
        if elem.get("type") in ["value_tile", "background"]:
            continue
        
        if elem.get("x") is None:
            continue
            
        elem_x, elem_y, elem_w, elem_h = percentage_to_pixels(
            elem.get("x", 0), elem.get("y", 0),
            elem.get("width", 0), elem.get("height", 0),
            canvas_width, canvas_height
        )
        elem_box = (elem_x, elem_y, elem_x + elem_w, elem_y + elem_h)
        
        if boxes_overlap(vt_box, elem_box):
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="VALUE_TILE_OVERLAP",
                message=f"Value tile overlaps with {elem.get('type')} element",
                fix_suggestion=f"Move {elem.get('type')} element away from value tile",
                element_id=elem.get("id")
            ))
    
    return issues


def validate_social_safe_zones(
    elements: List[Dict[str, Any]],
    canvas_width: int,
    canvas_height: int,
    channel: str
) -> List[ValidationIssue]:
    """
    Validate Stories safe zones (top 200px and bottom 250px must be free).
    HARD FAIL if text/logos/tiles in safe zones.
    """
    issues = []
    
    if channel != "stories":
        return issues
    
    protected_types = ["headline", "subhead", "logo", "value_tile", "tesco_tag"]
    
    for elem in elements:
        if elem.get("type") not in protected_types:
            continue
        
        if elem.get("y") is None:
            continue
        
        # Convert to pixels
        _, elem_y, _, elem_h = percentage_to_pixels(
            elem.get("x", 0), elem.get("y", 0),
            elem.get("width", 0), elem.get("height", 0),
            canvas_width, canvas_height
        )
        
        elem_top = elem_y
        elem_bottom = elem_y + elem_h
        
        # Check top safe zone
        if elem_top < STORIES_SAFE_ZONE_TOP:
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="SAFE_ZONE_TOP_VIOLATION",
                message=f"{elem.get('type')} element is in top safe zone (top 200px)",
                fix_suggestion=f"Move element below {STORIES_SAFE_ZONE_TOP}px from top",
                element_id=elem.get("id"),
                bounding_box={"x": elem.get("x"), "y": elem.get("y"), 
                             "width": elem.get("width"), "height": elem.get("height")}
            ))
        
        # Check bottom safe zone
        bottom_zone_start = canvas_height - STORIES_SAFE_ZONE_BOTTOM
        if elem_bottom > bottom_zone_start:
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="SAFE_ZONE_BOTTOM_VIOLATION",
                message=f"{elem.get('type')} element is in bottom safe zone (bottom 250px)",
                fix_suggestion=f"Move element above {STORIES_SAFE_ZONE_BOTTOM}px from bottom",
                element_id=elem.get("id"),
                bounding_box={"x": elem.get("x"), "y": elem.get("y"), 
                             "width": elem.get("width"), "height": elem.get("height")}
            ))
    
    return issues


def validate_minimum_font_size(
    elements: List[Dict[str, Any]],
    canvas_height: int,
    channel: str
) -> List[ValidationIssue]:
    """
    Validate minimum font sizes.
    HARD FAIL if too small.
    """
    issues = []
    
    min_size = CHANNEL_CONFIG.get(channel, {}).get("min_font_size", MIN_FONT_SIZE_BRAND)
    
    for elem in elements:
        if elem.get("type") not in ["headline", "subhead"]:
            continue
        
        font_size = elem.get("font_size", 0)
        
        # Scale font size for canvas (base is 1920 height)
        scaled_size = scale_font_size(font_size, 1920, canvas_height)
        
        if font_size < min_size:
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="FONT_SIZE_TOO_SMALL",
                message=f"{elem.get('type')} font size ({font_size}px) is below minimum ({min_size}px)",
                fix_suggestion=f"Increase font size to at least {min_size}px",
                element_id=elem.get("id")
            ))
    
    return issues


def validate_wcag_contrast(
    elements: List[Dict[str, Any]],
    background_color: str
) -> List[ValidationIssue]:
    """
    Validate WCAG AA contrast for text elements.
    HARD FAIL if contrast is insufficient.
    """
    issues = []
    
    for elem in elements:
        if elem.get("type") not in ["headline", "subhead"]:
            continue
        
        text_color = elem.get("color")
        if not text_color:
            continue
        
        font_size = elem.get("font_size", 16)
        is_large_text = font_size >= 24  # 24px or larger is considered large text
        
        if not check_wcag_aa_contrast(text_color, background_color, is_large_text):
            ratio = calculate_contrast_ratio(text_color, background_color)
            threshold = WCAG_AA_LARGE_TEXT if is_large_text else WCAG_AA_NORMAL_TEXT
            
            issues.append(ValidationIssue(
                severity=IssueSeverity.HARD,
                code="WCAG_CONTRAST_FAIL",
                message=f"{elem.get('type')} contrast ratio ({ratio:.2f}:1) is below WCAG AA threshold ({threshold}:1)",
                fix_suggestion=f"Change text color to improve contrast with background {background_color}",
                element_id=elem.get("id")
            ))
    
    return issues


def validate_cta_safe_gap(
    elements: List[Dict[str, Any]],
    canvas_width: int,
    canvas_height: int,
    is_double_density: bool = True
) -> List[ValidationIssue]:
    """
    Validate safe gap between packshot and CTA.
    HARD FAIL if too close.
    """
    issues = []
    
    required_gap = CTA_SAFE_GAP_DOUBLE_DENSITY if is_double_density else CTA_SAFE_GAP_SINGLE_DENSITY
    
    # Find packshots and potential CTAs
    packshots = [e for e in elements if e.get("type") == "packshot"]
    ctas = [e for e in elements if e.get("type") in ["headline", "subhead"] and 
            any(kw in (e.get("text") or "").lower() for kw in ["shop", "buy", "get", "discover"])]
    
    for packshot in packshots:
        if packshot.get("x") is None:
            continue
            
        ps_x, ps_y, ps_w, ps_h = percentage_to_pixels(
            packshot.get("x", 0), packshot.get("y", 0),
            packshot.get("width", 0), packshot.get("height", 0),
            canvas_width, canvas_height
        )
        
        for cta in ctas:
            if cta.get("x") is None:
                continue
                
            cta_x, cta_y, cta_w, cta_h = percentage_to_pixels(
                cta.get("x", 0), cta.get("y", 0),
                cta.get("width", 0), cta.get("height", 0),
                canvas_width, canvas_height
            )
            
            # Calculate minimum distance between elements
            gap = calculate_min_gap(
                (ps_x, ps_y, ps_x + ps_w, ps_y + ps_h),
                (cta_x, cta_y, cta_x + cta_w, cta_y + cta_h)
            )
            
            if gap < required_gap:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.HARD,
                    code="CTA_SAFE_GAP_VIOLATION",
                    message=f"Gap between packshot and CTA ({gap}px) is less than required ({required_gap}px)",
                    fix_suggestion=f"Increase gap to at least {required_gap}px"
                ))
    
    return issues


def validate_people_in_photography(elements: List[Dict[str, Any]]) -> List[ValidationIssue]:
    """
    Warn if people might be present in photography.
    WARNING level - prompts user to confirm consent.
    """
    issues = []
    
    # This would ideally use image analysis, but for now just warn
    for elem in elements:
        if elem.get("type") == "packshot":
            issues.append(ValidationIssue(
                severity=IssueSeverity.WARN,
                code="PEOPLE_IN_PHOTOGRAPHY",
                message="If packshot contains people, ensure model consent is obtained",
                fix_suggestion="Verify model consent documentation is on file",
                element_id=elem.get("id")
            ))
            break  # Only warn once
    
    return issues


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def boxes_overlap(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> bool:
    """Check if two bounding boxes overlap."""
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2
    
    return not (x1_max < x2_min or x2_max < x1_min or 
                y1_max < y2_min or y2_max < y1_min)


def calculate_min_gap(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> int:
    """Calculate minimum gap between two boxes."""
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2
    
    # Horizontal gap
    if x1_max < x2_min:
        h_gap = x2_min - x1_max
    elif x2_max < x1_min:
        h_gap = x1_min - x2_max
    else:
        h_gap = 0
    
    # Vertical gap
    if y1_max < y2_min:
        v_gap = y2_min - y1_max
    elif y2_max < y1_min:
        v_gap = y1_min - y2_max
    else:
        v_gap = 0
    
    return max(h_gap, v_gap)


def get_background_color(elements: List[Dict[str, Any]]) -> str:
    """Extract background color from elements."""
    for elem in elements:
        if elem.get("type") == "background":
            return elem.get("color", "#FFFFFF")
    return "#FFFFFF"


def get_text_content(elements: List[Dict[str, Any]]) -> Tuple[str, str]:
    """Extract headline and subhead text from elements."""
    headline = ""
    subhead = ""
    
    for elem in elements:
        if elem.get("type") == "headline":
            headline = elem.get("text", "")
        elif elem.get("type") == "subhead":
            subhead = elem.get("text", "")
    
    return headline, subhead


# ============================================================================
# MAIN VALIDATION FUNCTION
# ============================================================================

def validate_layout(
    layout: Layout,
    canvas_size: str = "1080x1920",
    is_alcohol: bool = False,
    channel: str = "stories"
) -> ValidationResult:
    """
    Validate a complete layout against all Appendix B / Tesco rules.
    
    Args:
        layout: Layout object to validate
        canvas_size: Canvas dimensions (e.g., "1080x1920")
        is_alcohol: Whether this is an alcohol campaign
        channel: Target channel (facebook, instagram, stories, in_store, says)
        
    Returns:
        ValidationResult with ok status and list of issues
    """
    canvas_width, canvas_height = parse_canvas_size(canvas_size)
    elements = [e.model_dump() if hasattr(e, 'model_dump') else e for e in layout.elements]
    
    issues: List[ValidationIssue] = []
    checked_rules: List[str] = []
    
    # Get text content for copy validation
    headline, subhead = get_text_content(elements)
    background_color = get_background_color(elements)
    
    # Run all validations
    
    # 1. Tesco tag validation
    checked_rules.append("TESCO_TAG")
    for elem in elements:
        issue = validate_tesco_tag(elem)
        if issue:
            issues.append(issue)
    
    # 2. Drinkaware validation (alcohol campaigns)
    checked_rules.append("DRINKAWARE")
    issues.extend(validate_drinkaware(elements, is_alcohol, canvas_height))
    
    # 3. No T&Cs
    checked_rules.append("NO_TERMS_AND_CONDITIONS")
    issues.extend(validate_no_terms_and_conditions(headline, subhead))
    
    # 4. No competition copy
    checked_rules.append("NO_COMPETITION_COPY")
    issues.extend(validate_no_competition_copy(headline, subhead))
    
    # 5. No sustainability claims
    checked_rules.append("NO_SUSTAINABILITY_CLAIMS")
    issues.extend(validate_no_sustainability_claims(headline, subhead))
    
    # 6. No charity copy
    checked_rules.append("NO_CHARITY_COPY")
    issues.extend(validate_no_charity_copy(headline, subhead))
    
    # 7. No price callouts
    checked_rules.append("NO_PRICE_CALLOUTS")
    issues.extend(validate_no_price_callouts(headline, subhead))
    
    # 8. No money-back guarantees
    checked_rules.append("NO_MONEY_BACK_GUARANTEE")
    issues.extend(validate_no_money_back_guarantee(headline, subhead))
    
    # 9. No unsubstantiated claims
    checked_rules.append("NO_CLAIMS")
    issues.extend(validate_no_claims(headline, subhead))
    
    # 10. Value tile position
    checked_rules.append("VALUE_TILE_POSITION")
    issues.extend(validate_value_tile_position(elements, canvas_width, canvas_height))
    
    # 11. Social safe zones
    checked_rules.append("SOCIAL_SAFE_ZONES")
    issues.extend(validate_social_safe_zones(elements, canvas_width, canvas_height, channel))
    
    # 12. Minimum font size
    checked_rules.append("MINIMUM_FONT_SIZE")
    issues.extend(validate_minimum_font_size(elements, canvas_height, channel))
    
    # 13. WCAG contrast
    checked_rules.append("WCAG_CONTRAST")
    issues.extend(validate_wcag_contrast(elements, background_color))
    
    # 14. CTA safe gap
    checked_rules.append("CTA_SAFE_GAP")
    issues.extend(validate_cta_safe_gap(elements, canvas_width, canvas_height))
    
    # 15. People in photography (warning only)
    checked_rules.append("PEOPLE_IN_PHOTOGRAPHY")
    issues.extend(validate_people_in_photography(elements))
    
    # Determine overall status (ok if no hard failures)
    hard_failures = [i for i in issues if i.severity == IssueSeverity.HARD]
    ok = len(hard_failures) == 0
    
    logger.info(
        "layout_validated",
        ok=ok,
        hard_issues=len(hard_failures),
        warn_issues=len(issues) - len(hard_failures),
        rules_checked=len(checked_rules)
    )
    
    return ValidationResult(
        ok=ok,
        issues=issues,
        checked_rules=checked_rules
    )
