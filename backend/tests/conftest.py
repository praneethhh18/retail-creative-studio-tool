"""
Pytest configuration and fixtures for backend tests
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI application"""
    return TestClient(app)


@pytest.fixture
def sample_layout():
    """Create a sample layout for testing"""
    return {
        "elements": [
            {
                "id": "bg-1",
                "type": "image",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 100,
                "content": "background.jpg",
            },
            {
                "id": "pack-1",
                "type": "image",
                "x": 55,
                "y": 15,
                "width": 40,
                "height": 70,
                "content": "packshot.png",
            },
            {
                "id": "logo-1",
                "type": "image",
                "x": 5,
                "y": 5,
                "width": 15,
                "height": 10,
                "content": "logo.png",
            },
            {
                "id": "headline-1",
                "type": "text",
                "x": 5,
                "y": 40,
                "width": 45,
                "height": 20,
                "content": "Summer Sale!",
                "style": {
                    "fontSize": 24,
                    "fontFamily": "Arial",
                    "color": "#ffffff",
                    "fontWeight": "bold",
                },
            },
        ],
        "background_color": "#0066cc",
    }


@pytest.fixture
def sample_layout_with_issues():
    """Create a layout with validation issues"""
    return {
        "elements": [
            {
                "id": "headline-1",
                "type": "text",
                "x": 1,  # Outside safe zone
                "y": 1,
                "width": 98,
                "height": 10,
                "content": "Buy Now!",
                "style": {
                    "fontSize": 8,  # Too small
                    "fontFamily": "Arial",
                    "color": "#cccccc",  # Low contrast
                },
            },
        ],
        "background_color": "#dddddd",
    }


@pytest.fixture
def sample_packshot_data():
    """Sample data for packshot upload response"""
    return {
        "original": "/uploads/packshot_original.png",
        "cleaned": "/uploads/packshot_cleaned.png",
        "palette": ["#ff5733", "#ffffff", "#333333"],
        "asset_id": "pack-123",
    }


@pytest.fixture
def sample_validation_result():
    """Sample validation result"""
    return {
        "valid": False,
        "issues": [
            {
                "code": "FONT_SIZE",
                "severity": "error",
                "message": "Font size 8px is below minimum 12px",
                "element_id": "headline-1",
                "suggestion": "Increase font size to at least 12px",
                "auto_fixable": True,
            },
        ],
    }
