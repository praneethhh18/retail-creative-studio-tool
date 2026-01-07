# Demo Script

This document provides a step-by-step walkthrough for demonstrating the Retail Media Creative Tool.

## Prerequisites

- Application running (Docker or local development)
- Sample assets available (see `sample_assets/` folder)
- Browser: Chrome, Firefox, or Edge (latest version)

## Demo Flow

### 1. Introduction (2 minutes)

**Opening Statement:**
> "Today I'll demonstrate the Retail Media Creative Tool - an AI-powered application that helps advertisers create retailer-compliant creatives for multiple channels in minutes, not hours."

**Key Value Propositions:**
- 🚀 Reduce creative production time by 80%
- ✅ Automatic compliance validation
- 🤖 AI-powered layout suggestions
- 📤 One-click multi-format export

---

### 2. Asset Upload (3 minutes)

**Navigate to the application:**
```
http://localhost (Docker) or http://localhost:5173 (dev)
```

**Demo Steps:**

1. **Upload Packshot**
   - Click "Drop Packshot here or browse" in the Asset Library
   - Select `sample_assets/packshot_cereal.png`
   - Point out: "Notice the background is automatically removed using AI"
   - Point out: "Color palette is extracted for design suggestions"

2. **Upload Logo**
   - Click "Drop Logo here or browse"
   - Select `sample_assets/logo_brand.png`
   - Point out: "Logo is processed and ready for placement"

3. **Upload Background**
   - Click "Drop Background here or browse"
   - Select `sample_assets/background_summer.jpg`

**Talking Points:**
- "The tool automatically processes assets - removing backgrounds, extracting colors"
- "This normally takes 15-20 minutes in Photoshop, done in seconds here"

---

### 3. Generate Layouts (3 minutes)

**Demo Steps:**

1. **Select Channel**
   - Use the dropdown in the toolbar
   - Select "Instagram Feed (1080×1080)"
   - Point out: "Canvas updates to show the correct aspect ratio"

2. **Generate Suggestions**
   - Click the "Generate" button (purple)
   - Wait for AI to process (~3-5 seconds)
   - Point out: "The AI generates 3 layout options based on our assets"

3. **Browse Suggestions**
   - Scroll through the suggestion carousel at the bottom
   - Click different suggestions to preview
   - Point out: "Each layout is professionally composed with our brand colors"

4. **Select Layout**
   - Click on preferred layout
   - Point out: "Selected layout loads into the canvas editor"

**Talking Points:**
- "The AI understands design principles - balance, hierarchy, safe zones"
- "It uses our extracted color palette for cohesive designs"
- "This replaces hours of designer iteration"

---

### 4. Canvas Editing (4 minutes)

**Demo Steps:**

1. **Drag Elements**
   - Click and drag the packshot to reposition
   - Point out: "Elements snap to safe zone guides"
   - Show: Safe zone indicator lines

2. **Resize Elements**
   - Select the headline text
   - Drag corner handles to resize
   - Point out: "Proportions are maintained"

3. **Edit Text**
   - Double-click on headline
   - Type: "Summer Sale - 20% Off"
   - Point out: "Text updates in real-time"

4. **Keyboard Shortcuts**
   - Press Ctrl+Z to undo
   - Press Ctrl+Y to redo
   - Point out: "Full undo/redo history"

5. **Show Safe Zones**
   - Toggle safe zones visibility (if available)
   - Point out: "Gray area shows where content might be cropped"

**Talking Points:**
- "Designers can still fine-tune every element"
- "But they're starting from a professionally composed layout"
- "Safe zones prevent content from being cut off on different platforms"

---

### 5. Validation (3 minutes)

**Demo Steps:**

1. **Run Validation**
   - Click the "Validate" button
   - Point out: "15 rules are checked automatically"

2. **Show Validation Panel**
   - Review the right panel with issues
   - Point out different severity levels (errors vs warnings)

3. **Demonstrate Error**
   - If no errors, intentionally create one:
     - Drag an element outside safe zone
     - Click Validate again
   - Show: Error appears in panel

4. **Auto-Fix**
   - Click "Auto-fix" button on an issue
   - Point out: "Element automatically repositioned into safe zone"

5. **Add Required Disclaimer**
   - If alcohol product, show drinkaware warning
   - Click Auto-fix to add disclaimer
   - Point out: "Legal requirements are automatically handled"

**Talking Points:**
- "This catches compliance issues before expensive mistakes"
- "Appendix B and Tesco guidelines are built-in"
- "Auto-fix handles common issues automatically"
- "Legal team no longer needs to review every creative"

---

### 6. Multi-Channel Export (3 minutes)

**Demo Steps:**

1. **Open Export Dialog**
   - Click "Export" button
   - Point out: "Can export to multiple channels at once"

2. **Select Channels**
   - Select all four channels:
     - Facebook Feed
     - Instagram Feed
     - Instagram Story
     - In-Store A4

3. **Choose Format**
   - Select JPEG (smaller file size)
   - Point out: "All exports optimized to under 500KB"

4. **Export**
   - Click "Export 4 Channels"
   - Wait for processing
   - Show: File sizes displayed

5. **Download**
   - Click "Download All"
   - Open downloaded files to show quality

**Talking Points:**
- "One layout, four platform-optimized versions"
- "Each export respects the channel's specific requirements"
- "File sizes are optimized for platform limits"
- "This process used to take a designer 2+ hours"

---

### 7. Summary (2 minutes)

**Recap Benefits:**

| Before | After |
|--------|-------|
| 4+ hours per creative | 15 minutes |
| Manual compliance checks | Automatic validation |
| Multiple export sessions | One-click multi-export |
| Designer bottleneck | Self-service for marketers |

**Call to Action:**
> "Let's discuss how this could fit into your creative workflow."

---

## Troubleshooting

### Common Demo Issues

| Issue | Solution |
|-------|----------|
| AI generation slow | Mention it's processing, or use fallback stubs |
| Upload fails | Check file size (max 10MB), try different file |
| Export fails | Validate first, fix any errors |
| Canvas blank | Refresh page, re-upload assets |

### Recovery Scripts

**If AI generation fails:**
> "The AI service is experiencing high demand. Let me show you the manual workflow, which still provides all the compliance features."

**If validation shows unexpected errors:**
> "This demonstrates how thorough our validation is - even I triggered a compliance rule! Let me fix that."

---

## Sample Scenarios

### Scenario 1: Summer Beverage Campaign
- Upload: Soft drink packshot, brand logo, beach background
- Channel: Instagram Story
- Headline: "Cool Down This Summer"
- Validation: Check for drinkaware (if alcoholic alternative shown)

### Scenario 2: Grocery Promotion
- Upload: Cereal box, supermarket logo, kitchen background
- Channel: Facebook Feed
- Headline: "2 for £5 - This Week Only"
- Validation: T&Cs required for promotional offer

### Scenario 3: Sustainability Launch
- Upload: Eco-friendly product, FSC logo, nature background
- Channel: In-Store A4
- Headline: "Now with 100% Recycled Packaging"
- Validation: Sustainability claim certification

---

## Demo Environment Checklist

- [ ] Application running and accessible
- [ ] Sample assets folder available
- [ ] OpenAI API key configured (for live AI)
- [ ] Browser dev tools closed
- [ ] Screen sharing ready
- [ ] Backup slides prepared (if live demo fails)
