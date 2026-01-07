"""
Export Routes - Handle image rendering and export with adaptive resizing.
"""
import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import structlog

from app.models import ExportRequest, ExportResponse, Layout
from app.services.exporter import exporter_service
from app.services.renderer import renderer_service
from app.services.adaptive_resizer import adaptive_resizer, FORMATS
from app.utils import ASSETS_DIR, EXPORTS_DIR, parse_canvas_size

logger = structlog.get_logger()

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/formats")
async def get_available_formats():
    """
    Get all available export formats with their configurations.
    """
    formats = {}
    for size, config in FORMATS.items():
        formats[size] = {
            "name": config.name,
            "width": config.width,
            "height": config.height,
            "aspect_ratio": round(config.aspect_ratio, 2),
            "platform": config.platform,
            "has_safe_zones": config.safe_zone_top_pct > 0 or config.safe_zone_bottom_pct > 0
        }
    return {"formats": formats}


@router.post("/image", response_model=ExportResponse)
async def export_image(request: ExportRequest):
    """
    Export a layout as images in multiple sizes.
    
    Request body:
    - layout: Layout object to render
    - assets_map: Dict mapping asset IDs to file paths
    - sizes: List of target sizes (e.g., ["1080x1080", "1080x1920", "1200x628"])
    - format: "jpeg" or "png"
    - max_file_size_kb: Maximum file size (default 500KB)
    
    Returns:
    - files: List of exported files with size, path, format, and file_size_kb
    - warnings: Any warnings during export
    """
    try:
        logger.info("export_image_request", 
                   layout_id=request.layout.id,
                   assets_map_keys=list(request.assets_map.keys())[:10],
                   sizes=request.sizes)
        
        # Build full asset paths with comprehensive mapping
        assets_map = {}
        for asset_id, path in request.assets_map.items():
            # Handle both relative and absolute paths
            if path.startswith("/assets/"):
                full_path = ASSETS_DIR / path.replace("/assets/", "")
            elif not os.path.isabs(path):
                full_path = ASSETS_DIR / path
            else:
                full_path = Path(path)
            
            # Store the full path
            full_path_str = str(full_path)
            
            # Map by original key
            assets_map[asset_id] = full_path_str
            # Also map by the original path for direct lookups
            assets_map[path] = full_path_str
            # Map by filename only
            filename = Path(path).name
            if filename:
                assets_map[filename] = full_path_str
            # Map with /assets/ prefix
            if not path.startswith("/assets/"):
                assets_map[f"/assets/{path}"] = full_path_str
                assets_map[f"/assets/{filename}"] = full_path_str
        
        logger.debug("assets_map_built", mapped_keys=list(assets_map.keys())[:15])
        
        result = exporter_service.export_layout(
            layout=request.layout,
            assets_map=assets_map,
            sizes=request.sizes,
            format=request.format,
            max_file_size_kb=request.max_file_size_kb
        )
        
        # Convert file paths to URLs
        for file_info in result.files:
            path = Path(file_info["path"])
            file_info["url"] = f"/exports/{path.name}"
        
        logger.info(
            "export_complete",
            file_count=len(result.files),
            format=request.format,
            sizes=request.sizes
        )
        
        return result
        
    except Exception as e:
        logger.error("export_failed", error=str(e), layout_id=request.layout.id if request.layout else "unknown")
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )


@router.post("/adaptive")
async def export_adaptive(
    layout: Layout,
    assets_map: dict,
    source_format: str = "1080x1920",
    target_formats: Optional[List[str]] = None,
    format: str = "jpeg",
    max_file_size_kb: int = 500
):
    """
    Export layout with intelligent adaptive resizing.
    
    Uses Adaptive Resizer to intelligently reflow layouts for different
    aspect ratios, ensuring visual hierarchy and compliance are maintained.
    
    Args:
        layout: Original layout
        assets_map: Asset ID to path mapping
        source_format: Original format (default: 1080x1920)
        target_formats: List of target formats (default: all standard formats)
        format: Output format (jpeg/png)
        max_file_size_kb: Maximum file size
    
    Returns:
        Exported files for all target formats
    """
    try:
        if target_formats is None:
            target_formats = ["1080x1080", "1080x1920", "1200x628"]
        
        # Adapt layouts for each target format
        adapted_layouts = adaptive_resizer.batch_adapt(
            layout, source_format, target_formats
        )
        
        files = []
        warnings = []
        
        # Build full asset paths
        full_assets_map = {}
        for asset_id, path in assets_map.items():
            if path.startswith("/assets/"):
                full_path = ASSETS_DIR / path.replace("/assets/", "")
            elif not os.path.isabs(path):
                full_path = ASSETS_DIR / path
            else:
                full_path = Path(path)
            full_assets_map[asset_id] = str(full_path)
        
        # Export each adapted layout
        for target_format, adapted_layout in adapted_layouts.items():
            try:
                result = exporter_service.export_layout(
                    layout=adapted_layout,
                    assets_map=full_assets_map,
                    sizes=[target_format],
                    format=format,
                    max_file_size_kb=max_file_size_kb
                )
                
                for file_info in result.files:
                    path = Path(file_info["path"])
                    file_info["url"] = f"/exports/{path.name}"
                    file_info["adaptation_strategy"] = adaptive_resizer.determine_strategy(
                        source_format, target_format
                    ).value
                    files.append(file_info)
                
                warnings.extend(result.warnings)
                
            except Exception as e:
                warnings.append(f"Failed to export {target_format}: {str(e)}")
        
        return {
            "files": files,
            "warnings": warnings,
            "adaptation_info": {
                "source_format": source_format,
                "target_formats": target_formats,
                "successfully_exported": len(files)
            }
        }
        
    except Exception as e:
        logger.error("adaptive_export_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Adaptive export failed: {str(e)}"
        )


@router.post("/batch")
async def export_batch(
    layout: Layout,
    assets_map: dict,
    format: str = "jpeg"
):
    """
    Export layout in all standard sizes (1080x1080, 1080x1920, 1200x628).
    
    Convenience endpoint for exporting all common formats at once.
    """
    request = ExportRequest(
        layout=layout,
        assets_map=assets_map,
        sizes=["1080x1080", "1080x1920", "1200x628"],
        format=format
    )
    
    return await export_image(request)


@router.post("/zip")
async def export_zip(request: ExportRequest):
    """
    Export layout and return as a ZIP file containing all sizes.
    """
    try:
        # First, export all images
        result = await export_image(request)
        
        if not result.files:
            raise HTTPException(status_code=400, detail="No files were exported")
        
        # Create ZIP
        zip_path = exporter_service.create_export_zip(result.files)
        
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=Path(zip_path).name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("zip_export_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"ZIP export failed: {str(e)}"
        )


@router.get("/preview/{layout_id}")
async def preview_layout(
    layout_id: str,
    size: str = "1080x1920"
):
    """
    Get a preview of a previously exported layout.
    """
    # Look for matching export
    for ext in [".jpg", ".jpeg", ".png"]:
        preview_path = EXPORTS_DIR / f"render_{layout_id}_{size.replace('x', '_')}{ext}"
        if preview_path.exists():
            return FileResponse(
                path=str(preview_path),
                media_type=f"image/{ext.lstrip('.')}"
            )
    
    raise HTTPException(status_code=404, detail=f"Preview not found for layout {layout_id}")


@router.get("/download/{filename}")
async def download_export(filename: str):
    """
    Download an exported file by filename.
    """
    file_path = EXPORTS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    
    # Determine media type
    if filename.endswith(".zip"):
        media_type = "application/zip"
    elif filename.endswith(".png"):
        media_type = "image/png"
    else:
        media_type = "image/jpeg"
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename
    )


@router.post("/reformat")
async def reformat_layout(
    layout: Layout,
    source_size: str = "1080x1920",
    target_size: str = "1080x1080"
):
    """
    Reformat a layout for a different canvas size.
    
    Applies proportional scaling and reflow heuristics.
    Returns the reformatted layout JSON.
    """
    try:
        reformatted = renderer_service.reformat_layout_for_size(
            layout=layout,
            source_size=source_size,
            target_size=target_size
        )
        
        return reformatted.model_dump()
        
    except Exception as e:
        logger.error("reformat_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Reformat failed: {str(e)}"
        )


@router.delete("/cleanup")
async def cleanup_exports(older_than_hours: int = 24):
    """
    Clean up old export files.
    
    Removes export files older than the specified number of hours.
    """
    import time
    
    cutoff_time = time.time() - (older_than_hours * 3600)
    deleted = []
    
    for file_path in EXPORTS_DIR.glob("*"):
        if file_path.stat().st_mtime < cutoff_time:
            try:
                os.remove(file_path)
                deleted.append(file_path.name)
            except OSError:
                pass
    
    return {"deleted": deleted, "count": len(deleted)}
