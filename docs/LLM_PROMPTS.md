# LLM Prompts Documentation

This document details the prompts used for AI-powered layout generation in the Retail Media Creative Tool.

## Overview

The tool uses OpenAI's GPT-4 to generate layout suggestions based on:
- Uploaded assets (packshots, logos, backgrounds)
- Extracted color palettes
- Channel specifications
- User instructions

## Prompt Templates

### 1. Layout Suggestion Prompt

**Purpose:** Generate initial layout suggestions based on assets and requirements.

```
You are a professional graphic designer specializing in retail media creatives.

Given the following assets and requirements, generate 3 layout suggestions:

Assets:
- Packshots: {packshot_count} product images
- Logos: {logo_count} brand logos
- Background: {has_background}
- Color Palette: {palette}

Channel: {channel_name}
Dimensions: {width}x{height}

Requirements:
- All elements must respect safe zones ({safe_zone_percent}% margin)
- Text must be minimum 12px for body, 18px for headlines
- Maintain 4.5:1 contrast ratio for accessibility
- Include required elements: background, packshot, logo, headline

User Instructions: {user_prompt}

Return exactly 3 layout options as a JSON array. Each layout should have:
- A unique composition approach
- All elements positioned with percentage-based coordinates
- Reasoning for the design choices

Format:
{
  "layouts": [
    {
      "elements": [
        {
          "id": "unique-id",
          "type": "image|text|shape",
          "x": 0-100,
          "y": 0-100,
          "width": 0-100,
          "height": 0-100,
          "content": "text content or asset reference",
          "style": { "fontSize": 24, "fontFamily": "Arial", "color": "#000000" }
        }
      ],
      "background_color": "#ffffff",
      "reasoning": "Explanation of design choices"
    }
  ]
}
```

### 2. Refinement Prompt

**Purpose:** Refine an existing layout based on user feedback.

```
You are refining an existing retail creative layout.

Current Layout:
{current_layout_json}

User Feedback: {feedback}

Channel: {channel_name}
Color Palette: {palette}

Modify the layout according to the feedback while:
- Maintaining all required elements
- Respecting safe zones
- Ensuring accessibility standards
- Keeping the overall brand consistency

Return the modified layout in the same JSON format.
```

### 3. Headline Generation Prompt

**Purpose:** Generate headline text options.

```
Generate 5 headline options for a retail creative:

Product: {product_name}
Brand: {brand_name}
Promotion: {promotion_type}
Character Limit: {max_chars}

Guidelines:
- Clear and concise messaging
- Action-oriented language
- Avoid superlatives without substantiation
- Suitable for {channel_name}

Return as JSON:
{
  "headlines": [
    "Headline option 1",
    "Headline option 2",
    ...
  ]
}
```

## Response Parsing

The LLM responses are parsed and validated:

1. **JSON Extraction:** Extract JSON from potential markdown code blocks
2. **Schema Validation:** Validate against Pydantic models
3. **Coordinate Normalization:** Ensure all coordinates are 0-100 percentages
4. **Fallback:** Use stub layouts if LLM fails or returns invalid data

## Fallback Stub Layouts

When the LLM is unavailable or returns invalid data, the system uses pre-defined stub layouts:

### Facebook Feed Layout
```json
{
  "elements": [
    { "type": "image", "x": 0, "y": 0, "width": 100, "height": 100, "content": "background" },
    { "type": "image", "x": 55, "y": 15, "width": 40, "height": 70, "content": "packshot" },
    { "type": "image", "x": 5, "y": 5, "width": 15, "height": 10, "content": "logo" },
    { "type": "text", "x": 5, "y": 40, "width": 45, "height": 20, "content": "Your Headline Here" }
  ]
}
```

### Instagram Story Layout
```json
{
  "elements": [
    { "type": "image", "x": 0, "y": 0, "width": 100, "height": 100, "content": "background" },
    { "type": "image", "x": 10, "y": 30, "width": 80, "height": 40, "content": "packshot" },
    { "type": "image", "x": 35, "y": 5, "width": 30, "height": 10, "content": "logo" },
    { "type": "text", "x": 10, "y": 80, "width": 80, "height": 15, "content": "Your Headline Here" }
  ]
}
```

## Best Practices

### Prompt Engineering

1. **Be Specific:** Include exact dimensions and requirements
2. **Provide Context:** Include color palette and asset information
3. **Set Constraints:** Specify safe zones and accessibility requirements
4. **Request Format:** Always specify the expected JSON output format

### Temperature Settings

- **Layout Generation:** 0.7 (creative variety)
- **Refinement:** 0.3 (consistent modifications)
- **Headlines:** 0.8 (creative text options)

### Token Management

- **Max Input Tokens:** ~2000 (prompt + context)
- **Max Output Tokens:** 2000 (layout JSON)
- **Model:** GPT-4 or GPT-3.5-turbo

## Error Handling

| Error | Fallback |
|-------|----------|
| API timeout | Use stub layout |
| Invalid JSON | Attempt repair, then use stub |
| Missing elements | Add required elements automatically |
| Coordinate overflow | Clamp to 0-100 range |

## Usage Example

```python
from app.services.layout_llm import LLMClient

client = LLMClient()

layouts = await client.generate_layouts(
    packshot_ids=["pack1", "pack2"],
    logo_ids=["logo1"],
    background_id="bg1",
    palette=["#FF5733", "#FFFFFF", "#333333"],
    channel="facebook_feed",
    user_prompt="Create a bold, modern layout for a summer sale"
)

for layout in layouts:
    print(f"Layout: {layout.elements}")
    print(f"Reasoning: {layout.reasoning}")
```
