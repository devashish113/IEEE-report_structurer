# IEEE Report Restructurer - Backend

FastAPI backend for the IEEE Report Restructurer application.

## Setup

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your GROQ_API_KEY

# Run server
uvicorn app.main:app --reload --port 8000
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Services

- **FileService**: File upload and text extraction
- **ParserService**: Section detection and classification
- **ContextExtractor**: Extract title, domain, objective
- **LLMService**: Groq API integration for rewriting
- **IEEEFormatter**: Apply IEEE structure and numbering
- **ExportService**: Generate DOCX and PDF

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| GROQ_API_KEY | Groq API key | Required |
| GROQ_MODEL | LLM model | llama-3.1-8b-instant |
| MAX_UPLOAD_SIZE_MB | Max file size | 50 |
| MIN_SECTION_WORDS | Min words per section | 200 |
| MAX_SECTION_WORDS | Max words per section | 400 |
