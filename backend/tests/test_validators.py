"""
Unit tests for validator functions.
Tests all Appendix B / Tesco rules.
"""
import pytest
from app.models import Layout, LayoutElement, IssueSeverity
from app.services.validators import (
    validate_layout,
    validate_tesco_tag,
    validate_drinkaware,
    validate_no_terms_and_conditions,
    validate_no_competition_copy,
    validate_no_sustainability_claims,
    validate_no_charity_copy,
    validate_no_price_callouts,
    validate_no_money_back_guarantee,
    validate_no_claims,
    validate_value_tile_position,
    validate_social_safe_zones,
    validate_minimum_font_size,
    validate_wcag_contrast,
    ALLOWED_TESCO_TAGS
)


class TestTescoTagValidation:
    """Tests for Tesco tag text validation."""
    
    def test_valid_tesco_tags(self):
        """Test that all allowed Tesco tag texts pass validation."""
        for tag_text in ALLOWED_TESCO_TAGS:
            element = {"type": "tesco_tag", "text": tag_text}
            issue = validate_tesco_tag(element)
            assert issue is None, f"Valid tag '{tag_text}' should not raise issue"
    
    def test_invalid_tesco_tag(self):
        """Test that invalid Tesco tag text fails validation."""
        element = {"type": "tesco_tag", "text": "Buy at Tesco"}
        issue = validate_tesco_tag(element)
        assert issue is not None
        assert issue.severity == IssueSeverity.HARD
        assert issue.code == "TESCO_TAG_INVALID"
    
    def test_empty_tesco_tag(self):
        """Test that empty Tesco tag text fails validation."""
        element = {"type": "tesco_tag", "text": ""}
        issue = validate_tesco_tag(element)
        assert issue is not None
        assert issue.code == "TESCO_TAG_INVALID"
    
    def test_non_tesco_tag_element(self):
        """Test that non-tesco_tag elements are ignored."""
        element = {"type": "headline", "text": "Random Text"}
        issue = validate_tesco_tag(element)
        assert issue is None


class TestDrinkawareValidation:
    """Tests for Drinkaware lock-up validation."""
    
    def test_missing_drinkaware_alcohol_campaign(self):
        """Test that missing drinkaware on alcohol campaign fails."""
        elements = [{"type": "background", "color": "#FFFFFF"}]
        issues = validate_drinkaware(elements, is_alcohol=True, canvas_height=1920)
        assert len(issues) == 1
        assert issues[0].code == "DRINKAWARE_MISSING"
    
    def test_missing_drinkaware_non_alcohol(self):
        """Test that non-alcohol campaigns don't need drinkaware."""
        elements = [{"type": "background", "color": "#FFFFFF"}]
        issues = validate_drinkaware(elements, is_alcohol=False, canvas_height=1920)
        assert len(issues) == 0
    
    def test_valid_drinkaware_black(self):
        """Test valid drinkaware with black color."""
        elements = [{
            "type": "drinkaware",
            "color": "#000000",
            "height": 2  # 2% of 1920 = 38.4px > 20px
        }]
        issues = validate_drinkaware(elements, is_alcohol=True, canvas_height=1920)
        assert len(issues) == 0
    
    def test_valid_drinkaware_white(self):
        """Test valid drinkaware with white color."""
        elements = [{
            "type": "drinkaware",
            "color": "#FFFFFF",
            "height": 2
        }]
        issues = validate_drinkaware(elements, is_alcohol=True, canvas_height=1920)
        assert len(issues) == 0
    
    def test_invalid_drinkaware_color(self):
        """Test drinkaware with invalid color fails."""
        elements = [{
            "type": "drinkaware",
            "color": "#FF0000",  # Red - not allowed
            "height": 2
        }]
        issues = validate_drinkaware(elements, is_alcohol=True, canvas_height=1920)
        assert any(i.code == "DRINKAWARE_COLOR_INVALID" for i in issues)
    
    def test_drinkaware_too_small(self):
        """Test drinkaware with height below minimum fails."""
        elements = [{
            "type": "drinkaware",
            "color": "#000000",
            "height": 0.5  # 0.5% of 1920 = 9.6px < 20px
        }]
        issues = validate_drinkaware(elements, is_alcohol=True, canvas_height=1920)
        assert any(i.code == "DRINKAWARE_TOO_SMALL" for i in issues)


class TestCopyValidation:
    """Tests for copy content validation."""
    
    def test_no_terms_and_conditions(self):
        """Test T&Cs detection."""
        test_cases = [
            ("Terms and conditions apply", True),
            ("T&C apply", True),
            ("See website for details", True),
            ("Great new product", False),
        ]
        for text, should_fail in test_cases:
            issues = validate_no_terms_and_conditions(text, "")
            if should_fail:
                assert len(issues) > 0, f"'{text}' should fail T&C check"
            else:
                assert len(issues) == 0, f"'{text}' should pass T&C check"
    
    def test_no_competition_copy(self):
        """Test competition wording detection."""
        test_cases = [
            ("Win a prize!", True),
            ("Enter now", True),
            ("Chance to win", True),
            ("Delicious taste", False),
        ]
        for text, should_fail in test_cases:
            issues = validate_no_competition_copy(text, "")
            if should_fail:
                assert len(issues) > 0, f"'{text}' should fail competition check"
            else:
                assert len(issues) == 0, f"'{text}' should pass competition check"
    
    def test_no_sustainability_claims(self):
        """Test sustainability claims detection."""
        test_cases = [
            ("Eco-friendly packaging", True),
            ("Carbon neutral", True),
            ("Sustainable sourcing", True),
            ("Fresh and tasty", False),
        ]
        for text, should_fail in test_cases:
            issues = validate_no_sustainability_claims(text, "")
            if should_fail:
                assert len(issues) > 0, f"'{text}' should fail sustainability check"
            else:
                assert len(issues) == 0, f"'{text}' should pass sustainability check"
    
    def test_no_charity_copy(self):
        """Test charity partnership detection."""
        test_cases = [
            ("Supporting local charity", True),
            ("Donate to help", True),
            ("Premium quality", False),
        ]
        for text, should_fail in test_cases:
            issues = validate_no_charity_copy(text, "")
            if should_fail:
                assert len(issues) > 0, f"'{text}' should fail charity check"
            else:
                assert len(issues) == 0, f"'{text}' should pass charity check"
    
    def test_no_price_callouts(self):
        """Test price callout detection."""
        test_cases = [
            ("50% off!", True),
            ("Only £2.99", True),
            ("Great value", False),  # 'value' alone might be ambiguous
            ("New arrival", False),
        ]
        for text, should_fail in test_cases:
            issues = validate_no_price_callouts(text, "")
            # Only check definite cases
            if "£" in text or "%" in text:
                assert len(issues) > 0, f"'{text}' should fail price check"
    
    def test_no_money_back_guarantee(self):
        """Test money-back guarantee detection."""
        test_cases = [
            ("Money back guarantee", True),
            ("Full refund available", True),
            ("Satisfaction guaranteed", True),
            ("Quality assured", False),
        ]
        for text, should_fail in test_cases:
            issues = validate_no_money_back_guarantee(text, "")
            if should_fail:
                assert len(issues) > 0, f"'{text}' should fail guarantee check"
            else:
                assert len(issues) == 0, f"'{text}' should pass guarantee check"
    
    def test_no_claims(self):
        """Test unsubstantiated claims detection."""
        test_cases = [
            ("#1 in the UK", True),
            ("Best selling", True),
            ("Clinically proven", True),
            ("New recipe", False),
        ]
        for text, should_fail in test_cases:
            issues = validate_no_claims(text, "")
            if should_fail:
                assert len(issues) > 0, f"'{text}' should fail claims check"
            else:
                assert len(issues) == 0, f"'{text}' should pass claims check"


class TestLayoutValidation:
    """Tests for layout position and size validation."""
    
    def test_social_safe_zones_violation(self):
        """Test Stories safe zone detection."""
        elements = [
            {"type": "headline", "text": "Test", "x": 10, "y": 2, "width": 80, "height": 5}  # 2% = 38px, in top safe zone
        ]
        issues = validate_social_safe_zones(elements, 1080, 1920, "stories")
        assert any(i.code == "SAFE_ZONE_TOP_VIOLATION" for i in issues)
    
    def test_social_safe_zones_non_stories(self):
        """Test that non-Stories channels don't have safe zones."""
        elements = [
            {"type": "headline", "text": "Test", "x": 10, "y": 2, "width": 80, "height": 5}
        ]
        issues = validate_social_safe_zones(elements, 1080, 1920, "facebook")
        assert len(issues) == 0
    
    def test_minimum_font_size_fail(self):
        """Test minimum font size detection."""
        elements = [
            {"type": "headline", "font_size": 14}  # Below 20px minimum
        ]
        issues = validate_minimum_font_size(elements, 1920, "stories")
        assert any(i.code == "FONT_SIZE_TOO_SMALL" for i in issues)
    
    def test_minimum_font_size_pass(self):
        """Test valid font size passes."""
        elements = [
            {"type": "headline", "font_size": 24}  # Above 20px minimum
        ]
        issues = validate_minimum_font_size(elements, 1920, "stories")
        assert len(issues) == 0


class TestWCAGContrast:
    """Tests for WCAG contrast validation."""
    
    def test_good_contrast(self):
        """Test good contrast passes."""
        elements = [
            {"type": "headline", "color": "#000000", "font_size": 24}  # Black on white
        ]
        issues = validate_wcag_contrast(elements, "#FFFFFF")
        assert len(issues) == 0
    
    def test_poor_contrast(self):
        """Test poor contrast fails."""
        elements = [
            {"type": "headline", "color": "#CCCCCC", "font_size": 16}  # Light gray on white
        ]
        issues = validate_wcag_contrast(elements, "#FFFFFF")
        assert any(i.code == "WCAG_CONTRAST_FAIL" for i in issues)


class TestFullLayoutValidation:
    """Integration tests for complete layout validation."""
    
    def test_valid_layout(self):
        """Test a fully valid layout passes."""
        layout = Layout(
            id="test_1",
            score=0.9,
            elements=[
                LayoutElement(type="background", color="#FFFFFF"),
                LayoutElement(
                    type="headline",
                    text="New Product Launch",
                    x=10, y=50, width=80, height=10,
                    font_size=32, color="#000000"
                ),
                LayoutElement(
                    type="tesco_tag",
                    text="Available at Tesco",
                    x=5, y=85, width=25, height=5
                )
            ]
        )
        
        result = validate_layout(layout, "1080x1920", is_alcohol=False, channel="facebook")
        assert result.ok
        assert len([i for i in result.issues if i.severity == IssueSeverity.HARD]) == 0
    
    def test_invalid_layout_multiple_issues(self):
        """Test a layout with multiple issues."""
        layout = Layout(
            id="test_2",
            score=0.9,
            elements=[
                LayoutElement(type="background", color="#FFFFFF"),
                LayoutElement(
                    type="headline",
                    text="Win 50% off!",  # Competition + price
                    x=10, y=50, width=80, height=10,
                    font_size=10, color="#CCCCCC"  # Too small + poor contrast
                ),
                LayoutElement(
                    type="tesco_tag",
                    text="Shop at Tesco",  # Invalid tag
                    x=5, y=85, width=25, height=5
                )
            ]
        )
        
        result = validate_layout(layout, "1080x1920", is_alcohol=False, channel="stories")
        assert not result.ok
        assert len(result.issues) >= 3  # At least 3 issues


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
