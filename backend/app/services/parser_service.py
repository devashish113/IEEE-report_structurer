"""
Parser Service for IEEE Report Restructurer.
Handles section detection, splitting, and classification.
"""

import re
from typing import List, Optional
from ..models.section import Section, IEEECategory, CATEGORY_KEYWORDS
from ..config import get_settings


class ParserService:
    """Service for parsing document structure and detecting sections."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def parse_sections(self, paragraphs: List[dict]) -> List[Section]:
        """
        Parse paragraphs into sections.
        
        Args:
            paragraphs: List of paragraph dictionaries with text and metadata
            
        Returns:
            List of Section objects
        """
        sections = []
        current_section = None
        current_content_parts = []
        
        for para in paragraphs:
            if para.get("is_heading", False):
                # Save previous section
                if current_section and current_content_parts:
                    current_section.original_content = "\n\n".join(current_content_parts)
                    current_section.calculate_word_count()
                    sections.append(current_section)
                
                # Start new section
                heading_text = para["text"]
                heading_level = para.get("heading_level", 1)
                
                # Clean the heading text
                clean_heading = self._clean_heading(heading_text)
                
                # Classify the section
                category = self._classify_section(clean_heading, "")
                
                current_section = Section(
                    title=clean_heading,
                    original_content="",
                    category=category,
                    level=heading_level,
                )
                current_content_parts = []
            else:
                # Add to current section content
                if current_section:
                    current_content_parts.append(para["text"])
                else:
                    # Content before first heading - treat as initial content
                    # Could be title, abstract, or unmarked introduction
                    if not sections:
                        current_section = Section(
                            title="Untitled Section",
                            original_content="",
                            category=IEEECategory.OTHER,
                            level=1,
                        )
                    current_content_parts.append(para["text"])
        
        # Don't forget the last section
        if current_section and current_content_parts:
            current_section.original_content = "\n\n".join(current_content_parts)
            current_section.calculate_word_count()
            sections.append(current_section)
        
        # Post-process: classify sections based on content if title wasn't clear
        for section in sections:
            if section.category == IEEECategory.OTHER:
                section.category = self._classify_section(
                    section.title, 
                    section.original_content[:500]
                )
        
        return sections
    
    def _clean_heading(self, heading: str) -> str:
        """Clean and normalize heading text."""
        # Remove numbering prefixes
        heading = re.sub(r'^(?:\d+\.|[IVXLC]+\.|[A-Za-z]\.|[a-z]\))\s*', '', heading)
        
        # Normalize case (title case)
        if heading.isupper():
            heading = heading.title()
        
        return heading.strip()
    
    def _classify_section(self, title: str, content: str) -> IEEECategory:
        """
        Classify a section into an IEEE category.
        
        Args:
            title: Section title
            content: Section content (first part)
            
        Returns:
            IEEECategory enum value
        """
        title_lower = title.lower()
        content_lower = content.lower() if content else ""
        
        # Check each category's keywords
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in title_lower:
                    return category
                # Less confident match on content
                if keyword in content_lower[:200]:
                    return category
        
        return IEEECategory.OTHER
    
    def detect_references(self, text: str) -> List[str]:
        """
        Detect and extract references from text.
        
        Args:
            text: Full document text or references section
            
        Returns:
            List of individual reference strings
        """
        references = []
        
        # Split by common reference patterns
        # Pattern 1: Numbered references [1], [2], etc.
        numbered_refs = re.findall(r'\[(\d+)\][^\[]+', text)
        if numbered_refs:
            # Extract full references
            for match in re.finditer(r'\[\d+\]\s*([^\[]+?)(?=\[\d+\]|$)', text, re.DOTALL):
                ref = match.group(0).strip()
                if len(ref) > 20:
                    references.append(ref)
        
        # Pattern 2: Line-based references (after "References" heading)
        if not references:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                # Skip short lines and lines that look like headings
                if len(line) > 30 and not line.isupper():
                    # Check if it looks like a reference (has author-like patterns)
                    if re.search(r'[A-Z][a-z]+,?\s+[A-Z]\.', line) or \
                       re.search(r'\(\d{4}\)', line) or \
                       re.search(r'\d{4}\.', line):
                        references.append(line)
        
        return references
    
    def merge_sections_by_category(self, sections: List[Section]) -> List[Section]:
        """
        Merge sections that have the same category.
        
        Args:
            sections: List of sections
            
        Returns:
            Merged list of sections
        """
        merged = {}
        
        for section in sections:
            cat = section.category
            if cat in merged:
                # Append content to existing section
                merged[cat].original_content += "\n\n" + section.original_content
                merged[cat].calculate_word_count()
            else:
                merged[cat] = section
        
        return list(merged.values())
    
    def split_large_section(self, section: Section, max_words: int = 800) -> List[Section]:
        """
        Split a large section into smaller parts.
        
        Args:
            section: Section to split
            max_words: Maximum words per split section
            
        Returns:
            List of split sections
        """
        content = section.get_content()
        words = content.split()
        
        if len(words) <= max_words:
            return [section]
        
        splits = []
        paragraphs = content.split('\n\n')
        current_content = []
        current_word_count = 0
        part_num = 1
        
        for para in paragraphs:
            para_words = len(para.split())
            
            if current_word_count + para_words > max_words and current_content:
                # Create new section
                new_section = Section(
                    title=f"{section.title} (Part {part_num})",
                    original_content="\n\n".join(current_content),
                    category=section.category,
                    level=section.level,
                )
                new_section.calculate_word_count()
                splits.append(new_section)
                
                current_content = [para]
                current_word_count = para_words
                part_num += 1
            else:
                current_content.append(para)
                current_word_count += para_words
        
        # Add remaining content
        if current_content:
            new_section = Section(
                title=f"{section.title} (Part {part_num})" if part_num > 1 else section.title,
                original_content="\n\n".join(current_content),
                category=section.category,
                level=section.level,
            )
            new_section.calculate_word_count()
            splits.append(new_section)
        
        return splits
