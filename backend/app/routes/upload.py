"""
Upload Routes - Handle file uploads for packshots, logos, and backgrounds.
"""
import os
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
import structlog

from app.models import UploadResponse
from app.utils import (
    ASSETS_DIR, generate_asset_id, create_safe_filename,
    is_valid_image_mime, extract_dominant_colors
)
from app.services.bg_remove import bg_removal_service

logger = structlog.get_logger()

router = APIRouter(prefix="/upload", tags=["Upload"])

# Configuration
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


@router.post("/packshot", response_model=UploadResponse)
async def upload_packshot(
    file: UploadFile = File(...),
    remove_background: bool = Form(default=True)
):
    """
    Upload a product packshot image.
    
    - Validates file type and size
    - Optionally removes background
    - Extracts dominant color palette
    
    Returns paths to original and cleaned images plus color palette.
    """
    # Validate content type
    if file.content_type and not is_valid_image_mime(file.content_type):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: image/jpeg, image/png, image/gif, image/webp"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE_MB}MB"
        )
    
    try:
        # Generate asset ID and safe filename
        asset_id = generate_asset_id()
        safe_name = create_safe_filename(file.filename or "packshot.png")
        
        # Save original file
        original_path = ASSETS_DIR / f"{asset_id}_{safe_name}"
        original_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(original_path, "wb") as f:
            f.write(content)
        
        logger.info("packshot_uploaded", asset_id=asset_id, original_path=str(original_path))
        
        # Remove background if requested
        cleaned_path = str(original_path)
        if remove_background:
            cleaned_path, success = bg_removal_service.remove_background(
                str(original_path),
                trim_borders=True
            )
            if not success:
                logger.warning("bg_removal_partial", asset_id=asset_id)
        
        # Extract dominant colors from cleaned image
        palette = extract_dominant_colors(cleaned_path, n_colors=3)
        
        return UploadResponse(
            original=f"/assets/{original_path.name}",
            cleaned=f"/assets/{Path(cleaned_path).name}",
            palette=palette,
            asset_id=asset_id
        )
        
    except Exception as e:
        logger.error("upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    remove_background: bool = Form(default=True)
):
    """
    Upload a brand logo image.
    
    Logos are processed similarly to packshots but may have different
    background removal needs.
    """
    # Use same logic as packshot upload
    return await upload_packshot(file, remove_background)


@router.post("/background")
async def upload_background(file: UploadFile = File(...)):
    """
    Upload a background image.
    
    Backgrounds are saved as-is without background removal.
    """
    # Validate content type
    if file.content_type and not is_valid_image_mime(file.content_type):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE_MB}MB"
        )
    
    try:
        # Generate asset ID and save
        asset_id = generate_asset_id()
        safe_name = create_safe_filename(file.filename or "background.png")
        
        file_path = ASSETS_DIR / f"{asset_id}_{safe_name}"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Extract colors
        palette = extract_dominant_colors(str(file_path), n_colors=5)
        
        logger.info("background_uploaded", asset_id=asset_id)
        
        return {
            "path": f"/assets/{file_path.name}",
            "palette": palette,
            "asset_id": asset_id
        }
        
    except Exception as e:
        logger.error("upload_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.delete("/{asset_id}")
async def delete_asset(asset_id: str):
    """
    Delete an uploaded asset and its processed versions.
    """
    deleted_files = []
    
    # Find and delete all files with this asset ID
    for file_path in ASSETS_DIR.glob(f"{asset_id}*"):
        try:
            os.remove(file_path)
            deleted_files.append(file_path.name)
        except OSError as e:
            logger.warning("delete_failed", path=str(file_path), error=str(e))
    
    if not deleted_files:
        raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")
    
    return {"deleted": deleted_files}
