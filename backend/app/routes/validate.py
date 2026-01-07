"""
Validate Routes - Handle layout validation against Appendix B rules.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
import structlog

from app.models import ValidateRequest, ValidationResult, Layout, LayoutElement
from app.services.validators import validate_layout
from app.services.brand_guardian import brand_guardian

logger = structlog.get_logger()

router = APIRouter(prefix="/validate", tags=["Validate"])


@router.post("/check", response_model=ValidationResult)
async def check_layout(request: ValidateRequest):
    """
    Validate a layout against Appendix B / Tesco rules.
    
    Checks:
    - Tesco tag text validity
    - Drinkaware presence for alcohol campaigns
    - No T&Cs, competition copy, sustainability claims, etc.
    - Value tile positioning
    - Social safe zones (for Stories)
    - Minimum font sizes
    - WCAG AA contrast
    - CTA safe gaps
    
    Returns validation result with:
    - ok: Boolean indicating if layout passes all hard rules
    - issues: List of issues with severity, code, message, and fix suggestions
    - checked_rules: List of rule names that were checked
    """
    try:
        result = validate_layout(
            layout=request.layout,
            canvas_size=request.canvas_size,
            is_alcohol=request.is_alcohol,
            channel=request.channel
        )
        
        logger.info(
            "layout_validated",
            ok=result.ok,
            issue_count=len(result.issues),
            channel=request.channel
        )
        
        return result
        
    except Exception as e:
        logger.error("validation_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )


@router.post("/comprehensive")
async def comprehensive_validation(
    request: ValidateRequest,
    brand_colors: Optional[List[str]] = None,
    retailer: str = "tesco"
):
    """
    Comprehensive validation including brand identity and visual quality.
    
    Uses Brand Guardian Engine for:
    - Brand color consistency
    - Logo sizing and placement
    - Visual hierarchy
    - Layout balance
    - WCAG contrast
    - Retailer compliance
    """
    try:
        all_issues = []
        
        # Standard compliance validation
        compliance_result = validate_layout(
            layout=request.layout,
            canvas_size=request.canvas_size,
            is_alcohol=request.is_alcohol,
            channel=request.channel
        )
        all_issues.extend(compliance_result.issues)
        
        # Brand identity validation
        if brand_colors:
            brand_issues = brand_guardian.validate_brand_identity(
                request.layout,
                brand_colors,
                request.canvas_size
            )
            all_issues.extend(brand_issues)
        
        # Visual quality validation
        visual_issues = brand_guardian.validate_visual_quality(
            request.layout,
            request.canvas_size
        )
        all_issues.extend(visual_issues)
        
        # Retailer-specific validation
        retailer_issues = brand_guardian.validate_retailer_compliance(
            request.layout,
            retailer=retailer,
            is_alcohol=request.is_alcohol,
            channel=request.channel,
            canvas_size=request.canvas_size
        )
        all_issues.extend(retailer_issues)
        
        # Deduplicate issues by code
        seen_codes = set()
        unique_issues = []
        for issue in all_issues:
            code = issue.code if hasattr(issue, 'code') else issue.get('code')
            if code not in seen_codes:
                seen_codes.add(code)
                unique_issues.append(issue)
        
        hard_failures = [
            i for i in unique_issues 
            if (hasattr(i, 'severity') and i.severity.value == 'hard') or 
               (isinstance(i, dict) and i.get('severity') == 'hard')
        ]
        
        return {
            "ok": len(hard_failures) == 0,
            "issues": [i.model_dump() if hasattr(i, 'model_dump') else i for i in unique_issues],
            "checked_rules": compliance_result.checked_rules + [
                "BRAND_IDENTITY", "VISUAL_QUALITY", "RETAILER_COMPLIANCE"
            ],
            "summary": {
                "total_issues": len(unique_issues),
                "hard_failures": len(hard_failures),
                "warnings": len(unique_issues) - len(hard_failures),
                "compliance_score": max(0, 100 - len(hard_failures) * 20 - (len(unique_issues) - len(hard_failures)) * 5)
            }
        }
        
    except Exception as e:
        logger.error("comprehensive_validation_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Comprehensive validation failed: {str(e)}"
        )


@router.post("/quick-check")
async def quick_check(
    headline: str,
    subhead: str = "",
    tesco_tag_text: str = "Available at Tesco",
    is_alcohol: bool = False
):
    """
    Quick validation of copy and basic elements without full layout.
    
    Useful for pre-validation before layout generation.
    """
    from app.services.validators import (
        validate_no_terms_and_conditions,
        validate_no_competition_copy,
        validate_no_sustainability_claims,
        validate_no_charity_copy,
        validate_no_price_callouts,
        validate_no_money_back_guarantee,
        validate_no_claims,
        validate_tesco_tag
    )
    from app.models import IssueSeverity
    
    issues = []
    
    # Copy validation
    issues.extend(validate_no_terms_and_conditions(headline, subhead))
    issues.extend(validate_no_competition_copy(headline, subhead))
    issues.extend(validate_no_sustainability_claims(headline, subhead))
    issues.extend(validate_no_charity_copy(headline, subhead))
    issues.extend(validate_no_price_callouts(headline, subhead))
    issues.extend(validate_no_money_back_guarantee(headline, subhead))
    issues.extend(validate_no_claims(headline, subhead))
    
    # Tesco tag validation
    tesco_issue = validate_tesco_tag({"type": "tesco_tag", "text": tesco_tag_text})
    if tesco_issue:
        issues.append(tesco_issue)
    
    # Check for drinkaware requirement
    if is_alcohol:
        issues.append({
            "severity": "warn",
            "code": "DRINKAWARE_REQUIRED",
            "message": "Drinkaware lock-up will be required for this alcohol campaign",
            "fix_suggestion": "Ensure drinkaware element is added with black or white color"
        })
    
    hard_failures = [i for i in issues if getattr(i, 'severity', i.get('severity')) == IssueSeverity.HARD or i.get('severity') == 'hard']
    
    return {
        "ok": len(hard_failures) == 0,
        "issues": [i.model_dump() if hasattr(i, 'model_dump') else i for i in issues],
        "headline": headline,
        "subhead": subhead
    }


@router.get("/rules")
async def get_validation_rules():
    """
    Get a list of all validation rules with descriptions.
    
    Useful for documentation and UI display.
    """
    rules = [
        {
            "code": "TESCO_TAG",
            "severity": "hard",
            "description": "Tesco tag text must be one of: 'Only at Tesco', 'Available at Tesco', 'Selected stores. While stocks last'"
        },
        {
            "code": "DRINKAWARE",
            "severity": "hard",
            "description": "Drinkaware lock-up required for alcohol campaigns with black/white color and minimum 20px height"
        },
        {
            "code": "NO_TERMS_AND_CONDITIONS",
            "severity": "hard",
            "description": "No T&Cs allowed in creative copy"
        },
        {
            "code": "NO_COMPETITION_COPY",
            "severity": "hard",
            "description": "No competition or giveaway wording allowed"
        },
        {
            "code": "NO_SUSTAINABILITY_CLAIMS",
            "severity": "hard",
            "description": "No sustainability or environmental claims without approval"
        },
        {
            "code": "NO_CHARITY_COPY",
            "severity": "hard",
            "description": "No charity partnership copy allowed"
        },
        {
            "code": "NO_PRICE_CALLOUTS",
            "severity": "hard",
            "description": "No price or discount references in copy"
        },
        {
            "code": "NO_MONEY_BACK_GUARANTEE",
            "severity": "hard",
            "description": "No money-back guarantee language allowed"
        },
        {
            "code": "NO_CLAIMS",
            "severity": "hard",
            "description": "No unsubstantiated claims (#1, best, clinically proven, etc.)"
        },
        {
            "code": "VALUE_TILE_POSITION",
            "severity": "hard",
            "description": "Value tile must not overlap with other elements"
        },
        {
            "code": "SOCIAL_SAFE_ZONES",
            "severity": "hard",
            "description": "Stories: Top 200px and bottom 250px must be free of text/logos/tiles"
        },
        {
            "code": "MINIMUM_FONT_SIZE",
            "severity": "hard",
            "description": "Minimum font size: 20px for Brand/Social, 12px for SAYS"
        },
        {
            "code": "WCAG_CONTRAST",
            "severity": "hard",
            "description": "Text must meet WCAG AA contrast (4.5:1 normal, 3:1 large text)"
        },
        {
            "code": "CTA_SAFE_GAP",
            "severity": "hard",
            "description": "Minimum 24px gap between packshot and CTA (12px for single density)"
        },
        {
            "code": "PEOPLE_IN_PHOTOGRAPHY",
            "severity": "warn",
            "description": "Confirm model consent if people are present in imagery"
        }
    ]
    
    return {"rules": rules}
