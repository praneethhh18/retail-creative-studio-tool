# Validator Rules Reference

This document provides a comprehensive reference for all validation rules implemented in the Retail Media Creative Tool, based on Appendix B / Tesco guidelines.

## Rule Summary

| Code | Rule | Severity | Auto-Fix |
|------|------|----------|----------|
| TESCO_TAG | Tesco tag required | Error | No |
| DRINKAWARE | Drinkaware disclaimer | Error | Yes |
| TERMS_CONDITIONS | T&C requirements | Error | Yes |
| COMPETITION_DISCLOSURE | Competition rules | Error | No |
| SUSTAINABILITY_CLAIM | Sustainability proof | Warning | No |
| CHARITY_PROMOTION | Charity disclosure | Error | No |
| PRICE_DISPLAY | Price visibility | Error | Yes |
| CLAIMS_VERIFICATION | Claims substantiation | Warning | No |
| SAFE_ZONE | Content margins | Error | Yes |
| FONT_SIZE | Minimum font size | Error | Yes |
| WCAG_CONTRAST | Color contrast | Error | Yes |
| REQUIRED_ELEMENTS | Missing elements | Error | No |
| MAX_ELEMENTS | Element count | Warning | No |
| BACKGROUND_REQUIRED | Background present | Error | No |
| LOGO_REQUIRED | Logo present | Error | No |

---

## Detailed Rule Descriptions

### 1. TESCO_TAG

**Severity:** Error  
**Category:** Retailer Compliance

**Description:**  
Creatives specifically for Tesco channels must include the official Tesco tag/branding element.

**Validation Logic:**
```python
def check_tesco_tag(layout, channel):
    if "tesco" in channel.lower():
        return any(
            "tesco" in str(elem.content).lower() or 
            elem.type == "retailer_tag"
            for elem in layout.elements
        )
    return True  # Non-Tesco channels pass
```

**Resolution:**  
Add Tesco logo or tag element to the layout.

---

### 2. DRINKAWARE

**Severity:** Error  
**Category:** Legal Compliance

**Description:**  
Alcohol products require the "drinkaware.co.uk" disclaimer to comply with UK advertising regulations.

**Validation Logic:**
```python
def check_drinkaware(layout):
    has_alcohol = any(
        "alcohol" in str(elem.content).lower() or
        "beer" in str(elem.content).lower() or
        "wine" in str(elem.content).lower() or
        "spirit" in str(elem.content).lower()
        for elem in layout.elements
    )
    
    if has_alcohol:
        return any(
            "drinkaware" in str(elem.content).lower()
            for elem in layout.elements
        )
    return True
```

**Auto-Fix:**  
Adds text element: "drinkaware.co.uk" at bottom-left corner.

---

### 3. TERMS_CONDITIONS

**Severity:** Error  
**Category:** Legal Compliance

**Description:**  
Promotional offers with conditions (e.g., "Buy 2, Get 1 Free", "Limited Time") must include Terms & Conditions reference.

**Trigger Keywords:**
- "offer", "deal", "save"
- "buy x get", "half price"
- "limited time", "while stocks last"
- "discount", "% off"

**Validation Logic:**
```python
def check_terms(layout):
    has_offer = any(
        any(keyword in str(elem.content).lower() 
            for keyword in OFFER_KEYWORDS)
        for elem in layout.elements
    )
    
    if has_offer:
        return any(
            "t&c" in str(elem.content).lower() or
            "terms" in str(elem.content).lower()
            for elem in layout.elements
        )
    return True
```

**Auto-Fix:**  
Adds text element: "T&Cs apply. See in store for details."

---

### 4. COMPETITION_DISCLOSURE

**Severity:** Error  
**Category:** Legal Compliance

**Description:**  
Competition promotions must include TSBS (Trading Standards Business Support) promoter information.

**Trigger Keywords:**
- "win", "prize", "competition"
- "enter to", "sweepstake"
- "giveaway", "draw"

**Required Disclosure Format:**
```
Promoter: [Brand Name]
[Address]
UK residents 18+ only
Entry closes: [Date]
```

---

### 5. SUSTAINABILITY_CLAIM

**Severity:** Warning  
**Category:** Claim Substantiation

**Description:**  
Environmental/sustainability claims must cite recognized certification bodies.

**Trigger Keywords:**
- "eco-friendly", "sustainable"
- "recyclable", "recycled"
- "carbon neutral", "net zero"
- "organic", "natural"

**Recognized Certifications:**
- FSC (Forest Stewardship Council)
- Rainforest Alliance
- Soil Association
- Carbon Trust
- RSPCA Assured

---

### 6. CHARITY_PROMOTION

**Severity:** Error  
**Category:** Legal Compliance

**Description:**  
Charity-linked promotions must disclose the donation amount or percentage.

**Trigger Keywords:**
- "charity", "donate", "donation"
- "proceeds go to", "supporting"
- "partnership with [charity name]"

**Required Disclosure:**
```
[X]p/£[X] per pack sold goes to [Charity Name]
Charity Reg No: [Number]
```

---

### 7. PRICE_DISPLAY

**Severity:** Error  
**Category:** Consumer Protection

**Description:**  
Price displays must meet minimum visibility standards for consumer protection.

**Requirements:**
- Minimum font size: 14px
- Clear contrast with background
- Complete price (including any "from" qualifiers)
- Currency symbol visible

**Validation Logic:**
```python
def check_price_display(layout):
    price_elements = [
        elem for elem in layout.elements
        if re.match(r'[£$€]\d+', str(elem.content))
    ]
    
    for price in price_elements:
        if price.style.get('fontSize', 0) < 14:
            return False
    return True
```

---

### 8. CLAIMS_VERIFICATION

**Severity:** Warning  
**Category:** Advertising Standards

**Description:**  
Product claims (health, performance, comparative) should be substantiated.

**Claim Types:**
- Health claims: "boosts immunity", "low fat"
- Performance claims: "works faster", "lasts longer"
- Comparative claims: "#1 brand", "best selling"

**Resolution:**  
Add footnote with claim source or remove unsubstantiated claims.

---

### 9. SAFE_ZONE

**Severity:** Error  
**Category:** Technical Requirements

**Description:**  
Important content must be within channel-specific safe zones to prevent cropping.

**Safe Zone Margins:**

| Channel | Safe Zone |
|---------|-----------|
| Facebook Feed | 5% all sides |
| Instagram Feed | 5% all sides |
| Instagram Story | 10% top/bottom, 5% sides |
| In-Store A4 | 3mm bleed + 5mm safe |

**Validation Logic:**
```python
def check_safe_zones(layout, channel):
    margin = SAFE_ZONES.get(channel, 5)
    
    for elem in layout.elements:
        if elem.type in ['text', 'logo', 'cta']:
            # Check if element is within safe zone
            if (elem.x < margin or 
                elem.y < margin or
                elem.x + elem.width > 100 - margin or
                elem.y + elem.height > 100 - margin):
                return False
    return True
```

**Auto-Fix:**  
Repositions elements to be within safe zone boundaries.

---

### 10. FONT_SIZE

**Severity:** Error  
**Category:** Accessibility

**Description:**  
Text must be readable at the intended viewing distance.

**Minimum Sizes:**
- Headlines: 18px
- Body text: 12px
- Legal/disclaimer: 8px
- Price: 14px

**Validation Logic:**
```python
def check_font_size(layout):
    for elem in layout.elements:
        if elem.type == 'text':
            font_size = elem.style.get('fontSize', 12)
            text_type = classify_text_type(elem.content)
            min_size = MIN_FONT_SIZES.get(text_type, 12)
            
            if font_size < min_size:
                return False
    return True
```

---

### 11. WCAG_CONTRAST

**Severity:** Error  
**Category:** Accessibility (WCAG 2.1 AA)

**Description:**  
Text must have sufficient contrast with its background for readability.

**Requirements:**
- Normal text: 4.5:1 ratio minimum
- Large text (18px+ or 14px bold): 3:1 ratio minimum
- Non-text elements: 3:1 ratio minimum

**Validation Logic:**
```python
def check_wcag_contrast(text_color, bg_color):
    # Calculate relative luminance
    def luminance(color):
        r, g, b = hex_to_rgb(color)
        r, g, b = [x/255 for x in (r, g, b)]
        r, g, b = [x/12.92 if x <= 0.03928 
                   else ((x+0.055)/1.055)**2.4 
                   for x in (r, g, b)]
        return 0.2126*r + 0.7152*g + 0.0722*b
    
    l1 = luminance(text_color)
    l2 = luminance(bg_color)
    
    ratio = (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)
    return ratio >= 4.5
```

**Auto-Fix:**  
Adjusts text color to meet contrast requirements while staying close to brand colors.

---

### 12. REQUIRED_ELEMENTS

**Severity:** Error  
**Category:** Creative Requirements

**Description:**  
Layouts must contain all mandatory elements.

**Required Elements:**
- Background (image or color)
- At least one packshot
- Brand logo
- Primary headline or CTA

---

### 13. MAX_ELEMENTS

**Severity:** Warning  
**Category:** Design Best Practices

**Description:**  
Excessive elements reduce visual clarity and message impact.

**Limits:**
| Channel | Max Elements |
|---------|-------------|
| Facebook Feed | 8 |
| Instagram Feed | 6 |
| Instagram Story | 5 |
| In-Store A4 | 12 |

---

### 14. BACKGROUND_REQUIRED

**Severity:** Error  
**Category:** Creative Requirements

**Description:**  
Every creative must have a background element (image or solid color).

---

### 15. LOGO_REQUIRED

**Severity:** Error  
**Category:** Brand Requirements

**Description:**  
Every creative must include the brand logo for brand recognition.

**Logo Requirements:**
- Minimum size: 5% of canvas width
- Must be within safe zones
- Must have clear space around it

---

## Validation Response Format

```json
{
  "valid": false,
  "issues": [
    {
      "code": "SAFE_ZONE",
      "severity": "error",
      "message": "Element 'headline' is outside safe zone",
      "element_id": "elem-123",
      "suggestion": "Move element at least 5% from edge",
      "auto_fixable": true
    }
  ],
  "score": 72,
  "passed_rules": 12,
  "total_rules": 15
}
```

## Implementation Notes

### Rule Priority

1. **Legal Compliance** (Errors that prevent export)
2. **Accessibility** (WCAG compliance)
3. **Technical Requirements** (Safe zones, format)
4. **Design Best Practices** (Warnings)

### Custom Rule Configuration

Rules can be configured per channel:

```python
CHANNEL_RULES = {
    "facebook_feed": {
        "safe_zone": 5,
        "max_elements": 8,
        "require_cta": True
    },
    "instore_a4": {
        "safe_zone": 8,
        "max_elements": 12,
        "require_barcode": True
    }
}
```

### Adding New Rules

1. Create validation function in `validators.py`
2. Add rule code to `ValidationRuleCode` enum
3. Register in `VALIDATORS` list
4. Add auto-fix function if applicable
5. Update documentation
