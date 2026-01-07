# Retail Media Creative Tool

> 🎨 AI-powered web application for creating retailer-compliant, brand-safe creatives

[![CI/CD Pipeline](https://github.com/your-org/retail-creative/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/retail-creative/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

The Retail Media Creative Tool enables advertisers to create retailer-compliant, brand-safe creatives (images) for multiple channels with:

- 🖼️ **Drag-and-drop visual editing** with React-Konva canvas
- 🤖 **AI-driven layout suggestions** powered by OpenAI
- ✅ **Automated guideline validation** (Appendix B / Tesco rules)
- 📤 **One-click multi-format export** (JPEG/PNG under 500KB)

### Supported Channels

| Channel | Dimensions | Use Case |
|---------|------------|----------|
| Facebook Feed | 1200×628 | Social media ads |
| Instagram Feed | 1080×1080 | Square format posts |
| Instagram Story | 1080×1920 | Vertical story format |
| In-Store A4 | 2480×3508 | Print displays |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose (optional)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/retail-creative.git
cd retail-creative

# Create environment file
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Start with Docker Compose
docker-compose up --build

# Access the application
open http://localhost
```

### Option 2: Local Development

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=your_key_here

# Run development server
uvicorn app.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Access at http://localhost:5173
```

## Project Structure

```
retail-creative/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry
│   │   ├── models.py            # Pydantic schemas
│   │   ├── utils.py             # Utility functions
│   │   ├── routes/
│   │   │   ├── upload.py        # Asset upload endpoints
│   │   │   ├── generate.py      # Layout generation
│   │   │   ├── validate.py      # Validation endpoints
│   │   │   └── export.py        # Export functionality
│   │   └── services/
│   │       ├── bg_remove.py     # Background removal (rembg)
│   │       ├── layout_llm.py    # LLM layout suggestions
│   │       ├── validators.py    # Appendix B rules
│   │       ├── renderer.py      # Image rendering
│   │       └── exporter.py      # Multi-format export
│   ├── tests/                   # Backend tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main application
│   │   ├── components/          # React components
│   │   ├── store/               # Zustand state
│   │   ├── api/                 # API client
│   │   └── types.ts             # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── docs/
│   ├── LLM_PROMPTS.md          # LLM prompt documentation
│   ├── VALIDATOR_RULES.md      # Validation rules reference
│   └── DEMO_SCRIPT.md          # Demo walkthrough
├── docker-compose.yml
└── README.md
```

## API Reference

### Upload Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload/packshot` | Upload product packshot |
| POST | `/upload/logo` | Upload brand logo |
| POST | `/upload/background` | Upload background image |
| DELETE | `/upload/{asset_id}` | Delete uploaded asset |

### Generation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/generate/layout` | Generate AI layout suggestions |

### Validation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/validate` | Validate layout against rules |

### Export Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/export` | Export creative to multiple formats |
| GET | `/exports/{filename}` | Download exported file |

## Validation Rules

The tool validates creatives against Appendix B / Tesco guidelines:

1. **Tesco Tag** - Tesco-specific layouts must include retailer tag
2. **Drinkaware** - Alcohol products require drinkaware.co.uk disclaimer
3. **Terms & Conditions** - Promotional offers need T&C text
4. **Competition Disclosure** - Competitions require TSBS promoter info
5. **Sustainability Claims** - Eco claims must cite certification
6. **Charity Promotions** - Charity promos need donation disclosure
7. **Price Display** - Prices must meet minimum visibility standards
8. **Claims Verification** - Health/product claims require substantiation
9. **Safe Zones** - Content must respect channel-specific margins
10. **Minimum Font Size** - Text must be readable (12px+ for body)
11. **WCAG Contrast** - Text must have 4.5:1 contrast ratio
12. **Required Elements** - All mandatory elements present
13. **Maximum Elements** - Prevent overcrowded layouts
14. **Background Required** - Must have background element
15. **Logo Required** - Must have brand logo

See [VALIDATOR_RULES.md](docs/VALIDATOR_RULES.md) for detailed documentation.

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v --cov=app
```

### Frontend Tests

```bash
cd frontend
npm run test:unit      # Unit tests
npm run test:e2e       # E2E tests with Playwright
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for layout suggestions |
| `LOG_LEVEL` | No | Logging level (default: INFO) |
| `MAX_UPLOAD_SIZE_MB` | No | Maximum upload size (default: 50) |

## Note on API keys & costs

- **Paid API keys required for full functionality:** Several features (LLM-driven layout suggestions, advanced moderation, and large-model image handling) rely on third-party APIs such as OpenAI, Groq, xAI (Grok), and Google Gemini. These providers often require paid API keys for reliable, production-ready throughput and higher-quality models.
- **Background removal & heavy media processing may be costly:** Services like `rembg` or other cloud-based image processing/vision APIs can consume significant CPU/GPU time and may incur costs or require native libraries that are heavy to run locally.
- **Local alternatives and free tiers:** Ollama can run models locally (no API key) but requires a capable machine and disk space. Some providers offer free tiers (Groq/Grok/Gemini) but with usage limits—expect to hit paid tiers for sustained or production use.
- **Recommendation:** For local development, set `LLM_PROVIDER` to `ollama` (if you have it) or use small/free models and sample data. For staging/production, budget for API usage and monitor costs closely. Keep sensitive API keys out of source control (use `.env` or secret managers).

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [rembg](https://github.com/danielgatis/rembg) for background removal
- [React-Konva](https://konvajs.org/docs/react/) for canvas editing
- [Tailwind CSS](https://tailwindcss.com/) for styling
- [FastAPI](https://fastapi.tiangolo.com/) for the backend API
