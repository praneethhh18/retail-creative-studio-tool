"""
Tests for utility functions.
"""
import pytest
from app.utils import (
    parse_canvas_size,
    percentage_to_pixels,
    pixels_to_percentage,
    scale_font_size,
    calculate_relative_luminance,
    calculate_contrast_ratio,
    check_wcag_aa_contrast,
    get_suggested_text_color,
    sanitize_text_for_llm
)


class TestCanvasParsing:
    """Tests for canvas size parsing."""
    
    def test_parse_valid_canvas(self):
        """Test parsing valid canvas sizes."""
        assert parse_canvas_size("1080x1920") == (1080, 1920)
        assert parse_canvas_size("1200x628") == (1200, 628)
        assert parse_canvas_size("1080x1080") == (1080, 1080)
    
    def test_parse_invalid_canvas(self):
        """Test parsing invalid canvas sizes raises error."""
        with pytest.raises(ValueError):
            parse_canvas_size("invalid")
        with pytest.raises(ValueError):
            parse_canvas_size("1080-1920")


class TestCoordinateConversion:
    """Tests for coordinate conversion."""
    
    def test_percentage_to_pixels(self):
        """Test percentage to pixel conversion."""
        x, y, w, h = percentage_to_pixels(50, 25, 20, 10, 1080, 1920)
        assert x == 540  # 50% of 1080
        assert y == 480  # 25% of 1920
        assert w == 216  # 20% of 1080
        assert h == 192  # 10% of 1920
    
    def test_pixels_to_percentage(self):
        """Test pixel to percentage conversion."""
        x, y, w, h = pixels_to_percentage(540, 480, 216, 192, 1080, 1920)
        assert x == 50.0
        assert y == 25.0
        assert w == 20.0
        assert h == 10.0


class TestFontScaling:
    """Tests for font size scaling."""
    
    def test_scale_font_size(self):
        """Test font size scaling."""
        # 32px at 1920 height scaled to 1080 height
        scaled = scale_font_size(32, 1920, 1080)
        assert scaled == 18  # 32 * (1080/1920) = 18
    
    def test_scale_font_size_minimum(self):
        """Test font size doesn't go below 8px."""
        scaled = scale_font_size(10, 1920, 100)
        assert scaled >= 8


class TestContrastCalculation:
    """Tests for WCAG contrast calculations."""
    
    def test_relative_luminance_black(self):
        """Test luminance of black."""
        lum = calculate_relative_luminance("#000000")
        assert lum == 0.0
    
    def test_relative_luminance_white(self):
        """Test luminance of white."""
        lum = calculate_relative_luminance("#FFFFFF")
        assert abs(lum - 1.0) < 0.01
    
    def test_contrast_ratio_black_white(self):
        """Test contrast ratio between black and white."""
        ratio = calculate_contrast_ratio("#000000", "#FFFFFF")
        assert ratio == 21.0
    
    def test_contrast_ratio_same_color(self):
        """Test contrast ratio of same color."""
        ratio = calculate_contrast_ratio("#FF0000", "#FF0000")
        assert ratio == 1.0
    
    def test_wcag_aa_pass(self):
        """Test WCAG AA pass for high contrast."""
        assert check_wcag_aa_contrast("#000000", "#FFFFFF")
    
    def test_wcag_aa_fail(self):
        """Test WCAG AA fail for low contrast."""
        assert not check_wcag_aa_contrast("#CCCCCC", "#FFFFFF")
    
    def test_suggested_text_color_light_bg(self):
        """Test suggested color for light background."""
        color = get_suggested_text_color("#FFFFFF")
        assert color == "#000000"
    
    def test_suggested_text_color_dark_bg(self):
        """Test suggested color for dark background."""
        color = get_suggested_text_color("#000000")
        assert color == "#FFFFFF"


class TestTextSanitization:
    """Tests for text sanitization."""
    
    def test_sanitize_normal_text(self):
        """Test normal text passes through."""
        text = "New Product Launch"
        assert sanitize_text_for_llm(text) == text
    
    def test_sanitize_removes_templates(self):
        """Test template patterns are removed."""
        text = "Hello {name} world"
        assert "{" not in sanitize_text_for_llm(text)
    
    def test_sanitize_removes_html(self):
        """Test HTML tags are removed."""
        text = "Hello <script>alert('x')</script> world"
        assert "<" not in sanitize_text_for_llm(text)
    
    def test_sanitize_limits_length(self):
        """Test long text is truncated."""
        text = "a" * 1000
        assert len(sanitize_text_for_llm(text)) <= 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
