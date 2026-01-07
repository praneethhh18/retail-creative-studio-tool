"""
Generate Routes - Handle layout generation using LLM.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import structlog

from app.models import GenRequest, LayoutsResponse, CopyModerationRequest, CopyModerationResult
from app.services.layout_llm import llm_client
from app.utils import sanitize_text_for_llm

logger = structlog.get_logger()

router = APIRouter(prefix="/generate", tags=["Generate"])


@router.post("/layouts", response_model=LayoutsResponse)
async def generate_layouts(request: GenRequest):
    """
    Generate layout suggestions for a creative.
    
    Uses LLM if available, otherwise falls back to deterministic stub layouts.
    Returns 3+ layout options with scores.
    
    Supports both new and legacy request formats:
    - New: packshot_ids, logo_ids, background_id, palette, channel, user_prompt
    - Legacy: brand, headline, subhead, colors, packshot_count, etc.
    """
    try:
        # Handle both new and legacy request formats
        headline = sanitize_text_for_llm(request.headline or request.user_prompt or "")
        subhead = sanitize_text_for_llm(request.subhead or "")
        brand = sanitize_text_for_llm(request.brand or "")
        
        # Use palette from new API or colors from legacy
        colors = request.palette if request.palette else request.colors
        
        # Derive packshot count from packshot_ids if provided
        packshot_count = len(request.packshot_ids) if request.packshot_ids else request.packshot_count
        packshot_count = max(1, min(5, packshot_count))  # Clamp to 1-5
        
        # Map packshot_ids to packshot_assets
        packshot_assets = request.packshot_ids if request.packshot_ids else request.packshot_assets
        
        # Map logo_ids to logo_asset
        logo_asset = request.logo_ids[0] if request.logo_ids else request.logo_asset
        
        # Map channel to canvas size
        canvas = request.canvas
        if request.channel:
            channel_map = {
                'facebook_feed': '1200x628',
                'instagram_feed': '1080x1080', 
                'instagram_story': '1080x1920',
                'instore_a4': '2480x3508'
            }
            canvas = channel_map.get(request.channel, request.canvas)
        
        # Generate layouts
        result = llm_client.generate_layouts(
            brand=brand,
            headline=headline,
            subhead=subhead,
            colors=colors,
            packshot_count=packshot_count,
            required_tiles=request.required_tiles,
            canvas=canvas,
            is_alcohol=request.is_alcohol,
            packshot_assets=packshot_assets,
            logo_asset=logo_asset
        )
        
        logger.info(
            "layouts_generated",
            brand=brand,
            layout_count=len(result.get("layouts", [])),
            llm_available=llm_client.is_available()
        )
        
        return result
        
    except Exception as e:
        logger.error("layout_generation_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Layout generation failed: {str(e)}"
        )


@router.post("/moderate-copy", response_model=CopyModerationResult)
async def moderate_copy(request: CopyModerationRequest):
    """
    Check headline and subhead for compliance issues.
    
    Validates against:
    - Price/discount references
    - Competition/giveaway wording
    - Sustainability claims
    - Charity partnerships
    - Unsubstantiated claims
    
    Returns ok status and list of issues.
    """
    try:
        # Sanitize inputs
        headline = sanitize_text_for_llm(request.headline)
        subhead = sanitize_text_for_llm(request.subhead or "")
        
        result = llm_client.moderate_copy(headline, subhead)
        
        logger.info(
            "copy_moderated",
            ok=result.get("ok", False),
            issue_count=len(result.get("issues", []))
        )
        
        return result
        
    except Exception as e:
        logger.error("copy_moderation_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Copy moderation failed: {str(e)}"
        )


@router.post("/classify-content")
async def classify_content(text: str):
    """
    Classify text content for borderline cases.
    
    Returns:
    - classification: "allowed", "disallowed", or "needs_edit"
    - reason: Explanation
    - suggested_edit: Suggested alternative text
    """
    try:
        sanitized = sanitize_text_for_llm(text)
        result = llm_client.classify_content(sanitized)
        
        return result
        
    except Exception as e:
        logger.error("content_classification_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Content classification failed: {str(e)}"
        )


@router.get("/status")
async def get_llm_status():
    """
    Check LLM service status.
    
    Returns whether LLM is available and which provider is configured.
    """
    return {
        "available": llm_client.is_available(),
        "provider": llm_client.provider,
        "model": llm_client.model if llm_client.is_available() else None
    }


@router.get("/providers")
async def get_available_providers():
    """
    Get information about supported LLM providers.
    
    Returns list of providers with setup instructions.
    """
    return {
        "current_provider": llm_client.provider if llm_client.is_available() else None,
        "current_model": llm_client.model if llm_client.is_available() else None,
        "providers": [
            {
                "id": "groq",
                "name": "Groq",
                "free": True,
                "description": "Fast inference with generous free tier",
                "signup_url": "https://console.groq.com/keys",
                "env_var": "GROQ_API_KEY",
                "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
            },
            {
                "id": "grok",
                "name": "Grok (xAI)",
                "free": True,
                "description": "Free with X Premium subscription",
                "signup_url": "https://console.x.ai/",
                "env_var": "XAI_API_KEY",
                "models": ["grok-beta", "grok-2-1212"]
            },
            {
                "id": "gemini",
                "name": "Google Gemini",
                "free": True,
                "description": "Google's AI with free tier",
                "signup_url": "https://makersuite.google.com/app/apikey",
                "env_var": "GOOGLE_API_KEY",
                "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"]
            },
            {
                "id": "ollama",
                "name": "Ollama (Local)",
                "free": True,
                "description": "Completely free, runs on your machine",
                "signup_url": "https://ollama.ai/",
                "env_var": None,
                "models": ["llama3.2", "mistral", "codellama", "phi3"],
                "setup_command": "ollama pull llama3.2"
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "free": False,
                "description": "GPT-4 and other models (paid)",
                "signup_url": "https://platform.openai.com/api-keys",
                "env_var": "OPENAI_API_KEY",
                "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"]
            }
        ]
    }


@router.post("/detect-tone")
async def detect_tone(
    brand: str = "",
    colors: list[str] = None,
    headline: str = "",
    category: str = "general"
):
    """
    Analyze brand identity and detect the appropriate messaging tone.
    
    Returns:
    - detected_tone: bold, minimal, premium, playful, or classic
    - color_mood: warm, cool, neutral, or vibrant
    - suggested_style: layout_type, emphasis, and contrast recommendations
    - reasoning: Explanation of analysis
    """
    try:
        result = llm_client.detect_tone(
            brand=sanitize_text_for_llm(brand),
            colors=colors or [],
            headline=sanitize_text_for_llm(headline),
            category=category
        )
        
        logger.info(
            "tone_detected",
            tone=result.get("detected_tone"),
            mood=result.get("color_mood")
        )
        
        return result
        
    except Exception as e:
        logger.error("tone_detection_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Tone detection failed: {str(e)}"
        )


@router.post("/layouts-with-tone")
async def generate_layouts_with_tone(request: GenRequest, style_preset: str = None):
    """
    Enhanced layout generation with automatic tone detection.
    
    If style_preset is provided, uses that tone; otherwise auto-detects.
    Returns layouts enriched with tone_analysis metadata.
    
    Style presets:
    - bold: Large packshots, bold headlines, high contrast
    - minimal: Clean layouts, white space, subtle typography
    - premium: Elegant spacing, refined typography
    - playful: Dynamic compositions, varied sizes
    - classic: Traditional layouts, balanced composition
    """
    try:
        headline = sanitize_text_for_llm(request.headline or request.user_prompt or "")
        subhead = sanitize_text_for_llm(request.subhead or "")
        brand = sanitize_text_for_llm(request.brand or "")
        
        colors = request.palette if request.palette else request.colors
        packshot_count = len(request.packshot_ids) if request.packshot_ids else request.packshot_count
        packshot_count = max(1, min(5, packshot_count))
        
        packshot_assets = request.packshot_ids if request.packshot_ids else request.packshot_assets
        logo_asset = request.logo_ids[0] if request.logo_ids else request.logo_asset
        
        canvas = request.canvas
        if request.channel:
            channel_map = {
                'facebook_feed': '1200x628',
                'instagram_feed': '1080x1080', 
                'instagram_story': '1080x1920',
                'instore_a4': '2480x3508'
            }
            canvas = channel_map.get(request.channel, request.canvas)
        
        result = llm_client.generate_layouts_with_tone(
            brand=brand,
            headline=headline,
            subhead=subhead,
            colors=colors,
            packshot_count=packshot_count,
            required_tiles=request.required_tiles,
            canvas=canvas,
            is_alcohol=request.is_alcohol,
            packshot_assets=packshot_assets,
            logo_asset=logo_asset,
            style_preset=style_preset,
            category="general"  # Could be made configurable
        )
        
        logger.info(
            "layouts_generated_with_tone",
            brand=brand,
            layout_count=len(result.get("layouts", [])),
            tone=result.get("style_applied")
        )
        
        return result
        
    except Exception as e:
        logger.error("layout_generation_with_tone_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Layout generation failed: {str(e)}"
        )


@router.get("/style-presets")
async def get_style_presets():
    """
    Get available style presets for layout generation.
    """
    return {
        "presets": [
            {
                "id": "bold",
                "name": "Bold",
                "description": "Large packshots, bold headlines, high contrast colors",
                "icon": "⚡"
            },
            {
                "id": "minimal",
                "name": "Minimal",
                "description": "Clean layouts, lots of white space, subtle typography",
                "icon": "🔲"
            },
            {
                "id": "premium",
                "name": "Premium",
                "description": "Elegant spacing, refined typography, sophisticated colors",
                "icon": "✨"
            },
            {
                "id": "playful",
                "name": "Playful",
                "description": "Dynamic compositions, varied sizes, energetic layouts",
                "icon": "🎨"
            },
            {
                "id": "classic",
                "name": "Classic",
                "description": "Traditional layouts, balanced composition, professional feel",
                "icon": "📐"
            }
        ]
    }
