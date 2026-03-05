"""
Documents Router for IEEE Report Restructurer.
Handles all document-related API endpoints.
"""

import os
import asyncio
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ..models.document import Document, ProcessingStatus, GlobalContext
from ..models.section import Section, IEEECategory
from ..services.file_service import FileService
from ..services.parser_service import ParserService
from ..services.context_extractor import ContextExtractor
from ..services.llm_service import LLMService
from ..services.ieee_formatter import IEEEFormatter
from ..services.export_service import ExportService
from ..services.post_processor import PostProcessor
from ..config import get_settings


router = APIRouter(prefix="/api", tags=["documents"])

# In-memory document storage (for MVP - replace with database in production)
documents_store: dict[str, Document] = {}

# Service instances
file_service = FileService()
parser_service = ParserService()
llm_service = LLMService()
context_extractor = ContextExtractor(llm_service)
ieee_formatter = IEEEFormatter()
export_service = ExportService()
post_processor = PostProcessor()


# Request/Response models
class SectionUpdate(BaseModel):
    """Request model for updating a section."""
    content: str


class ProcessingOptions(BaseModel):
    """Request model for processing options."""
    generate_abstract: bool = True
    balance_word_counts: bool = True
    format_references: bool = True


class SectionResponse(BaseModel):
    """Response model for a section."""
    id: str
    title: str
    content: str
    category: str
    ieee_number: Optional[str]
    word_count: int
    is_processed: bool
    level: int


# Endpoints
@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document for processing.
    
    Accepts .docx and .pdf files.
    Returns document ID for tracking.
    """
    settings = get_settings()
    
    # Read file content
    content = await file.read()
    
    # Validate file
    is_valid, error = file_service.validate_file(file.filename, len(content))
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    
    # Create document record
    doc = Document(filename=file.filename)
    
    # Save file
    try:
        file_path = await file_service.save_file(file.filename, content, doc.id)
        doc.file_path = file_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Store document
    documents_store[doc.id] = doc
    
    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status.value,
        "message": "File uploaded successfully. Call /api/process/{id} to start processing."
    }


@router.post("/process/{doc_id}")
async def process_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    options: Optional[ProcessingOptions] = None
):
    """
    Start processing an uploaded document.
    
    Processing runs in background. Use /api/status/{id} to check progress.
    """
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_store[doc_id]
    
    if doc.status not in [ProcessingStatus.UPLOADED, ProcessingStatus.ERROR]:
        raise HTTPException(
            status_code=400,
            detail=f"Document is already being processed. Current status: {doc.status.value}"
        )
    
    # Use default options if not provided
    if options is None:
        options = ProcessingOptions()
    
    # Start background processing
    background_tasks.add_task(
        process_document_task,
        doc_id,
        options
    )
    
    return {
        "id": doc_id,
        "status": "processing_started",
        "message": "Document processing started. Check /api/status/{id} for progress."
    }


async def process_document_task(doc_id: str, options: ProcessingOptions):
    """Background task for document processing."""
    doc = documents_store[doc_id]
    
    try:
        # Step 1: Parse document
        doc.update_status(ProcessingStatus.PARSING, "Extracting text from document...", 5)
        
        full_text, paragraphs = file_service.extract_text(doc.file_path)
        doc.original_text = full_text
        
        # Step 2: Parse sections
        doc.update_status(ProcessingStatus.PARSING, "Detecting sections...", 15)
        
        sections = parser_service.parse_sections(paragraphs)
        
        # If no sections detected, try AI inference
        if len(sections) <= 1:
            doc.update_status(ProcessingStatus.PARSING, "Inferring section structure with AI...", 20)
            try:
                inferred = await llm_service.infer_headings(full_text)
                # Reconstruct sections from inference
                if inferred:
                    sections = []
                    for i, info in enumerate(inferred):
                        section = Section(
                            title=info.get("heading", f"Section {i+1}"),
                            original_content="",  # Will be filled based on text position
                            category=IEEECategory(info.get("category", "other")),
                            level=1,
                        )
                        sections.append(section)
            except Exception as e:
                doc.add_error(f"Section inference failed: {str(e)}")
        
        doc.sections = sections
        
        # Step 3: Extract context
        doc.update_status(ProcessingStatus.EXTRACTING_CONTEXT, "Extracting document context...", 25)
        
        context = await context_extractor.extract_context(full_text)
        doc.context = context
        
        # Step 4: Rewrite sections
        doc.update_status(ProcessingStatus.REWRITING, "Rewriting sections...", 30)
        
        async def update_progress(index: int, total: int):
            progress = 30 + int((index / total) * 40)
            doc.update_status(
                ProcessingStatus.REWRITING,
                f"Rewriting section {index + 1} of {total}...",
                progress
            )
            doc.current_section_index = index
        
        sections = await llm_service.process_sections_parallel(
            sections,
            context,
            callback=update_progress
        )
        doc.sections = sections
        
        # Step 5: Apply full IEEE formatting pipeline
        doc.update_status(ProcessingStatus.STRUCTURING, "Applying IEEE structure and formatting...", 75)
        
        # Use the new comprehensive formatting pipeline
        sections, validation_report = ieee_formatter.format_document(sections, context)
        doc.sections = sections
        
        # Log any compliance warnings
        if validation_report.get("warnings"):
            for warning in validation_report["warnings"]:
                doc.add_error(f"Warning: {warning}")
        
        # Step 6: Post-processing (final cleanup + word count logging)
        doc.update_status(ProcessingStatus.STRUCTURING, "Running post-processing checks...", 82)
        sections, word_count_log = post_processor.run_post_processing(sections)
        doc.sections = sections
        
        # Step 7: Generate output
        doc.update_status(ProcessingStatus.FORMATTING, "Generating IEEE document...", 85)
        
        result = export_service.generate_both_formats(doc, sections, context)
        
        doc.output_docx_path = result.get("docx_path")
        doc.output_pdf_path = result.get("pdf_path")
        
        if result.get("errors"):
            for error in result["errors"]:
                doc.add_error(error)
        
        # Done!
        doc.update_status(ProcessingStatus.COMPLETE, "Processing complete!", 100)
        
    except Exception as e:
        doc.update_status(ProcessingStatus.ERROR, f"Processing failed: {str(e)}", doc.progress_percent)
        doc.add_error(str(e))


@router.get("/status/{doc_id}")
async def get_status(doc_id: str):
    """Get document processing status."""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_store[doc_id]
    return doc.to_status_response()


@router.get("/sections/{doc_id}")
async def get_sections(doc_id: str) -> List[SectionResponse]:
    """Get all sections of a processed document."""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_store[doc_id]
    
    return [
        SectionResponse(
            id=s.id,
            title=s.title,
            content=s.rewritten_content or s.original_content,
            category=s.category if isinstance(s.category, str) else s.category.value,
            ieee_number=s.ieee_number,
            word_count=s.word_count,
            is_processed=s.is_processed,
            level=s.level,
        )
        for s in doc.sections
    ]


@router.put("/sections/{doc_id}/{section_id}")
async def update_section(doc_id: str, section_id: str, update: SectionUpdate):
    """Update a section's content."""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_store[doc_id]
    
    # Find section
    section = None
    for s in doc.sections:
        if s.id == section_id:
            section = s
            break
    
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    # Update content
    section.rewritten_content = update.content
    section.calculate_word_count()
    
    return {
        "id": section.id,
        "title": section.title,
        "word_count": section.word_count,
        "message": "Section updated successfully"
    }


@router.post("/regenerate/{doc_id}")
async def regenerate_document(doc_id: str, background_tasks: BackgroundTasks):
    """Regenerate output documents after editing sections."""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_store[doc_id]
    
    # Generate new output
    doc.update_status(ProcessingStatus.FORMATTING, "Regenerating document...", 90)
    
    background_tasks.add_task(
        regenerate_task,
        doc_id
    )
    
    return {
        "id": doc_id,
        "message": "Document regeneration started"
    }


async def regenerate_task(doc_id: str):
    """Background task for regenerating documents."""
    doc = documents_store[doc_id]
    
    try:
        result = export_service.generate_both_formats(doc, doc.sections, doc.context)
        doc.output_docx_path = result.get("docx_path")
        doc.output_pdf_path = result.get("pdf_path")
        doc.update_status(ProcessingStatus.COMPLETE, "Document regenerated!", 100)
    except Exception as e:
        doc.update_status(ProcessingStatus.ERROR, f"Regeneration failed: {str(e)}")


@router.get("/download/{doc_id}")
async def download_document(doc_id: str, format: str = "docx"):
    """
    Download the processed document.
    
    Args:
        doc_id: Document ID
        format: 'docx' or 'pdf'
    """
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_store[doc_id]
    
    if doc.status != ProcessingStatus.COMPLETE:
        raise HTTPException(
            status_code=400,
            detail=f"Document is not ready. Current status: {doc.status.value}"
        )
    
    if format.lower() == "docx":
        if not doc.output_docx_path or not os.path.exists(doc.output_docx_path):
            raise HTTPException(status_code=404, detail="DOCX file not found")
        return FileResponse(
            doc.output_docx_path,
            filename=f"IEEE_{doc.filename}",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    elif format.lower() == "pdf":
        if not doc.output_pdf_path or not os.path.exists(doc.output_pdf_path):
            raise HTTPException(status_code=404, detail="PDF file not found. PDF conversion may not be available.")
        return FileResponse(
            doc.output_pdf_path,
            filename=f"IEEE_{doc.filename.replace('.docx', '.pdf').replace('.pdf', '.pdf')}",
            media_type="application/pdf"
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'docx' or 'pdf'")


@router.get("/context/{doc_id}")
async def get_context(doc_id: str):
    """Get extracted document context."""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_store[doc_id]
    
    return {
        "project_title": doc.context.project_title,
        "domain": doc.context.domain,
        "objective": doc.context.objective,
        "keywords": doc.context.keywords,
        "authors": doc.context.authors,
    }


@router.get("/stats/{doc_id}")
async def get_stats(doc_id: str):
    """Get section statistics for a document."""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_store[doc_id]
    
    return ieee_formatter.calculate_section_stats(doc.sections)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and its files."""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_store[doc_id]
    
    # Clean up files
    if doc.file_path:
        file_service.cleanup_file(doc.file_path)
    if doc.output_docx_path:
        file_service.cleanup_file(doc.output_docx_path)
    if doc.output_pdf_path:
        file_service.cleanup_file(doc.output_pdf_path)
    
    # Remove from store
    del documents_store[doc_id]
    
    return {"message": "Document deleted successfully"}


@router.get("/test-llm")
async def test_llm():
    """
    Test LLM connection with a simple prompt.
    Used to verify the Groq client works correctly.
    """
    try:
        result = await llm_service.test_connection()
        return {
            "status": "success",
            "message": "LLM connection working!",
            "response": result
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"LLM connection failed: {str(e)}"
            }
        )
