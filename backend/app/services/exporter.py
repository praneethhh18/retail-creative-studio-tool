"""
Exporter Service for generating and compressing final creative images.
Handles multi-format export and file size optimization.
"""
import os
import io
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image
import structlog

from app.models import Layout, ExportResponse
from app.utils import EXPORTS_DIR, parse_canvas_size, generate_asset_id
from app.services.renderer import renderer_service

logger = structlog.get_logger()

# Export configuration
MAX_FILE_SIZE_KB = 500
JPEG_QUALITY_START = 95
JPEG_QUALITY_MIN = 60
PNG_COMPRESSION_LEVEL = 9


class ExporterService:
    """Service for exporting and compressing creative images."""
    
    def __init__(self):
        self.output_dir = EXPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_layout(
        self,
        layout: Layout,
        assets_map: Dict[str, str],
        sizes: List[str],
        format: str = "jpeg",
        max_file_size_kb: int = MAX_FILE_SIZE_KB
    ) -> ExportResponse:
        """
        Export a layout in multiple sizes.
        
        Args:
            layout: Layout to export
            assets_map: Map of asset IDs to file paths
            sizes: List of target sizes (e.g., ["1080x1080", "1080x1920"])
            format: Output format ("jpeg" or "png")
            max_file_size_kb: Maximum file size in KB
            
        Returns:
            ExportResponse with file paths and any warnings
        """
        files = []
        warnings = []
        export_id = generate_asset_id()
        
        # Base size for the layout
        base_size = "1080x1920"
        
        for target_size in sizes:
            try:
                # Reformat layout for target size if needed
                if target_size != base_size:
                    reformatted_layout = renderer_service.reformat_layout_for_size(
                        layout, base_size, target_size
                    )
                else:
                    reformatted_layout = layout
                
                # Render the layout
                temp_path = self.output_dir / f"temp_{export_id}_{target_size}.png"
                renderer_service.render_layout(
                    reformatted_layout,
                    assets_map,
                    target_size,
                    str(temp_path)
                )
                
                # Compress to target format and size
                if format.lower() == "jpeg":
                    final_path, file_size, compression_warning = self.export_jpeg_under_500kb(
                        str(temp_path),
                        max_file_size_kb=max_file_size_kb
                    )
                else:
                    final_path, file_size, compression_warning = self.export_png_optimized(
                        str(temp_path),
                        max_file_size_kb=max_file_size_kb
                    )
                
                if compression_warning:
                    warnings.append(compression_warning)
                
                # Clean up temp file
                if Path(temp_path).exists() and str(temp_path) != final_path:
                    os.remove(temp_path)
                
                files.append({
                    "size": target_size,
                    "path": final_path,
                    "format": format,
                    "file_size_kb": file_size
                })
                
                logger.info(
                    "export_success",
                    layout_id=layout.id,
                    size=target_size,
                    format=format,
                    file_size_kb=file_size
                )
                
            except Exception as e:
                logger.error("export_failed", size=target_size, error=str(e))
                warnings.append(f"Failed to export {target_size}: {str(e)}")
        
        return ExportResponse(files=files, warnings=warnings)
    
    def export_jpeg_under_500kb(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        max_file_size_kb: int = MAX_FILE_SIZE_KB
    ) -> Tuple[str, int, Optional[str]]:
        """
        Export image as JPEG under target file size.
        Uses iterative compression: quality reduction, then resize if needed.
        
        Args:
            input_path: Path to input image
            output_path: Optional output path
            max_file_size_kb: Maximum file size in KB
            
        Returns:
            Tuple of (output_path, final_size_kb, warning_message)
        """
        input_path = Path(input_path)
        
        if output_path is None:
            output_path = self.output_dir / f"{input_path.stem}_compressed.jpg"
        else:
            output_path = Path(output_path)
        
        # Load image
        img = Image.open(input_path).convert("RGB")
        original_size = img.size
        
        max_bytes = max_file_size_kb * 1024
        warning = None
        
        # Try progressive quality reduction
        for quality in range(JPEG_QUALITY_START, JPEG_QUALITY_MIN - 1, -5):
            buffer = io.BytesIO()
            img.save(
                buffer,
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=True
            )
            size = buffer.tell()
            
            if size <= max_bytes:
                # Success! Save to file
                with open(output_path, "wb") as f:
                    f.write(buffer.getvalue())
                
                return str(output_path), size // 1024, None
        
        # Quality reduction wasn't enough, try resizing
        for scale in [0.9, 0.8, 0.7, 0.6, 0.5]:
            new_size = (int(original_size[0] * scale), int(original_size[1] * scale))
            resized = img.resize(new_size, Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            resized.save(
                buffer,
                format="JPEG",
                quality=JPEG_QUALITY_MIN,
                optimize=True,
                progressive=True
            )
            size = buffer.tell()
            
            if size <= max_bytes:
                # Save resized image
                with open(output_path, "wb") as f:
                    f.write(buffer.getvalue())
                
                warning = f"Image was resized to {new_size[0]}x{new_size[1]} to meet size limit"
                return str(output_path), size // 1024, warning
        
        # Last resort: save at minimum settings
        buffer = io.BytesIO()
        final_scale = 0.4
        final_size = (int(original_size[0] * final_scale), int(original_size[1] * final_scale))
        resized = img.resize(final_size, Image.Resampling.LANCZOS)
        resized.save(
            buffer,
            format="JPEG",
            quality=JPEG_QUALITY_MIN,
            optimize=True,
            progressive=True
        )
        
        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())
        
        final_kb = buffer.tell() // 1024
        
        if final_kb > max_file_size_kb:
            warning = f"Could not achieve {max_file_size_kb}KB target. Final size: {final_kb}KB. Consider simplifying the creative."
        else:
            warning = f"Image significantly resized to {final_size[0]}x{final_size[1]} to meet size limit"
        
        return str(output_path), final_kb, warning
    
    def export_png_optimized(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        max_file_size_kb: int = MAX_FILE_SIZE_KB
    ) -> Tuple[str, int, Optional[str]]:
        """
        Export image as optimized PNG.
        
        Args:
            input_path: Path to input image
            output_path: Optional output path
            max_file_size_kb: Maximum file size in KB
            
        Returns:
            Tuple of (output_path, final_size_kb, warning_message)
        """
        input_path = Path(input_path)
        
        if output_path is None:
            output_path = self.output_dir / f"{input_path.stem}_optimized.png"
        else:
            output_path = Path(output_path)
        
        # Load image
        img = Image.open(input_path)
        
        # Keep RGBA for transparency support
        if img.mode not in ["RGB", "RGBA"]:
            img = img.convert("RGBA")
        
        max_bytes = max_file_size_kb * 1024
        warning = None
        original_size = img.size
        
        # Try optimized save first
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True, compress_level=PNG_COMPRESSION_LEVEL)
        size = buffer.tell()
        
        if size <= max_bytes:
            with open(output_path, "wb") as f:
                f.write(buffer.getvalue())
            return str(output_path), size // 1024, None
        
        # Try color quantization for smaller file
        if img.mode == "RGBA":
            # Quantize while preserving alpha
            quantized = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
            quantized = quantized.convert("RGBA")
        else:
            quantized = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
            quantized = quantized.convert("RGB")
        
        buffer = io.BytesIO()
        quantized.save(buffer, format="PNG", optimize=True, compress_level=PNG_COMPRESSION_LEVEL)
        size = buffer.tell()
        
        if size <= max_bytes:
            with open(output_path, "wb") as f:
                f.write(buffer.getvalue())
            return str(output_path), size // 1024, None
        
        # Try resizing
        for scale in [0.9, 0.8, 0.7, 0.6, 0.5]:
            new_size = (int(original_size[0] * scale), int(original_size[1] * scale))
            resized = quantized.resize(new_size, Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            resized.save(buffer, format="PNG", optimize=True, compress_level=PNG_COMPRESSION_LEVEL)
            size = buffer.tell()
            
            if size <= max_bytes:
                with open(output_path, "wb") as f:
                    f.write(buffer.getvalue())
                warning = f"Image was resized to {new_size[0]}x{new_size[1]} to meet size limit"
                return str(output_path), size // 1024, warning
        
        # Save best effort
        final_scale = 0.5
        final_size = (int(original_size[0] * final_scale), int(original_size[1] * final_scale))
        resized = quantized.resize(final_size, Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        resized.save(buffer, format="PNG", optimize=True, compress_level=PNG_COMPRESSION_LEVEL)
        
        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())
        
        final_kb = buffer.tell() // 1024
        
        if final_kb > max_file_size_kb:
            warning = f"Could not achieve {max_file_size_kb}KB target. Final size: {final_kb}KB. Consider using JPEG format."
        else:
            warning = f"Image resized to {final_size[0]}x{final_size[1]} to meet size limit"
        
        return str(output_path), final_kb, warning
    
    def create_export_zip(
        self,
        files: List[Dict],
        zip_name: Optional[str] = None
    ) -> str:
        """
        Create a ZIP file containing all exported images.
        
        Args:
            files: List of file dictionaries with 'path' keys
            zip_name: Optional name for ZIP file
            
        Returns:
            Path to ZIP file
        """
        if zip_name is None:
            zip_name = f"creative_export_{generate_asset_id()}.zip"
        
        zip_path = self.output_dir / zip_name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_info in files:
                file_path = Path(file_info["path"])
                if file_path.exists():
                    # Use size as folder structure
                    arcname = f"{file_info.get('size', 'export')}/{file_path.name}"
                    zf.write(file_path, arcname)
        
        logger.info("zip_created", path=str(zip_path), file_count=len(files))
        return str(zip_path)
    
    def cleanup_temp_files(self, export_id: str) -> None:
        """Clean up temporary files from an export."""
        for temp_file in self.output_dir.glob(f"temp_{export_id}_*"):
            try:
                os.remove(temp_file)
            except OSError:
                pass


# Singleton instance
exporter_service = ExporterService()
