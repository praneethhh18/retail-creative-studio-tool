"""
Retail Media Creative Tool - Main FastAPI Application

A Generative-AI powered web application for creating retailer-compliant,
brand-safe creatives for multiple channels.
"""
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import structlog

from app import __version__
from app.routes import upload, generate, validate, export
from app.utils import ASSETS_DIR, EXPORTS_DIR
from app.models import HealthResponse

# Load environment variables from project root or backend directory
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Try default location

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("application_starting", version=__version__)
    
    # Ensure directories exist
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("directories_ready", 
                assets=str(ASSETS_DIR), 
                exports=str(EXPORTS_DIR))
    
    yield
    
    # Shutdown
    logger.info("application_shutting_down")


# Create FastAPI application
app = FastAPI(
    title="Retail Media Creative Tool",
    description="""
    A Generative-AI powered web application for creating retailer-compliant,
    brand-safe creatives for multiple channels (Facebook, Instagram, Stories, in-store).
    
    ## Features
    
    - **Upload**: Upload packshots, logos, and backgrounds with automatic background removal
    - **Generate**: AI-driven layout suggestions with multiple options
    - **Validate**: Real-time validation against Appendix B / Tesco rules
    - **Export**: Multi-format export (JPEG/PNG) optimized under 500KB
    
    ## Channels Supported
    
    - Facebook (1200×628)
    - Instagram (1080×1080)
    - Stories (1080×1920)
    - In-store displays
    """,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if os.getenv("APP_ENV") == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", 
                 error=str(exc), 
                 path=request.url.path,
                 method=request.method)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."}
    )


# Include routers
app.include_router(upload.router)
app.include_router(generate.router)
app.include_router(validate.router)
app.include_router(export.router)


# Mount static files for assets and exports
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")
app.mount("/exports", StaticFiles(directory=str(EXPORTS_DIR)), name="exports")


@app.get("/", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns application status, version, and service availability.
    """
    from app.services.layout_llm import llm_client
    from app.services.bg_remove import REMBG_AVAILABLE
    
    return HealthResponse(
        status="healthy",
        version=__version__,
        services={
            "llm_available": llm_client.is_available(),
            "llm_provider": llm_client.provider,
            "bg_removal_available": REMBG_AVAILABLE,
            "assets_dir": str(ASSETS_DIR),
            "exports_dir": str(EXPORTS_DIR)
        }
    )


@app.get("/api/info")
async def api_info():
    """Get API information and available endpoints."""
    return {
        "name": "Retail Media Creative Tool API",
        "version": __version__,
        "endpoints": {
            "health": "GET /",
            "upload": {
                "packshot": "POST /upload/packshot",
                "logo": "POST /upload/logo",
                "background": "POST /upload/background"
            },
            "generate": {
                "layouts": "POST /generate/layouts",
                "moderate_copy": "POST /generate/moderate-copy",
                "status": "GET /generate/status"
            },
            "validate": {
                "check": "POST /validate/check",
                "quick_check": "POST /validate/quick-check",
                "rules": "GET /validate/rules"
            },
            "export": {
                "image": "POST /export/image",
                "batch": "POST /export/batch",
                "zip": "POST /export/zip",
                "download": "GET /export/download/{filename}"
            },
            "assets": "GET /assets/{asset_id}",
            "docs": "GET /docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=os.getenv("APP_ENV") != "production"
    )
