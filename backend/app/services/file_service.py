"""
File Service for IEEE Report Restructurer.
Handles file upload, parsing, and text extraction from DOCX and PDF files.
"""

import os
import re
from typing import Tuple, List
from pathlib import Path
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.shared import Pt

from ..config import get_settings


class FileService:
    """Service for handling file operations and text extraction."""
    
    def __init__(self):
        self.settings = get_settings()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure upload and output directories exist."""
        os.makedirs(self.settings.upload_dir, exist_ok=True)
        os.makedirs(self.settings.output_dir, exist_ok=True)
    
    def validate_file(self, filename: str, file_size: int) -> Tuple[bool, str]:
        """
        Validate uploaded file.
        
        Args:
            filename: Name of the uploaded file
            file_size: Size of the file in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in self.settings.allowed_extensions:
            return False, f"Invalid file type. Allowed: {', '.join(self.settings.allowed_extensions)}"
        
        # Check size
        max_size_bytes = self.settings.max_upload_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return False, f"File too large. Maximum size: {self.settings.max_upload_size_mb}MB"
        
        return True, ""
    
    async def save_file(self, filename: str, content: bytes, doc_id: str) -> str:
        """
        Save uploaded file to disk.
        
        Args:
            filename: Original filename
            content: File content as bytes
            doc_id: Document ID for unique naming
            
        Returns:
            Path to saved file
        """
        ext = Path(filename).suffix.lower()
        safe_filename = f"{doc_id}{ext}"
        file_path = os.path.join(self.settings.upload_dir, safe_filename)
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        return file_path
    
    def extract_text(self, file_path: str) -> Tuple[str, List[dict]]:
        """
        Extract text and structure from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (full_text, paragraphs_with_metadata)
        """
        ext = Path(file_path).suffix.lower()
        
        if ext == ".docx":
            return self._extract_from_docx(file_path)
        elif ext == ".pdf":
            return self._extract_from_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")
    
    def _extract_from_docx(self, file_path: str) -> Tuple[str, List[dict]]:
        """
        Extract text from DOCX file preserving structure.
        
        Returns:
            Tuple of (full_text, paragraphs_with_metadata)
        """
        doc = DocxDocument(file_path)
        paragraphs = []
        full_text_parts = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            
            # Detect if this is a heading
            is_heading = False
            heading_level = 0
            
            # Check paragraph style
            style_name = para.style.name.lower() if para.style else ""
            if "heading" in style_name:
                is_heading = True
                # Extract heading level from style name (e.g., "Heading 1" -> 1)
                match = re.search(r'heading\s*(\d+)', style_name)
                if match:
                    heading_level = int(match.group(1))
                else:
                    heading_level = 1
            
            # Additional heading detection heuristics
            if not is_heading:
                # Check if text is short, all caps, or bold
                runs = para.runs
                if runs:
                    first_run = runs[0]
                    if first_run.bold and len(text) < 100:
                        is_heading = True
                        heading_level = 2
                
                # Check for numbered headings (e.g., "1. Introduction", "I. INTRODUCTION")
                if re.match(r'^(?:\d+\.|[IVXLC]+\.)\s*[A-Z]', text):
                    is_heading = True
                    heading_level = 1
                elif re.match(r'^(?:[A-Z]\.|[a-z]\))\s+', text):
                    is_heading = True
                    heading_level = 2
            
            # Check for all caps (common for IEEE headings)
            if text.isupper() and len(text) < 100:
                is_heading = True
                heading_level = 1
            
            para_data = {
                "text": text,
                "is_heading": is_heading,
                "heading_level": heading_level,
                "style": style_name,
            }
            paragraphs.append(para_data)
            full_text_parts.append(text)
        
        full_text = "\n\n".join(full_text_parts)
        return full_text, paragraphs
    
    def _extract_from_pdf(self, file_path: str) -> Tuple[str, List[dict]]:
        """
        Extract text from PDF file.
        
        Returns:
            Tuple of (full_text, paragraphs_with_metadata)
        """
        doc = fitz.open(file_path)
        paragraphs = []
        full_text_parts = []
        
        for page_num, page in enumerate(doc):
            # Get text blocks with position and font info
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if block["type"] != 0:  # Skip non-text blocks
                    continue
                
                for line in block.get("lines", []):
                    line_text_parts = []
                    max_font_size = 0
                    is_bold = False
                    
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            line_text_parts.append(text)
                            font_size = span.get("size", 12)
                            max_font_size = max(max_font_size, font_size)
                            
                            # Check for bold font
                            font_name = span.get("font", "").lower()
                            if "bold" in font_name:
                                is_bold = True
                    
                    line_text = " ".join(line_text_parts).strip()
                    if not line_text:
                        continue
                    
                    # Heading detection heuristics for PDF
                    is_heading = False
                    heading_level = 0
                    
                    # Larger font sizes typically indicate headings
                    if max_font_size > 12:
                        is_heading = True
                        if max_font_size > 16:
                            heading_level = 1
                        else:
                            heading_level = 2
                    
                    # Bold text that's short is likely a heading
                    if is_bold and len(line_text) < 100:
                        is_heading = True
                        heading_level = heading_level or 2
                    
                    # Check for numbered headings
                    if re.match(r'^(?:\d+\.|[IVXLC]+\.)\s*[A-Z]', line_text):
                        is_heading = True
                        heading_level = 1
                    
                    # All caps detection
                    if line_text.isupper() and len(line_text) < 100:
                        is_heading = True
                        heading_level = 1
                    
                    para_data = {
                        "text": line_text,
                        "is_heading": is_heading,
                        "heading_level": heading_level,
                        "font_size": max_font_size,
                        "page": page_num + 1,
                    }
                    paragraphs.append(para_data)
                    full_text_parts.append(line_text)
        
        doc.close()
        
        # Merge consecutive non-heading paragraphs
        merged_paragraphs = self._merge_paragraphs(paragraphs)
        full_text = "\n\n".join(p["text"] for p in merged_paragraphs)
        
        return full_text, merged_paragraphs
    
    def _merge_paragraphs(self, paragraphs: List[dict]) -> List[dict]:
        """Merge consecutive non-heading paragraphs."""
        if not paragraphs:
            return []
        
        merged = []
        current = None
        
        for para in paragraphs:
            if para["is_heading"]:
                if current:
                    merged.append(current)
                    current = None
                merged.append(para)
            else:
                if current:
                    current["text"] += " " + para["text"]
                else:
                    current = para.copy()
        
        if current:
            merged.append(current)
        
        return merged
    
    def cleanup_file(self, file_path: str):
        """Remove a file from disk."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass  # Ignore cleanup errors
