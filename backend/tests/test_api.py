"""
Integration tests for API endpoints.
Tests the complete upload -> generate -> validate -> export flow.
"""
import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image
import io

from app.main import app
from app.utils import ASSETS_DIR, EXPORTS_DIR


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_image():
    """Create a sample test image."""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


@pytest.fixture
def sample_layout():
    """Create a sample layout for testing."""
    return {
        "id": "test_layout_1",
        "score": 0.9,
        "elements": [
            {"type": "background", "color": "#FFFFFF"},
            {
                "type": "packshot",
                "asset": "test_pack",
                "x": 20, "y": 20, "width": 40, "height": 40, "z": 2
            },
            {
                "type": "headline",
                "text": "New Product",
                "x": 10, "y": 65, "width": 80, "height": 10,
                "font_size": 32, "color": "#000000"
            },
            {
                "type": "tesco_tag",
                "text": "Available at Tesco",
                "x": 5, "y": 85, "width": 25, "height": 5
            }
        ]
    }


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "services" in data


class TestUploadEndpoints:
    """Tests for upload endpoints."""
    
    def test_upload_packshot(self, client, sample_image):
        """Test packshot upload."""
        response = client.post(
            "/upload/packshot",
            files={"file": ("test.png", sample_image, "image/png")},
            data={"remove_background": "true"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "original" in data
        assert "cleaned" in data
        assert "palette" in data
        assert "asset_id" in data
    
    def test_upload_invalid_file_type(self, client):
        """Test upload rejects invalid file types."""
        response = client.post(
            "/upload/packshot",
            files={"file": ("test.txt", b"hello", "text/plain")}
        )
        assert response.status_code == 400
    
    def test_upload_logo(self, client, sample_image):
        """Test logo upload."""
        response = client.post(
            "/upload/logo",
            files={"file": ("logo.png", sample_image, "image/png")}
        )
        assert response.status_code == 200
    
    def test_upload_background(self, client, sample_image):
        """Test background upload."""
        response = client.post(
            "/upload/background",
            files={"file": ("bg.png", sample_image, "image/png")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert "palette" in data


class TestGenerateEndpoints:
    """Tests for generation endpoints."""
    
    def test_generate_layouts(self, client):
        """Test layout generation."""
        request = {
            "brand": "Test Brand",
            "headline": "New Product Launch",
            "subhead": "Try it today",
            "colors": ["#FF0000", "#FFFFFF"],
            "packshot_count": 1,
            "required_tiles": {"tesco_tag": True, "value_tile": False},
            "canvas": "1080x1920",
            "is_alcohol": False
        }
        
        response = client.post("/generate/layouts", json=request)
        assert response.status_code == 200
        data = response.json()
        assert "layouts" in data
        assert len(data["layouts"]) >= 1
        
        # Check layout structure
        layout = data["layouts"][0]
        assert "id" in layout
        assert "score" in layout
        assert "elements" in layout
    
    def test_generate_layouts_alcohol(self, client):
        """Test layout generation for alcohol campaign includes drinkaware."""
        request = {
            "brand": "Test Beer",
            "headline": "Refreshing Taste",
            "colors": ["#GOLD", "#WHITE"],
            "packshot_count": 1,
            "required_tiles": {"tesco_tag": True},
            "is_alcohol": True
        }
        
        response = client.post("/generate/layouts", json=request)
        assert response.status_code == 200
        data = response.json()
        
        # Check for drinkaware element
        layout = data["layouts"][0]
        element_types = [e["type"] for e in layout["elements"]]
        assert "drinkaware" in element_types
    
    def test_moderate_copy(self, client):
        """Test copy moderation."""
        request = {
            "headline": "New Product",
            "subhead": "Great taste"
        }
        
        response = client.post("/generate/moderate-copy", json=request)
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert "issues" in data
    
    def test_moderate_copy_with_issues(self, client):
        """Test copy moderation detects issues."""
        request = {
            "headline": "Win 50% off!",
            "subhead": "Enter now"
        }
        
        response = client.post("/generate/moderate-copy", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert len(data["issues"]) > 0
    
    def test_llm_status(self, client):
        """Test LLM status endpoint."""
        response = client.get("/generate/status")
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        assert "provider" in data


class TestValidateEndpoints:
    """Tests for validation endpoints."""
    
    def test_validate_layout(self, client, sample_layout):
        """Test layout validation."""
        request = {
            "layout": sample_layout,
            "canvas_size": "1080x1920",
            "is_alcohol": False,
            "channel": "stories"
        }
        
        response = client.post("/validate/check", json=request)
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert "issues" in data
        assert "checked_rules" in data
    
    def test_validate_invalid_layout(self, client):
        """Test validation detects issues."""
        layout = {
            "id": "invalid_1",
            "score": 0.9,
            "elements": [
                {"type": "background", "color": "#FFFFFF"},
                {
                    "type": "headline",
                    "text": "Win Big Prizes!",  # Competition copy
                    "x": 10, "y": 5, "width": 80, "height": 10,  # In safe zone
                    "font_size": 10, "color": "#CCCCCC"  # Too small, poor contrast
                },
                {
                    "type": "tesco_tag",
                    "text": "Buy at Tesco",  # Invalid tag text
                    "x": 5, "y": 85, "width": 25, "height": 5
                }
            ]
        }
        
        request = {
            "layout": layout,
            "canvas_size": "1080x1920",
            "channel": "stories"
        }
        
        response = client.post("/validate/check", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert len(data["issues"]) > 0
    
    def test_quick_check(self, client):
        """Test quick validation endpoint."""
        response = client.post(
            "/validate/quick-check",
            params={
                "headline": "New Product",
                "subhead": "Try it today",
                "tesco_tag_text": "Available at Tesco"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
    
    def test_get_rules(self, client):
        """Test rules listing endpoint."""
        response = client.get("/validate/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert len(data["rules"]) > 0


class TestExportEndpoints:
    """Tests for export endpoints."""
    
    def test_export_image(self, client, sample_layout):
        """Test image export."""
        request = {
            "layout": sample_layout,
            "assets_map": {},
            "sizes": ["1080x1080"],
            "format": "jpeg"
        }
        
        response = client.post("/export/image", json=request)
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert len(data["files"]) > 0
    
    def test_export_multiple_sizes(self, client, sample_layout):
        """Test multi-size export."""
        request = {
            "layout": sample_layout,
            "assets_map": {},
            "sizes": ["1080x1080", "1080x1920", "1200x628"],
            "format": "jpeg"
        }
        
        response = client.post("/export/image", json=request)
        assert response.status_code == 200
        data = response.json()
        assert len(data["files"]) == 3
    
    def test_reformat_layout(self, client, sample_layout):
        """Test layout reformatting."""
        response = client.post(
            "/export/reformat",
            params={
                "source_size": "1080x1920",
                "target_size": "1080x1080"
            },
            json=sample_layout
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "elements" in data


class TestIntegrationFlow:
    """Integration tests for complete workflow."""
    
    def test_complete_flow(self, client, sample_image):
        """Test complete upload -> generate -> validate -> export flow."""
        # 1. Upload packshot
        upload_response = client.post(
            "/upload/packshot",
            files={"file": ("pack.png", sample_image, "image/png")},
            data={"remove_background": "false"}
        )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        asset_id = upload_data["asset_id"]
        
        # 2. Generate layouts
        gen_request = {
            "brand": "Test Brand",
            "headline": "New Product",
            "colors": upload_data["palette"],
            "packshot_count": 1,
            "required_tiles": {"tesco_tag": True}
        }
        gen_response = client.post("/generate/layouts", json=gen_request)
        assert gen_response.status_code == 200
        layouts = gen_response.json()["layouts"]
        
        # 3. Validate first layout
        validate_request = {
            "layout": layouts[0],
            "canvas_size": "1080x1920",
            "channel": "stories"
        }
        validate_response = client.post("/validate/check", json=validate_request)
        assert validate_response.status_code == 200
        
        # 4. Export
        export_request = {
            "layout": layouts[0],
            "assets_map": {},
            "sizes": ["1080x1920"],
            "format": "jpeg"
        }
        export_response = client.post("/export/image", json=export_request)
        assert export_response.status_code == 200
        export_data = export_response.json()
        assert len(export_data["files"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
