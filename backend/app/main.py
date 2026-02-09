"""
IEEE Report Restructurer - FastAPI Application
Main entry point for the backend API.
Serves both API and static frontend files.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from .config import get_settings
from .routers import documents


# Get the project root directory
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    
    # Ensure directories exist
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.output_dir, exist_ok=True)
    
    print("=" * 50)
    print("IEEE Report Restructurer API")
    print("=" * 50)
    print(f"Upload directory: {settings.upload_dir}")
    print(f"Output directory: {settings.output_dir}")
    print(f"Frontend directory: {FRONTEND_DIR}")
    print(f"Max upload size: {settings.max_upload_size_mb}MB")
    print(f"Word count range: {settings.min_section_words}-{settings.max_section_words}")
    print("=" * 50)
    
    yield
    
    # Shutdown
    print("Shutting down IEEE Report Restructurer API...")


# Create FastAPI application
app = FastAPI(
    title="IEEE Report Restructurer",
    description="Transform project reports into IEEE-formatted academic documents",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(documents.router)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/Kubernetes."""
    return {"status": "healthy", "service": "ieee-report-restructurer"}


@app.get("/api/info")
async def api_info():
    """API information endpoint."""
    return {
        "name": "IEEE Report Restructurer API",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs",
    }


# Serve static frontend files
# Mount CSS directory
if os.path.exists(os.path.join(FRONTEND_DIR, "css")):
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")

# Mount JS directory
if os.path.exists(os.path.join(FRONTEND_DIR, "js")):
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")

# Mount assets directory if exists
if os.path.exists(os.path.join(FRONTEND_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")


# Serve index.html for root path
@app.get("/")
async def serve_frontend():
    """Serve the frontend index.html."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Frontend not found. API is running at /docs"}


# Catch-all route for SPA (Single Page Application) routing
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve static files or fall back to index.html for SPA routing."""
    # Check if it's a static file
    static_path = os.path.join(FRONTEND_DIR, full_path)
    if os.path.exists(static_path) and os.path.isfile(static_path):
        return FileResponse(static_path)
    
    # Fall back to index.html for SPA routing
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    
    return {"error": "Not found"}


# API documentation customization
app.openapi_tags = [
    {
        "name": "documents",
        "description": "Document upload, processing, and download operations",
    },
]
