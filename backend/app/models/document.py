"""
Document model for IEEE Report Restructurer.
Represents the entire document being processed.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from .section import Section


class ProcessingStatus(str, Enum):
    """Document processing status."""
    UPLOADED = "uploaded"
    PARSING = "parsing"
    EXTRACTING_CONTEXT = "extracting_context"
    REWRITING = "rewriting"
    STRUCTURING = "structuring"
    FORMATTING = "formatting"
    COMPLETE = "complete"
    ERROR = "error"


class GlobalContext(BaseModel):
    """Global context extracted from the document."""
    project_title: str = ""
    domain: str = ""
    objective: str = ""
    keywords: List[str] = []
    authors: List[str] = []
    abstract_text: str = ""


class Document(BaseModel):
    """Represents the entire document being processed."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_text: str = ""
    file_path: Optional[str] = None
    
    # Processing state
    status: ProcessingStatus = ProcessingStatus.UPLOADED
    status_message: str = ""
    progress_percent: int = 0
    current_section_index: int = 0
    
    # Context and sections
    context: GlobalContext = Field(default_factory=GlobalContext)
    sections: List[Section] = []
    
    # Output files
    output_docx_path: Optional[str] = None
    output_pdf_path: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Error tracking
    errors: List[str] = []
    
    def update_status(self, status: ProcessingStatus, message: str = "", progress: int = -1):
        """Update processing status."""
        self.status = status
        self.status_message = message
        if progress >= 0:
            self.progress_percent = progress
        self.updated_at = datetime.utcnow()
    
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
        self.updated_at = datetime.utcnow()
    
    def get_total_word_count(self) -> int:
        """Calculate total word count across all sections."""
        return sum(s.word_count for s in self.sections)
    
    def to_status_response(self) -> Dict[str, Any]:
        """Convert to status response for API."""
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status.value,
            "status_message": self.status_message,
            "progress_percent": self.progress_percent,
            "current_section_index": self.current_section_index,
            "total_sections": len(self.sections),
            "errors": self.errors,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    class Config:
        use_enum_values = True
