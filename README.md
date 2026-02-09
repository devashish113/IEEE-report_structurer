# IEEE Report Restructurer

Transform project reports into IEEE-formatted academic documents using AI-powered restructuring.

![IEEE Report Restructurer](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-orange.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

## Features

- **Document Upload**: Upload DOCX or PDF project reports
- **AI-Powered Restructuring**: Uses Groq LLM (Llama 3.1) for intelligent rewriting
- **IEEE Format Compliance**: Automatic section numbering (I., II., III.), heading normalization, citation conversion
- **Section Length Control**: Automatically expands short sections and compresses long ones
- **Dual Export**: Download as DOCX or PDF
- **Live Editing**: Edit sections directly in the browser before export
- **Full-Stack Deployment**: Docker, Nginx, and Jenkins CI/CD ready

## Quick Start

### Option 1: Run Locally (Development)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd ieee-report-restructurer

# 2. Create virtual environment
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Edit .env and add your GROQ_API_KEY

# 5. Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Open browser
# Visit: http://localhost:8000
```

### Option 2: Docker (Production)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd ieee-report-restructurer

# 2. Configure environment
copy .env.example .env
# Edit .env and add your GROQ_API_KEY

# 3. Build and run with Docker Compose
docker-compose up -d

# 4. Open browser
# Visit: http://localhost:8000

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 3: Docker with Nginx (Production with SSL)

```bash
# 1. Configure .env file
# 2. Add SSL certificates to nginx/ssl/
# 3. Run with production profile
docker-compose --profile production up -d

# Visit: http://localhost (or https with SSL configured)
```

## Project Structure

```
ieee-report-restructurer/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app (serves frontend + API)
│   │   ├── config.py         # Configuration settings
│   │   ├── routers/          # API endpoints
│   │   ├── services/         # Business logic
│   │   ├── models/           # Data models
│   │   └── prompts/          # LLM prompt templates
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── index.html            # Main HTML page
│   ├── css/styles.css        # Styling
│   └── js/app.js             # Frontend JavaScript
├── nginx/
│   └── nginx.conf            # Nginx reverse proxy config
├── Dockerfile                # Docker build file
├── docker-compose.yml        # Docker orchestration
├── Jenkinsfile               # CI/CD pipeline
├── .env.example              # Environment template
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve frontend |
| GET | `/health` | Health check |
| POST | `/api/upload` | Upload document |
| POST | `/api/process/{id}` | Start processing |
| GET | `/api/status/{id}` | Get processing status |
| GET | `/api/sections/{id}` | Get processed sections |
| PUT | `/api/sections/{id}/{section_id}` | Update section |
| GET | `/api/download/{id}?format=docx\|pdf` | Download document |
| GET | `/docs` | Swagger API documentation |

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | **Required** - Groq API key | - |
| `GROQ_MODEL` | LLM model to use | `llama-3.1-8b-instant` |
| `MAX_UPLOAD_SIZE_MB` | Maximum file upload size | `50` |
| `MIN_SECTION_WORDS` | Expand sections below this | `250` |
| `MAX_SECTION_WORDS` | Compress sections above this | `600` |
| `TARGET_SECTION_WORDS` | Target word count per section | `400` |

### Getting a Groq API Key

1. Go to [https://console.groq.com/](https://console.groq.com/)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy and paste into your `.env` file

## Jenkins CI/CD

The included `Jenkinsfile` provides:

- **Code Quality**: Linting with Ruff
- **Docker Build**: Multi-stage image building
- **Testing**: Container health checks
- **Security Scan**: Trivy vulnerability scanning
- **Deployment**: Automatic staging/production deployment

### Jenkins Setup

1. Install Jenkins with Docker support
2. Add credentials:
   - `groq-api-key`: Your Groq API key (Secret text)
   - `docker-registry-credentials`: Docker registry login
3. Create a pipeline job pointing to this repository
4. Run the pipeline!

## IEEE Formatting Features

### Section Numbering
- Main sections: I., II., III., IV., etc.
- Subsections: A., B., C., etc.
- Sub-subsections: 1), 2), 3), etc.

### Heading Normalization
- "Introduction Of The Study" → "INTRODUCTION"
- "Literature Review" → "RELATED WORK"
- "Research Methodology" → "METHODOLOGY"

### Content Processing
- Abstract normalization: "Abstract— text..."
- Keywords format: "Index Terms— term1, term2..."
- Reference formatting: [1], [2], [3] numbered style
- Citation conversion: (Author, 2023) → [1]

## Troubleshooting

### "GROQ_API_KEY not set"
Make sure your `.env` file contains a valid API key.

### PDF not downloading
Ensure `fpdf2` is installed: `pip install fpdf2`

### Processing stuck
Check the console logs for LLM errors. The Groq API has rate limits.

### Docker build fails
Ensure Docker is running and you have sufficient disk space.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Groq](https://groq.com/) - Fast LLM inference
- [fpdf2](https://github.com/py-pdf/fpdf2) - PDF generation
- [python-docx](https://python-docx.readthedocs.io/) - DOCX generation
