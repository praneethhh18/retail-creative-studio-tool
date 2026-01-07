"""
LLM Client for layout generation and content moderation.
Supports multiple providers: Grok (xAI), Groq, Google Gemini, Ollama, OpenAI.
Falls back to deterministic stubs if no API is available.
"""
import os
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx
from dotenv import load_dotenv

# Load environment variables from project root
env_path = Path(__file__).parent.parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

logger = structlog.get_logger()

# ============================================================================
# LLM Provider Detection
# ============================================================================

# Try to import OpenAI (also works for Grok/xAI and Groq which use OpenAI-compatible API)
try:
    from openai import OpenAI
    OPENAI_COMPATIBLE_AVAILABLE = True
except ImportError:
    OPENAI_COMPATIBLE_AVAILABLE = False
    logger.warning("openai_lib_not_available", message="OpenAI library not installed (needed for Grok/Groq too)")

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.info("gemini_not_available", message="Google Generative AI not installed")


# ============================================================================
# LLM PROMPT TEMPLATES - Enhanced for Advanced Layout Generation
# ============================================================================

LAYOUT_GENERATION_PROMPT = """You are an expert retail creative layout generator with deep understanding of visual design principles, brand guidelines, and platform compliance.

Generate professional, visually appealing layouts that follow these principles:

VISUAL DESIGN RULES:
1. Visual Hierarchy: Headline > Subhead > Body. Size ratio should be approximately 1.5-2x between levels.
2. Golden Ratio: Use 60-30-10 rule for visual weight distribution.
3. White Space: Maintain breathing room (minimum 5% margin from edges).
4. Balance: Distribute visual weight evenly. Avoid clustering elements on one side.
5. Alignment: Use consistent alignment (left, center, or right) throughout.
6. Focal Point: The packshot or hero image should be the primary attention grabber.

COMPLIANCE RULES (HARD REQUIREMENTS):
- Stories format: Keep elements out of top 200px (10.4%) and bottom 250px (13%) safe zones.
- Tesco tag MUST be included with text "Available at Tesco" or "Only at Tesco".
- If alcohol=true, MUST include drinkaware element in black (#000000) or white (#FFFFFF).
- Minimum font size: 20px for headlines, 16px for body text.
- WCAG AA contrast: 4.5:1 for normal text, 3:1 for large text (24px+).
- Value tile and Tesco tag MUST NOT overlap with any other element.

OUTPUT FORMAT:
Return valid JSON with a top-level "layouts" array. Each layout must include:
- id: unique identifier (layout_1, layout_2, etc.)
- score: quality score 0-1 (higher = better)
- elements: array of elements with type, position (x,y as %), size (width,height as %), and type-specific properties

ELEMENT TYPES AND PROPERTIES:
- background: color (hex)
- packshot: asset, x, y, width, height, z (layer order)
- logo: asset, x, y, width, height, z
- headline: text, x, y, width, height, font_size (px), color (hex), font_family
- subhead: text, x, y, width, height, font_size (px), color (hex), font_family  
- tesco_tag: text, x, y, width, height
- value_tile: x, y, width, height
- drinkaware: x, y, width, height, color (hex)

STYLE GUIDANCE based on tone:
- "bold": Large packshots (50%+), bold headlines, high contrast colors
- "minimal": Clean layouts, lots of white space, subtle typography
- "premium": Elegant spacing, refined typography, sophisticated color palette
- "playful": Dynamic compositions, varied sizes, energetic layouts
- "classic": Traditional layouts, balanced composition, professional feel

Input:
{input_json}

Generate 3 diverse, high-quality layouts. Return ONLY valid JSON."""

COPY_MODERATION_PROMPT = """You are a content compliance expert for retail advertising. Analyze copy for regulatory and brand safety issues.

STRICTLY PROHIBITED (return ok=false):
1. Price/Discount Language: £, $, %, off, save, sale, deal, offer, discount, reduced, clearance, BOGOF
2. Competition/Prize: win, enter, contest, prize, giveaway, competition, raffle, lottery, chance to win
3. Sustainability Claims: sustainable, eco, green, carbon, environmental, organic, natural (without certification)
4. Charity References: charity, donate, fundraise, nonprofit, give back
5. Unsubstantiated Claims: #1, best, leading, top, award-winning, clinically proven, scientifically tested
6. Guarantees: money-back, guaranteed, refund, satisfaction guaranteed
7. Terms & Conditions: T&Cs, terms and conditions, subject to, see website for details

FLAGGED FOR REVIEW (return ok=false with warning):
- Superlatives without evidence
- Health claims
- Comparative statements
- Time-limited offers without dates

Return JSON format:
{
  "ok": boolean,
  "issues": [
    {
      "code": "ISSUE_CODE",
      "severity": "hard" | "warn",
      "message": "Description of issue",
      "suggestion": "How to fix it"
    }
  ],
  "sentiment": "positive" | "neutral" | "negative",
  "tone": "informative" | "promotional" | "urgent" | "friendly"
}

Headline: {headline}
Subhead: {subhead}"""

TONE_DETECTION_PROMPT = """Analyze the brand identity and messaging tone from the provided inputs.

Return JSON:
{
  "detected_tone": "bold" | "minimal" | "premium" | "playful" | "classic",
  "color_mood": "warm" | "cool" | "neutral" | "vibrant",
  "suggested_style": {
    "layout_type": "hero-centered" | "split" | "multi-product" | "text-overlay",
    "emphasis": "product" | "message" | "brand",
    "contrast_level": "high" | "medium" | "low"
  },
  "reasoning": "Brief explanation of analysis"
}

Brand: {brand}
Colors: {colors}
Headline: {headline}
Product Category: {category}"""

CONTENT_CLASSIFICATION_PROMPT = """Classify the following text for a retail creative.
Return JSON: {"classification": "allowed|disallowed|needs_edit", "reason": "...", "suggested_edit": "..."}

Text to classify: {text}

Rules:
- Disallowed: price/discount references, competition/prize wording, sustainability claims, charity mentions, unsubstantiated claims
- Needs edit: ambiguous wording that could be improved
- Allowed: neutral product descriptions, brand names, CTAs without claims

Return only JSON."""


# ============================================================================
# Provider Configurations
# ============================================================================

PROVIDER_CONFIGS = {
    # Grok (xAI) - Free with X Premium, OpenAI-compatible API
    "grok": {
        "base_url": "https://api.x.ai/v1",
        "env_key": "XAI_API_KEY",
        "default_model": "grok-beta",
        "models": ["grok-beta", "grok-2-1212"],
    },
    # Groq - Very fast inference, generous free tier
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "default_model": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
    },
    # Google Gemini - Generous free tier (uses google-generativeai library)
    "gemini": {
        "env_key": "GOOGLE_API_KEY",
        "default_model": "gemini-2.0-flash",
        "models": ["gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro-latest"],
    },
    # Ollama - Completely free, runs locally
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "env_key": None,  # No API key needed
        "default_model": "llama3.2",
        "models": ["llama3.2", "mistral", "codellama", "phi3"],
    },
    # OpenAI - Paid
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
    },
}


class LLMClient:
    """
    Client for LLM interactions supporting multiple providers:
    - Grok (xAI): Free with X Premium subscription
    - Groq: Fast inference with generous free tier
    - Google Gemini: Free tier available
    - Ollama: Completely free, runs locally
    - OpenAI: Paid (fallback)
    
    Falls back to deterministic stubs if no API is available.
    """
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "auto").lower()
        self.model = os.getenv("LLM_MODEL", "")
        self.client = None
        self.gemini_model = None
        self._init_provider()
    
    def _init_provider(self):
        """Initialize the LLM provider based on configuration or auto-detect."""
        
        # If auto, try providers in order of preference (free first)
        if self.provider == "auto":
            provider_order = ["groq", "grok", "gemini", "ollama", "openai"]
            for provider in provider_order:
                if self._try_init_provider(provider):
                    return
            logger.warning("llm_client_stub_mode", 
                          message="No LLM API available, using deterministic stubs")
        else:
            if not self._try_init_provider(self.provider):
                logger.warning("llm_client_stub_mode", 
                              message=f"Provider {self.provider} not available, using deterministic stubs")
    
    def _try_init_provider(self, provider: str) -> bool:
        """Try to initialize a specific provider. Returns True if successful."""
        config = PROVIDER_CONFIGS.get(provider)
        if not config:
            return False
        
        # Get API key if required
        api_key = None
        if config.get("env_key"):
            api_key = os.getenv(config["env_key"])
            if not api_key:
                return False
        
        # Special handling for Gemini (uses different library)
        if provider == "gemini":
            if not GEMINI_AVAILABLE:
                return False
            try:
                genai.configure(api_key=api_key)
                model_name = self.model or config["default_model"]
                self.gemini_model = genai.GenerativeModel(model_name)
                self.provider = provider
                self.model = model_name
                logger.info("llm_client_init", provider=provider, model=model_name)
                return True
            except Exception as e:
                logger.warning("gemini_init_failed", error=str(e))
                return False
        
        # OpenAI-compatible providers (Grok, Groq, Ollama, OpenAI)
        if not OPENAI_COMPATIBLE_AVAILABLE:
            return False
        
        # For Ollama, check if server is running
        if provider == "ollama":
            try:
                response = httpx.get(f"{config['base_url']}/models", timeout=2.0)
                if response.status_code != 200:
                    return False
            except Exception:
                return False
        
        try:
            model_name = self.model or config["default_model"]
            self.client = OpenAI(
                api_key=api_key or "ollama",  # Ollama doesn't need real key
                base_url=config.get("base_url")
            )
            self.provider = provider
            self.model = model_name
            logger.info("llm_client_init", provider=provider, model=model_name)
            return True
        except Exception as e:
            logger.warning("provider_init_failed", provider=provider, error=str(e))
            return False
    
    def is_available(self) -> bool:
        """Check if LLM API is available."""
        return self.client is not None or self.gemini_model is not None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def call_llm(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 800,
        temperature: float = 0.2
    ) -> str:
        """
        Call the LLM with the given prompt.
        
        Args:
            prompt: User prompt
            system: Optional system message
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            
        Returns:
            LLM response text
        """
        # Gemini uses different API
        if self.gemini_model:
            return self._call_gemini(prompt, system, max_tokens, temperature)
        
        if not self.client:
            raise RuntimeError("LLM client not available")
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("llm_call_failed", provider=self.provider, error=str(e))
            raise
    
    def _call_gemini(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 800,
        temperature: float = 0.2
    ) -> str:
        """Call Google Gemini API."""
        try:
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            response = self.gemini_model.generate_content(
                full_prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                }
            )
            return response.text
        except Exception as e:
            logger.error("gemini_call_failed", error=str(e))
            raise
    
    def extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response, handling markdown code blocks and extra text.
        """
        # Try to find JSON in code blocks
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if code_block_match:
            text = code_block_match.group(1)
        
        # Try to find JSON object or array
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if json_match:
            text = json_match.group(1)
        
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            logger.error("json_parse_failed", error=str(e), text=text[:200])
            raise ValueError(f"Failed to parse JSON: {e}")
    
    def generate_layouts(
        self,
        brand: str,
        headline: str,
        subhead: str,
        colors: List[str],
        packshot_count: int,
        required_tiles: Dict[str, bool],
        canvas: str = "1080x1920",
        is_alcohol: bool = False,
        packshot_assets: List[str] = None,
        logo_asset: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate layout suggestions using LLM or fallback stub.
        """
        input_data = {
            "brand": brand,
            "headline": headline,
            "subhead": subhead,
            "colors": colors if colors else ["#FFFFFF", "#000000"],
            "packshot_count": packshot_count,
            "required_tiles": required_tiles,
            "canvas": canvas,
            "alcohol": is_alcohol
        }
        
        if self.is_available():
            try:
                prompt = LAYOUT_GENERATION_PROMPT.format(
                    input_json=json.dumps(input_data, indent=2)
                )
                response = self.call_llm(prompt, max_tokens=1500, temperature=0.3)
                layouts = self.extract_json(response)
                
                # Add asset references
                layouts = self._add_asset_references(
                    layouts, packshot_assets or [], logo_asset
                )
                
                logger.info("layouts_generated_llm", count=len(layouts.get("layouts", [])))
                return layouts
            except Exception as e:
                logger.error("layout_generation_failed", error=str(e))
                # Fall through to stub
        
        # Fallback to deterministic stub
        return self._generate_stub_layouts(
            brand, headline, subhead, colors, packshot_count,
            required_tiles, canvas, is_alcohol, packshot_assets, logo_asset
        )
    
    def _add_asset_references(
        self,
        layouts: Dict[str, Any],
        packshot_assets: List[str],
        logo_asset: Optional[str]
    ) -> Dict[str, Any]:
        """Add actual asset references to generated layouts."""
        for layout in layouts.get("layouts", []):
            pack_idx = 0
            for element in layout.get("elements", []):
                if element.get("type") == "packshot":
                    if packshot_assets and pack_idx < len(packshot_assets):
                        element["asset"] = packshot_assets[pack_idx]
                        pack_idx += 1
                elif element.get("type") == "logo" and logo_asset:
                    element["asset"] = logo_asset
        return layouts
    
    def _generate_stub_layouts(
        self,
        brand: str,
        headline: str,
        subhead: str,
        colors: List[str],
        packshot_count: int,
        required_tiles: Dict[str, bool],
        canvas: str,
        is_alcohol: bool,
        packshot_assets: List[str] = None,
        logo_asset: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate professional layout variations based on canvas size."""
        bg_color = colors[0] if colors else "#FFFFFF"
        accent_color = colors[1] if len(colors) > 1 else "#000000"
        text_color = "#000000" if self._is_light_color(bg_color) else "#FFFFFF"
        
        # Parse canvas dimensions
        canvas_parts = canvas.split('x')
        canvas_width = int(canvas_parts[0]) if len(canvas_parts) > 0 else 1080
        canvas_height = int(canvas_parts[1]) if len(canvas_parts) > 1 else 1080
        is_portrait = canvas_height > canvas_width  # Stories format
        is_landscape = canvas_width > canvas_height  # Facebook feed
        is_square = canvas_width == canvas_height  # Instagram
        
        # Prepare assets
        packshot_assets = packshot_assets or [f"pack{i+1}" for i in range(packshot_count)]
        actual_packshot_count = min(len(packshot_assets), packshot_count)
        
        layouts = []
        
        # Generate layouts based on canvas orientation
        if is_portrait:
            # Stories format (1080x1920) - vertical layout
            layouts = self._generate_stories_layouts(
                brand, headline, subhead, bg_color, text_color, accent_color,
                packshot_assets[:actual_packshot_count], logo_asset,
                required_tiles, is_alcohol
            )
        elif is_landscape:
            # Facebook format (1200x628) - horizontal layout
            layouts = self._generate_landscape_layouts(
                brand, headline, subhead, bg_color, text_color, accent_color,
                packshot_assets[:actual_packshot_count], logo_asset,
                required_tiles, is_alcohol
            )
        else:
            # Square format (1080x1080) - Instagram
            layouts = self._generate_square_layouts(
                brand, headline, subhead, bg_color, text_color, accent_color,
                packshot_assets[:actual_packshot_count], logo_asset,
                required_tiles, is_alcohol
            )
        
        logger.info("layouts_generated_stub", count=len(layouts), canvas=canvas)
        return {"layouts": layouts}
    
    def _generate_square_layouts(
        self,
        brand: str,
        headline: str,
        subhead: str,
        bg_color: str,
        text_color: str,
        accent_color: str,
        packshot_assets: List[str],
        logo_asset: Optional[str],
        required_tiles: Dict[str, bool],
        is_alcohol: bool
    ) -> List[Dict[str, Any]]:
        """Generate layouts for 1080x1080 square format."""
        layouts = []
        
        # Layout 1: Hero Product Center (like Brancott Estate example)
        elements1 = [
            {"type": "background", "color": bg_color, "z": 0}
        ]
        
        # Large centered packshot
        if packshot_assets:
            elements1.append({
                "type": "packshot",
                "asset": packshot_assets[0],
                "x": 20, "y": 10, "width": 60, "height": 55, "z": 2
            })
        
        # Logo in top-left
        if logo_asset:
            elements1.append({
                "type": "logo",
                "asset": logo_asset,
                "x": 5, "y": 5, "width": 18, "height": 12, "z": 3
            })
        
        # Headline below packshot
        if headline:
            elements1.append({
                "type": "headline",
                "text": headline,
                "x": 5, "y": 68, "width": 90, "height": 10,
                "font_size": 42, "color": text_color, "z": 2
            })
        
        # Subhead
        if subhead:
            elements1.append({
                "type": "subhead",
                "text": subhead,
                "x": 5, "y": 79, "width": 90, "height": 8,
                "font_size": 24, "color": text_color, "z": 2
            })
        
        # Tesco tag
        if required_tiles.get("tesco_tag", True):
            elements1.append({
                "type": "tesco_tag",
                "text": "Available at Tesco",
                "x": 5, "y": 90, "width": 30, "height": 5, "z": 2
            })
        
        # Drinkaware for alcohol
        if is_alcohol:
            elements1.append({
                "type": "drinkaware",
                "x": 60, "y": 92, "width": 35, "height": 4,
                "color": text_color, "z": 2
            })
        
        layouts.append({"id": "layout_hero_center", "score": 0.95, "elements": elements1})
        
        # Layout 2: Split Layout (Product left, Text right)
        elements2 = [
            {"type": "background", "color": bg_color, "z": 0}
        ]
        
        if packshot_assets:
            elements2.append({
                "type": "packshot",
                "asset": packshot_assets[0],
                "x": 5, "y": 15, "width": 45, "height": 55, "z": 2
            })
        
        if logo_asset:
            elements2.append({
                "type": "logo",
                "asset": logo_asset,
                "x": 55, "y": 5, "width": 20, "height": 12, "z": 3
            })
        
        if headline:
            elements2.append({
                "type": "headline",
                "text": headline,
                "x": 52, "y": 25, "width": 45, "height": 15,
                "font_size": 36, "color": text_color, "z": 2
            })
        
        if subhead:
            elements2.append({
                "type": "subhead",
                "text": subhead,
                "x": 52, "y": 45, "width": 45, "height": 10,
                "font_size": 20, "color": text_color, "z": 2
            })
        
        if required_tiles.get("tesco_tag", True):
            elements2.append({
                "type": "tesco_tag",
                "text": "Available at Tesco",
                "x": 5, "y": 90, "width": 30, "height": 5, "z": 2
            })
        
        if is_alcohol:
            elements2.append({
                "type": "drinkaware",
                "x": 55, "y": 92, "width": 40, "height": 4,
                "color": text_color, "z": 2
            })
        
        layouts.append({"id": "layout_split", "score": 0.90, "elements": elements2})
        
        # Layout 3: Multi-Product Grid (if multiple packshots)
        if len(packshot_assets) >= 2:
            elements3 = [
                {"type": "background", "color": bg_color, "z": 0}
            ]
            
            # Arrange packshots in a grid
            for i, asset in enumerate(packshot_assets[:4]):
                row = i // 2
                col = i % 2
                elements3.append({
                    "type": "packshot",
                    "asset": asset,
                    "x": 8 + (col * 44), "y": 12 + (row * 35),
                    "width": 40, "height": 30, "z": 2
                })
            
            if logo_asset:
                elements3.append({
                    "type": "logo",
                    "asset": logo_asset,
                    "x": 38, "y": 2, "width": 24, "height": 8, "z": 3
                })
            
            if headline:
                elements3.append({
                    "type": "headline",
                    "text": headline,
                    "x": 5, "y": 78, "width": 90, "height": 8,
                    "font_size": 32, "color": text_color, "z": 2
                })
            
            if required_tiles.get("tesco_tag", True):
                elements3.append({
                    "type": "tesco_tag",
                    "text": "Available at Tesco",
                    "x": 5, "y": 90, "width": 30, "height": 5, "z": 2
                })
            
            if is_alcohol:
                elements3.append({
                    "type": "drinkaware",
                    "x": 55, "y": 92, "width": 40, "height": 4,
                    "color": text_color, "z": 2
                })
            
            layouts.append({"id": "layout_grid", "score": 0.88, "elements": elements3})
        else:
            # Alternative single-product layout: Bottom-heavy
            elements3 = [
                {"type": "background", "color": bg_color, "z": 0}
            ]
            
            if logo_asset:
                elements3.append({
                    "type": "logo",
                    "asset": logo_asset,
                    "x": 38, "y": 3, "width": 24, "height": 10, "z": 3
                })
            
            if headline:
                elements3.append({
                    "type": "headline",
                    "text": headline,
                    "x": 10, "y": 15, "width": 80, "height": 12,
                    "font_size": 40, "color": text_color, "z": 2
                })
            
            if packshot_assets:
                elements3.append({
                    "type": "packshot",
                    "asset": packshot_assets[0],
                    "x": 15, "y": 30, "width": 70, "height": 50, "z": 2
                })
            
            if required_tiles.get("tesco_tag", True):
                elements3.append({
                    "type": "tesco_tag",
                    "text": "Available at Tesco",
                    "x": 5, "y": 88, "width": 30, "height": 5, "z": 2
                })
            
            if is_alcohol:
                elements3.append({
                    "type": "drinkaware",
                    "x": 55, "y": 92, "width": 40, "height": 4,
                    "color": text_color, "z": 2
                })
            
            layouts.append({"id": "layout_text_top", "score": 0.85, "elements": elements3})
        
        return layouts
    
    def _generate_stories_layouts(
        self,
        brand: str,
        headline: str,
        subhead: str,
        bg_color: str,
        text_color: str,
        accent_color: str,
        packshot_assets: List[str],
        logo_asset: Optional[str],
        required_tiles: Dict[str, bool],
        is_alcohol: bool
    ) -> List[Dict[str, Any]]:
        """Generate layouts for 1080x1920 stories format."""
        layouts = []
        
        # Layout 1: Full-height hero
        elements1 = [
            {"type": "background", "color": bg_color, "z": 0}
        ]
        
        if logo_asset:
            elements1.append({
                "type": "logo",
                "asset": logo_asset,
                "x": 35, "y": 12, "width": 30, "height": 8, "z": 3
            })
        
        if packshot_assets:
            elements1.append({
                "type": "packshot",
                "asset": packshot_assets[0],
                "x": 15, "y": 22, "width": 70, "height": 40, "z": 2
            })
        
        if headline:
            elements1.append({
                "type": "headline",
                "text": headline,
                "x": 8, "y": 65, "width": 84, "height": 8,
                "font_size": 48, "color": text_color, "z": 2
            })
        
        if subhead:
            elements1.append({
                "type": "subhead",
                "text": subhead,
                "x": 8, "y": 74, "width": 84, "height": 5,
                "font_size": 28, "color": text_color, "z": 2
            })
        
        if required_tiles.get("tesco_tag", True):
            elements1.append({
                "type": "tesco_tag",
                "text": "Available at Tesco",
                "x": 8, "y": 82, "width": 35, "height": 4, "z": 2
            })
        
        if is_alcohol:
            elements1.append({
                "type": "drinkaware",
                "x": 30, "y": 88, "width": 40, "height": 3,
                "color": text_color, "z": 2
            })
        
        layouts.append({"id": "stories_hero", "score": 0.95, "elements": elements1})
        
        # Layout 2: Text at top
        elements2 = [
            {"type": "background", "color": bg_color, "z": 0}
        ]
        
        if logo_asset:
            elements2.append({
                "type": "logo",
                "asset": logo_asset,
                "x": 5, "y": 12, "width": 25, "height": 6, "z": 3
            })
        
        if headline:
            elements2.append({
                "type": "headline",
                "text": headline,
                "x": 8, "y": 20, "width": 84, "height": 10,
                "font_size": 44, "color": text_color, "z": 2
            })
        
        if packshot_assets:
            elements2.append({
                "type": "packshot",
                "asset": packshot_assets[0],
                "x": 10, "y": 35, "width": 80, "height": 45, "z": 2
            })
        
        if required_tiles.get("tesco_tag", True):
            elements2.append({
                "type": "tesco_tag",
                "text": "Available at Tesco",
                "x": 8, "y": 82, "width": 35, "height": 4, "z": 2
            })
        
        if is_alcohol:
            elements2.append({
                "type": "drinkaware",
                "x": 30, "y": 88, "width": 40, "height": 3,
                "color": text_color, "z": 2
            })
        
        layouts.append({"id": "stories_text_top", "score": 0.90, "elements": elements2})
        
        # Layout 3: Multi-product stack
        elements3 = [
            {"type": "background", "color": bg_color, "z": 0}
        ]
        
        if logo_asset:
            elements3.append({
                "type": "logo",
                "asset": logo_asset,
                "x": 35, "y": 12, "width": 30, "height": 6, "z": 3
            })
        
        for i, asset in enumerate(packshot_assets[:3]):
            elements3.append({
                "type": "packshot",
                "asset": asset,
                "x": 25 + (i * 5), "y": 22 + (i * 18),
                "width": 50, "height": 25, "z": 2 + i
            })
        
        if headline:
            elements3.append({
                "type": "headline",
                "text": headline,
                "x": 8, "y": 75, "width": 84, "height": 6,
                "font_size": 36, "color": text_color, "z": 2
            })
        
        if required_tiles.get("tesco_tag", True):
            elements3.append({
                "type": "tesco_tag",
                "text": "Available at Tesco",
                "x": 8, "y": 82, "width": 35, "height": 4, "z": 2
            })
        
        if is_alcohol:
            elements3.append({
                "type": "drinkaware",
                "x": 30, "y": 88, "width": 40, "height": 3,
                "color": text_color, "z": 2
            })
        
        layouts.append({"id": "stories_stack", "score": 0.85, "elements": elements3})
        
        return layouts
    
    def _generate_landscape_layouts(
        self,
        brand: str,
        headline: str,
        subhead: str,
        bg_color: str,
        text_color: str,
        accent_color: str,
        packshot_assets: List[str],
        logo_asset: Optional[str],
        required_tiles: Dict[str, bool],
        is_alcohol: bool
    ) -> List[Dict[str, Any]]:
        """Generate layouts for 1200x628 landscape format."""
        layouts = []
        
        # Layout 1: Product right, text left
        elements1 = [
            {"type": "background", "color": bg_color, "z": 0}
        ]
        
        if logo_asset:
            elements1.append({
                "type": "logo",
                "asset": logo_asset,
                "x": 5, "y": 8, "width": 18, "height": 15, "z": 3
            })
        
        if headline:
            elements1.append({
                "type": "headline",
                "text": headline,
                "x": 5, "y": 30, "width": 45, "height": 20,
                "font_size": 38, "color": text_color, "z": 2
            })
        
        if subhead:
            elements1.append({
                "type": "subhead",
                "text": subhead,
                "x": 5, "y": 55, "width": 45, "height": 15,
                "font_size": 22, "color": text_color, "z": 2
            })
        
        if packshot_assets:
            elements1.append({
                "type": "packshot",
                "asset": packshot_assets[0],
                "x": 55, "y": 10, "width": 40, "height": 70, "z": 2
            })
        
        if required_tiles.get("tesco_tag", True):
            elements1.append({
                "type": "tesco_tag",
                "text": "Available at Tesco",
                "x": 5, "y": 82, "width": 25, "height": 10, "z": 2
            })
        
        if is_alcohol:
            elements1.append({
                "type": "drinkaware",
                "x": 35, "y": 85, "width": 30, "height": 8,
                "color": text_color, "z": 2
            })
        
        layouts.append({"id": "landscape_right", "score": 0.95, "elements": elements1})
        
        # Layout 2: Product left, text right
        elements2 = [
            {"type": "background", "color": bg_color, "z": 0}
        ]
        
        if packshot_assets:
            elements2.append({
                "type": "packshot",
                "asset": packshot_assets[0],
                "x": 5, "y": 10, "width": 40, "height": 70, "z": 2
            })
        
        if logo_asset:
            elements2.append({
                "type": "logo",
                "asset": logo_asset,
                "x": 50, "y": 8, "width": 18, "height": 15, "z": 3
            })
        
        if headline:
            elements2.append({
                "type": "headline",
                "text": headline,
                "x": 50, "y": 28, "width": 45, "height": 20,
                "font_size": 36, "color": text_color, "z": 2
            })
        
        if subhead:
            elements2.append({
                "type": "subhead",
                "text": subhead,
                "x": 50, "y": 52, "width": 45, "height": 15,
                "font_size": 20, "color": text_color, "z": 2
            })
        
        if required_tiles.get("tesco_tag", True):
            elements2.append({
                "type": "tesco_tag",
                "text": "Available at Tesco",
                "x": 50, "y": 75, "width": 25, "height": 10, "z": 2
            })
        
        if is_alcohol:
            elements2.append({
                "type": "drinkaware",
                "x": 50, "y": 88, "width": 35, "height": 8,
                "color": text_color, "z": 2
            })
        
        layouts.append({"id": "landscape_left", "score": 0.90, "elements": elements2})
        
        # Layout 3: Center composition
        elements3 = [
            {"type": "background", "color": bg_color, "z": 0}
        ]
        
        if logo_asset:
            elements3.append({
                "type": "logo",
                "asset": logo_asset,
                "x": 5, "y": 8, "width": 15, "height": 15, "z": 3
            })
        
        if packshot_assets:
            elements3.append({
                "type": "packshot",
                "asset": packshot_assets[0],
                "x": 35, "y": 5, "width": 30, "height": 60, "z": 2
            })
        
        if headline:
            elements3.append({
                "type": "headline",
                "text": headline,
                "x": 10, "y": 70, "width": 80, "height": 12,
                "font_size": 32, "color": text_color, "z": 2
            })
        
        if required_tiles.get("tesco_tag", True):
            elements3.append({
                "type": "tesco_tag",
                "text": "Available at Tesco",
                "x": 5, "y": 85, "width": 25, "height": 10, "z": 2
            })
        
        if is_alcohol:
            elements3.append({
                "type": "drinkaware",
                "x": 65, "y": 88, "width": 30, "height": 8,
                "color": text_color, "z": 2
            })
        
        layouts.append({"id": "landscape_center", "score": 0.85, "elements": elements3})
        
        return layouts
    
    def _is_light_color(self, hex_color: str) -> bool:
        """Check if a color is light (for contrast purposes)."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        # Calculate perceived brightness
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return brightness > 128
    
    def moderate_copy(self, headline: str, subhead: str = "") -> Dict[str, Any]:
        """
        Check headline and subhead for compliance issues.
        """
        if self.is_available():
            try:
                prompt = COPY_MODERATION_PROMPT.format(
                    headline=headline,
                    subhead=subhead
                )
                response = self.call_llm(prompt, max_tokens=500, temperature=0.1)
                return self.extract_json(response)
            except Exception as e:
                logger.error("copy_moderation_llm_failed", error=str(e))
        
        # Fallback to deterministic checks
        return self._moderate_copy_deterministic(headline, subhead)
    
    def _moderate_copy_deterministic(self, headline: str, subhead: str) -> Dict[str, Any]:
        """Deterministic copy moderation using regex patterns."""
        issues = []
        text = f"{headline} {subhead}".lower()
        
        # Price/discount patterns
        if re.search(r'\b(price|discount|off|save|sale|%|£|deal)\b', text):
            issues.append({
                "code": "PRICE_REFERENCE",
                "message": "Price or discount reference detected. Remove pricing language."
            })
        
        # Competition patterns
        if re.search(r'\b(win|enter|contest|prize|giveaway|competition)\b', text):
            issues.append({
                "code": "COMPETITION_COPY",
                "message": "Competition or prize wording detected. Not allowed."
            })
        
        # Sustainability patterns
        if re.search(r'\b(sustainable|eco|green|carbon|environmental|planet)\b', text):
            issues.append({
                "code": "SUSTAINABILITY_CLAIM",
                "message": "Sustainability claim detected. Not allowed without approval."
            })
        
        # Charity patterns
        if re.search(r'\b(charity|donate|donation|support|cause)\b', text):
            issues.append({
                "code": "CHARITY_REFERENCE",
                "message": "Charity or donation reference detected. Not allowed."
            })
        
        # Claim patterns
        if re.search(r'\b(#1|number one|best|clinically|proven|survey|studies)\b', text):
            issues.append({
                "code": "UNSUBSTANTIATED_CLAIM",
                "message": "Claim detected that may require substantiation."
            })
        
        # Money-back guarantee
        if re.search(r'\b(money.?back|guarantee|refund)\b', text):
            issues.append({
                "code": "GUARANTEE_CLAIM",
                "message": "Money-back guarantee or similar claim detected. Not allowed."
            })
        
        return {
            "ok": len(issues) == 0,
            "issues": issues
        }
    
    def classify_content(self, text: str) -> Dict[str, Any]:
        """
        Classify text content for borderline cases.
        Returns: allowed, disallowed, or needs_edit with suggestions.
        """
        if self.is_available():
            try:
                prompt = CONTENT_CLASSIFICATION_PROMPT.format(text=text)
                response = self.call_llm(prompt, max_tokens=300, temperature=0.1)
                return self.extract_json(response)
            except Exception as e:
                logger.error("content_classification_failed", error=str(e))
        
        # Fallback
        moderation = self._moderate_copy_deterministic(text, "")
        if moderation["ok"]:
            return {"classification": "allowed", "reason": "No issues detected"}
        else:
            return {
                "classification": "disallowed",
                "reason": moderation["issues"][0]["message"] if moderation["issues"] else "Issue detected",
                "suggested_edit": ""
            }

    def detect_tone(
        self,
        brand: str,
        colors: List[str],
        headline: str,
        category: str = "general"
    ) -> Dict[str, Any]:
        """
        Analyze brand identity and detect the appropriate messaging tone.
        
        Returns:
            Dict with detected_tone, color_mood, suggested_style, and reasoning.
        """
        if self.is_available():
            try:
                prompt = TONE_DETECTION_PROMPT.format(
                    brand=brand,
                    colors=", ".join(colors) if colors else "N/A",
                    headline=headline,
                    category=category
                )
                response = self.call_llm(prompt, max_tokens=400, temperature=0.2)
                return self.extract_json(response)
            except Exception as e:
                logger.error("tone_detection_failed", error=str(e))
        
        # Fallback deterministic tone detection
        return self._detect_tone_deterministic(brand, colors, headline, category)
    
    def _detect_tone_deterministic(
        self,
        brand: str,
        colors: List[str],
        headline: str,
        category: str
    ) -> Dict[str, Any]:
        """Deterministic tone detection based on heuristics."""
        # Analyze color mood
        color_mood = "neutral"
        if colors:
            primary = colors[0].lower()
            warm_hues = ["#ff", "#f0", "#e8", "#f5", "#fa", "#ff8", "#ffa", "#ffc"]
            cool_hues = ["#00", "#0a", "#1a", "#2a", "#3a", "#0ff", "#00f", "#088"]
            vibrant_markers = ["#f00", "#ff0", "#0f0", "#0ff", "#f0f"]
            
            if any(primary.startswith(h) for h in warm_hues):
                color_mood = "warm"
            elif any(primary.startswith(h) for h in cool_hues):
                color_mood = "cool"
            elif any(m in primary for m in vibrant_markers):
                color_mood = "vibrant"
        
        # Analyze headline for tone markers
        headline_lower = headline.lower()
        
        if any(w in headline_lower for w in ["new", "introducing", "discover", "experience"]):
            detected_tone = "premium"
        elif any(w in headline_lower for w in ["!", "amazing", "wow", "incredible", "love"]):
            detected_tone = "playful"
        elif any(w in headline_lower for w in ["essential", "trusted", "quality", "heritage"]):
            detected_tone = "classic"
        elif len(headline.split()) <= 3 or any(w in headline_lower for w in ["simple", "clean", "pure"]):
            detected_tone = "minimal"
        else:
            detected_tone = "bold"
        
        # Determine layout type based on tone
        layout_mapping = {
            "bold": "hero-centered",
            "minimal": "text-overlay",
            "premium": "split",
            "playful": "multi-product",
            "classic": "hero-centered"
        }
        
        emphasis_mapping = {
            "bold": "product",
            "minimal": "message",
            "premium": "brand",
            "playful": "product",
            "classic": "brand"
        }
        
        return {
            "detected_tone": detected_tone,
            "color_mood": color_mood,
            "suggested_style": {
                "layout_type": layout_mapping.get(detected_tone, "hero-centered"),
                "emphasis": emphasis_mapping.get(detected_tone, "product"),
                "contrast_level": "high" if detected_tone in ["bold", "playful"] else "medium"
            },
            "reasoning": f"Detected {detected_tone} tone based on headline style and {color_mood} color palette."
        }

    def generate_layouts_with_tone(
        self,
        brand: str,
        headline: str,
        subhead: str,
        colors: List[str],
        packshot_count: int,
        required_tiles: Dict[str, bool],
        canvas: str = "1080x1920",
        is_alcohol: bool = False,
        packshot_assets: List[str] = None,
        logo_asset: Optional[str] = None,
        style_preset: Optional[str] = None,
        category: str = "general"
    ) -> Dict[str, Any]:
        """
        Enhanced layout generation that first detects tone, then generates layouts accordingly.
        
        Args:
            style_preset: Optional override for tone ("bold", "minimal", "premium", "playful", "classic")
            category: Product category for tone context
        """
        # Detect or use preset tone
        if style_preset:
            tone_info = {
                "detected_tone": style_preset,
                "color_mood": "neutral",
                "suggested_style": {
                    "layout_type": "hero-centered",
                    "emphasis": "product",
                    "contrast_level": "high"
                }
            }
        else:
            tone_info = self.detect_tone(brand, colors, headline, category)
        
        # Generate layouts with tone context
        layouts = self.generate_layouts(
            brand=brand,
            headline=headline,
            subhead=subhead,
            colors=colors,
            packshot_count=packshot_count,
            required_tiles=required_tiles,
            canvas=canvas,
            is_alcohol=is_alcohol,
            packshot_assets=packshot_assets,
            logo_asset=logo_asset
        )
        
        # Enrich with tone metadata
        layouts["tone_analysis"] = tone_info
        layouts["style_applied"] = style_preset or tone_info.get("detected_tone", "bold")
        
        logger.info(
            "layouts_generated_with_tone",
            tone=layouts["style_applied"],
            layout_count=len(layouts.get("layouts", []))
        )
        
        return layouts


# Singleton instance
llm_client = LLMClient()
