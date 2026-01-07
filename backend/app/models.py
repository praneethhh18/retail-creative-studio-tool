"""
Pydantic models for the Retail Media Creative Tool API.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class IssueSeverity(str, Enum):
    """Severity levels for validation issues."""
    HARD = "hard"
    WARN = "warn"


class ValidationIssue(BaseModel):
    """A single validation issue found during layout validation."""
    severity: IssueSeverity
    code: str
    message: str
    fix_suggestion: Optional[str] = None
    element_id: Optional[str] = None
    bounding_box: Optional[dict] = None


class ValidationResult(BaseModel):
    """Result of validating a layout."""
    ok: bool
    issues: List[ValidationIssue] = []
    checked_rules: List[str] = []


class ElementBase(BaseModel):
    """Base class for layout elements."""
    type: str
    x: float = Field(ge=0, le=100, description="X position as percentage (0-100)")
    y: float = Field(ge=0, le=100, description="Y position as percentage (0-100)")
    width: float = Field(ge=0, le=100, description="Width as percentage (0-100)")
    height: float = Field(ge=0, le=100, description="Height as percentage (0-100)")
    z: int = Field(default=0, description="Z-index for layering")


class BackgroundElement(BaseModel):
    """Background element with solid color."""
    type: Literal["background"] = "background"
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class PackshotElement(ElementBase):
    """Product packshot element."""
    type: Literal["packshot"] = "packshot"
    asset: str


class LogoElement(ElementBase):
    """Brand logo element."""
    type: Literal["logo"] = "logo"
    asset: str


class TextElement(ElementBase):
    """Text element (headline, subhead)."""
    type: Literal["headline", "subhead"]
    text: str
    font_size: int = Field(ge=8, le=200, description="Font size in px for 1080x1920 base")
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    font_family: Optional[str] = "Arial"


class TescoTagElement(ElementBase):
    """Tesco retailer tag element."""
    type: Literal["tesco_tag"] = "tesco_tag"
    text: str


class ValueTileElement(ElementBase):
    """Value tile element (non-moveable)."""
    type: Literal["value_tile"] = "value_tile"
    text: Optional[str] = None


class DrinkawareElement(ElementBase):
    """Drinkaware lock-up for alcohol campaigns."""
    type: Literal["drinkaware"] = "drinkaware"
    color: Literal["#000000", "#FFFFFF", "#ffffff", "#000", "#fff"]


class LayoutElement(BaseModel):
    """Union type for all possible layout elements."""
    type: str
    asset: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    z: Optional[int] = 0
    text: Optional[str] = None
    font_size: Optional[int] = None
    color: Optional[str] = None
    font_family: Optional[str] = None


class Layout(BaseModel):
    """A complete layout with all elements."""
    id: str
    score: float = Field(ge=0, le=1)
    elements: List[LayoutElement]


class LayoutsResponse(BaseModel):
    """Response containing multiple layout options."""
    layouts: List[Layout]


class UploadResponse(BaseModel):
    """Response from uploading an asset."""
    original: str
    cleaned: str
    palette: List[str] = []
    asset_id: str


class GenRequest(BaseModel):
    """Request for generating layouts."""
    # New API fields (from frontend)
    packshot_ids: List[str] = []
    logo_ids: List[str] = []
    background_id: Optional[str] = None
    palette: List[str] = []
    channel: Optional[str] = None
    user_prompt: Optional[str] = None
    # Legacy fields (original API)
    brand: str = ""
    headline: str = ""
    subhead: Optional[str] = ""
    colors: List[str] = []
    packshot_count: int = Field(ge=1, le=5, default=1)
    required_tiles: dict = Field(default_factory=lambda: {"tesco_tag": True, "value_tile": False})
    canvas: str = "1080x1920"
    is_alcohol: bool = False
    packshot_assets: List[str] = []
    logo_asset: Optional[str] = None


class ValidateRequest(BaseModel):
    """Request for validating a layout."""
    layout: Layout
    canvas_size: str = "1080x1920"
    is_alcohol: bool = False
    channel: Literal["facebook", "instagram", "stories", "in_store"] = "stories"


class ExportRequest(BaseModel):
    """Request for exporting a creative."""
    layout: Layout
    assets_map: dict = Field(default_factory=dict, description="Map of asset IDs to file paths")
    sizes: List[str] = Field(default=["1080x1080", "1080x1920", "1200x628"])
    format: Literal["jpeg", "png"] = "jpeg"
    max_file_size_kb: int = 500


class ExportResponse(BaseModel):
    """Response from exporting creatives."""
    files: List[dict]  # [{size, path, format, file_size_kb}]
    warnings: List[str] = []


class CopyModerationRequest(BaseModel):
    """Request for moderating copy text."""
    headline: str
    subhead: Optional[str] = ""


class CopyModerationResult(BaseModel):
    """Result of copy moderation check."""
    ok: bool
    issues: List[dict] = []


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    services: dict = {}
