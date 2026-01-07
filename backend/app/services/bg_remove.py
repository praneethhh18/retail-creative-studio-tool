"""
Background Removal Service using rembg.
Optionally supports Segment-Anything (SAM) integration.
"""
import os
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import structlog

from app.utils import ASSETS_DIR, trim_transparent_borders, generate_asset_id

logger = structlog.get_logger()

# Try to import rembg
try:
    from rembg import remove as rembg_remove
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    logger.warning("rembg_not_available", message="rembg not installed, background removal will be limited")

# SAM Integration (commented out for optional use)
# To enable SAM, install segment-anything and uncomment below
SAM_AVAILABLE = False
"""
try:
    from segment_anything import sam_model_registry, SamPredictor
    SAM_AVAILABLE = True
    
    # Load SAM model (requires downloading checkpoint)
    SAM_CHECKPOINT = os.getenv("SAM_CHECKPOINT", "sam_vit_h_4b8939.pth")
    SAM_MODEL_TYPE = os.getenv("SAM_MODEL_TYPE", "vit_h")
    
    if Path(SAM_CHECKPOINT).exists():
        sam = sam_model_registry[SAM_MODEL_TYPE](checkpoint=SAM_CHECKPOINT)
        sam_predictor = SamPredictor(sam)
    else:
        SAM_AVAILABLE = False
        logger.warning("sam_checkpoint_missing", checkpoint=SAM_CHECKPOINT)
except ImportError:
    SAM_AVAILABLE = False
    logger.info("sam_not_available", message="Segment-Anything not installed")
"""


class BackgroundRemovalService:
    """Service for removing backgrounds from product images."""
    
    def __init__(self):
        self.use_sam = SAM_AVAILABLE and os.getenv("USE_SAM", "false").lower() == "true"
        logger.info(
            "bg_removal_init",
            rembg_available=REMBG_AVAILABLE,
            sam_available=SAM_AVAILABLE,
            using_sam=self.use_sam
        )
    
    def remove_background(
        self, 
        input_path: str, 
        output_path: Optional[str] = None,
        trim_borders: bool = True
    ) -> Tuple[str, bool]:
        """
        Remove background from an image.
        
        Args:
            input_path: Path to input image
            output_path: Optional path for output. If None, generates automatically.
            trim_borders: Whether to trim transparent borders after removal
            
        Returns:
            Tuple of (output_path, success)
        """
        input_path = Path(input_path)
        
        if output_path is None:
            output_path = ASSETS_DIR / f"{input_path.stem}_cleaned_{generate_asset_id()}.png"
        else:
            output_path = Path(output_path)
        
        try:
            # Open input image
            input_image = Image.open(input_path)
            
            # Use SAM if available and enabled
            if self.use_sam and SAM_AVAILABLE:
                result = self._remove_with_sam(input_image)
            elif REMBG_AVAILABLE:
                result = self._remove_with_rembg(input_image)
            else:
                # Fallback: just convert to RGBA and return
                logger.warning("no_bg_removal_available", 
                              message="No background removal library available, returning original")
                result = input_image.convert("RGBA")
            
            # Trim transparent borders if requested
            if trim_borders:
                result = trim_transparent_borders(result)
            
            # Optimize PNG
            result = self._optimize_png(result)
            
            # Save result
            result.save(str(output_path), "PNG", optimize=True)
            
            logger.info("bg_removal_success", input=str(input_path), output=str(output_path))
            return str(output_path), True
            
        except Exception as e:
            logger.error("bg_removal_failed", error=str(e), input=str(input_path))
            # Return original as fallback
            try:
                original = Image.open(input_path).convert("RGBA")
                original.save(str(output_path), "PNG")
                return str(output_path), False
            except:
                return str(input_path), False
    
    def _remove_with_rembg(self, image: Image.Image) -> Image.Image:
        """Remove background using rembg library."""
        return rembg_remove(image)
    
    def _remove_with_sam(self, image: Image.Image) -> Image.Image:
        """
        Remove background using Segment-Anything Model.
        This is a placeholder - actual implementation requires SAM setup.
        """
        # SAM implementation would go here
        # For now, fall back to rembg
        logger.info("sam_fallback_to_rembg", message="SAM not fully configured, using rembg")
        if REMBG_AVAILABLE:
            return self._remove_with_rembg(image)
        return image.convert("RGBA")
    
    def _optimize_png(self, image: Image.Image) -> Image.Image:
        """Optimize PNG image for smaller file size."""
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        # Quantize colors while preserving alpha
        # This reduces file size while maintaining quality
        try:
            # Split into RGB and alpha
            if image.mode == "RGBA":
                r, g, b, a = image.split()
                rgb = Image.merge("RGB", (r, g, b))
                
                # Quantize RGB
                rgb_quantized = rgb.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
                rgb_quantized = rgb_quantized.convert("RGB")
                
                # Merge back with alpha
                r, g, b = rgb_quantized.split()
                image = Image.merge("RGBA", (r, g, b, a))
        except Exception as e:
            logger.warning("png_optimization_failed", error=str(e))
        
        return image
    
    def batch_remove_backgrounds(
        self, 
        input_paths: list,
        output_dir: Optional[str] = None
    ) -> list:
        """
        Remove backgrounds from multiple images.
        
        Args:
            input_paths: List of input image paths
            output_dir: Optional output directory
            
        Returns:
            List of (output_path, success) tuples
        """
        results = []
        output_dir = Path(output_dir) if output_dir else ASSETS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for input_path in input_paths:
            input_path = Path(input_path)
            output_path = output_dir / f"{input_path.stem}_cleaned.png"
            result = self.remove_background(str(input_path), str(output_path))
            results.append(result)
        
        return results


# Singleton instance
bg_removal_service = BackgroundRemovalService()
