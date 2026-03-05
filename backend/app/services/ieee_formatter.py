"""
IEEE Formatter Service for IEEE Report Restructurer.
Handles section reordering, numbering, heading normalization, citation conversion,
deduplication, HTML cleanup, placeholder replacement, and IEEE structure enforcement.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from ..models.section import Section, IEEECategory, IEEE_SECTION_ORDER
from ..models.document import GlobalContext
from ..config import get_settings

logger = logging.getLogger(__name__)

# Sections to remove (non-paper metadata)
NON_PAPER_SECTIONS = [
    "submission", "submitted", "declaration", "acknowledgment form",
    "cover page", "title page", "table of contents", "list of figures",
    "list of tables", "approval sheet", "certificate", "bonafide",
    "plagiarism", "turnitin", "originality", "sign", "signature",
    "supervisor", "guide", "examiner", "viva", "placeholder",
    "to be added", "tbd", "todo", "draft"
]

# Sections that should be merged into Introduction
MERGE_INTO_INTRO = [
    "objective", "objectives", "aim", "aims", "purpose",
    "problem statement", "problem definition", "motivation",
    "overview", "scope", "objectives of study",
    "objectives of the study"
]

# Sections that should be promoted to main sections (level 1)
PROMOTE_TO_MAIN = [
    "methodology", "proposed methodology", "research methodology",
    "system design", "system architecture", "proposed system",
    "implementation", "results", "results and discussion",
    "data analysis", "data analysis and interpretation",
    "literature review", "related work",
    "conclusion", "future work"
]

# Heading normalization map (narrative → IEEE standard)
HEADING_NORMALIZATION = {
    # Introduction variants
    "introduction of the study": "INTRODUCTION",
    "introduction to the study": "INTRODUCTION",
    "introduction of study": "INTRODUCTION",
    "chapter 1 introduction": "INTRODUCTION",
    "chapter one introduction": "INTRODUCTION",
    "1. introduction": "INTRODUCTION",
    "i. introduction": "INTRODUCTION",
    "introduction:": "INTRODUCTION",
    
    # Literature Review variants
    "literature review": "RELATED WORK",
    "literature survey": "RELATED WORK",
    "review of literature": "RELATED WORK",
    "related works": "RELATED WORK",
    "background study": "RELATED WORK",
    "previous work": "RELATED WORK",
    "prior work": "RELATED WORK",
    
    # Methodology variants
    "methodology of the study": "METHODOLOGY",
    "research methodology": "METHODOLOGY",
    "proposed methodology": "METHODOLOGY",
    "materials and methods": "METHODOLOGY",
    "methods": "METHODOLOGY",
    "approach": "METHODOLOGY",
    "methodology:": "METHODOLOGY",
    
    # System Design variants
    "system design and architecture": "SYSTEM DESIGN",
    "proposed system": "SYSTEM DESIGN",
    "system architecture": "SYSTEM DESIGN",
    "design and implementation": "SYSTEM DESIGN",
    "architectural design": "SYSTEM DESIGN",
    "system design:": "SYSTEM DESIGN",
    
    # Implementation variants
    "implementation details": "IMPLEMENTATION",
    "implementation and testing": "IMPLEMENTATION",
    "system implementation": "IMPLEMENTATION",
    "implementation:": "IMPLEMENTATION",
    
    # Results variants
    "results and discussion": "RESULTS AND DISCUSSION",
    "results and analysis": "RESULTS AND DISCUSSION",
    "experimental results": "RESULTS AND DISCUSSION",
    "findings": "RESULTS AND DISCUSSION",
    "analysis and results": "RESULTS AND DISCUSSION",
    "data analysis and interpretation": "RESULTS AND DISCUSSION",
    "discussion": "RESULTS AND DISCUSSION",
    "results:": "RESULTS AND DISCUSSION",
    
    # Conclusion variants
    "conclusion and future work": "CONCLUSION",
    "conclusions": "CONCLUSION",
    "conclusion and recommendations": "CONCLUSION",
    "summary and conclusion": "CONCLUSION",
    "concluding remarks": "CONCLUSION",
    "future work": "CONCLUSION",
    "future scope": "CONCLUSION",
    "conclusion:": "CONCLUSION",
}

# Placeholder patterns to replace
PLACEHOLDER_PATTERNS = [
    (r'\[Your Name\]', ''),
    (r'\[Author Name\]', ''),
    (r'\[Name\]', ''),
    (r'\[Date\]', ''),
    (r'\[Title\]', ''),
    (r'\[Institution\]', ''),
    (r'\[University\]', ''),
    (r'\[College Name\]', ''),
    (r'\[Department\]', ''),
    (r'\[Email\]', ''),
    (r'\[Phone\]', ''),
    (r'\[Address\]', ''),
    (r'\[Insert .+?\]', ''),
    (r'\[TODO.*?\]', ''),
    (r'\[TBD.*?\]', ''),
    (r'\[PLACEHOLDER.*?\]', ''),
    (r'\[Your .+?\]', ''),
    (r'<Your Name>', ''),
    (r'<Author>', ''),
]

# HTML artifacts to strip
HTML_PATTERNS = [
    r'<hr\s*/?>',
    r'<br\s*/?>',
    r'</?div[^>]*>',
    r'</?span[^>]*>',
    r'</?p[^>]*>',
    r'</?strong>',
    r'</?em>',
    r'</?b>',
    r'</?i>',
    r'</?u>',
    r'&nbsp;',
    r'&amp;',
    r'&lt;',
    r'&gt;',
    r'&quot;',
]

# Roman numerals mapping
ROMAN_NUMERALS = [
    '', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
    'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX'
]


class IEEEFormatter:
    """Service for formatting documents according to IEEE standards."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # IEEE section display names (ALL CAPS for main sections)
        self.section_names = {
            IEEECategory.TITLE: "Title",
            IEEECategory.ABSTRACT: "Abstract",
            IEEECategory.KEYWORDS: "Index Terms",
            IEEECategory.INTRODUCTION: "INTRODUCTION",
            IEEECategory.RELATED_WORK: "RELATED WORK",
            IEEECategory.METHODOLOGY: "METHODOLOGY",
            IEEECategory.SYSTEM_DESIGN: "SYSTEM DESIGN",
            IEEECategory.IMPLEMENTATION: "IMPLEMENTATION",
            IEEECategory.RESULTS: "RESULTS AND DISCUSSION",
            IEEECategory.CONCLUSION: "CONCLUSION",
            IEEECategory.REFERENCES: "REFERENCES",
        }
        
        # Citation patterns to convert
        self.author_year_pattern = re.compile(
            r'\(([A-Z][a-z]+(?:\s+(?:et\s+al\.?|&|and)\s+[A-Z][a-z]+)?),?\s*(\d{4})\)',
            re.IGNORECASE
        )
    
    # ==================== HTML/PLACEHOLDER CLEANUP ====================
    
    def strip_html_artifacts(self, text: str) -> str:
        """Remove HTML artifacts from content."""
        if not text:
            return ""
        
        for pattern in HTML_PATTERNS:
            text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)
        
        # Clean up multiple spaces
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        return text.strip()
    
    def replace_placeholders(self, text: str, context: GlobalContext = None) -> str:
        """Replace placeholder tokens with blank or metadata values."""
        if not text:
            return ""
        
        for pattern, replacement in PLACEHOLDER_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Replace with context values if available
        if context:
            if context.authors:
                text = re.sub(r'\[Author\]', context.authors[0], text, flags=re.IGNORECASE)
            if context.project_title:
                text = re.sub(r'\[Project Title\]', context.project_title, text, flags=re.IGNORECASE)
        
        return text
    
    def clean_content(self, text: str, context: GlobalContext = None) -> str:
        """Apply all content cleaning operations."""
        text = self.strip_html_artifacts(text)
        text = self.replace_placeholders(text, context)
        return text
    
    # ==================== ABSTRACT NORMALIZATION ====================
    
    def normalize_abstract(self, sections: List[Section]) -> List[Section]:
        """
        Normalize Abstract section to IEEE format:
        - Remove "Extended Abstract" duplication
        - Enforce "Abstract— text..." format
        """
        for section in sections:
            cat = self._get_category(section)
            
            if cat == IEEECategory.ABSTRACT:
                section.title = "Abstract"
                
                content = section.rewritten_content or section.original_content
                
                # Remove "Extended Abstract" prefix
                content = re.sub(r'^Extended\s+Abstract\s*[:\-–—]?\s*', '', content, flags=re.IGNORECASE)
                content = re.sub(r'Extended\s+Abstract\s*[:\-–—]?\s*', '', content, flags=re.IGNORECASE)
                
                # Remove duplicate "Abstract" text at start
                content = re.sub(r'^Abstract\s*[:\-–—]?\s*', '', content, flags=re.IGNORECASE)
                
                # Ensure proper format: "Abstract— content"
                content = content.strip()
                if content and not content.startswith('Abstract'):
                    content = f"Abstract— {content}"
                elif content.startswith('Abstract') and '—' not in content[:15]:
                    content = re.sub(r'^Abstract\s*', 'Abstract— ', content)
                
                section.rewritten_content = content
                section.original_content = content
        
        return sections
    
    # ==================== KEYWORDS/INDEX TERMS NORMALIZATION ====================
    
    def normalize_keywords(self, sections: List[Section]) -> List[Section]:
        """
        Normalize Keywords to IEEE "Index Terms—" format.
        """
        for section in sections:
            cat = self._get_category(section)
            
            if cat == IEEECategory.KEYWORDS:
                section.title = "Index Terms"
                
                content = section.rewritten_content or section.original_content
                
                # Remove various keyword prefixes
                content = re.sub(r'^Keywords?\s*[:\-–—]+\s*', '', content, flags=re.IGNORECASE)
                content = re.sub(r'^Key\s*words?\s*[:\-–—]+\s*', '', content, flags=re.IGNORECASE)
                content = re.sub(r'^Index\s*Terms?\s*[:\-–—]+\s*', '', content, flags=re.IGNORECASE)
                content = re.sub(r'^\*?Keywords?\*?\s*[:\-–—]+\s*', '', content, flags=re.IGNORECASE)
                
                # Clean up and format
                content = content.strip()
                if content:
                    # Replace -- with em dash
                    content = content.replace('--', '—')
                    # Ensure proper format
                    if not content.startswith('Index Terms'):
                        content = 'Index Terms— ' + content.lstrip('—-: ')
                    # Ensure ends with period
                    if not content.endswith('.'):
                        content += '.'
                
                section.rewritten_content = content
                section.original_content = content
        
        return sections
    
    # ==================== HEADING NORMALIZATION ====================
    
    def normalize_heading(self, title: str, level: int = 1) -> str:
        """
        Normalize heading to IEEE style.
        - Level 1: ALL CAPS, no trailing colon
        - Level 2: ALL CAPS (subsections use A., B., C.)
        - Level 3+: Title case
        """
        # Clean the title
        title = title.strip()
        title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
        title = re.sub(r'^[\d.]+\s*', '', title)  # Remove existing numbering
        title = re.sub(r'^[IVXLCDM]+\.\s*', '', title)  # Remove Roman numerals
        title = re.sub(r'^[A-Z]\.\s*', '', title)  # Remove letter numbering
        title = re.sub(r'^Chapter\s+\d+[:\s]*', '', title, flags=re.IGNORECASE)
        title = re.sub(r':$', '', title)  # Remove trailing colon
        
        # Check normalization map
        title_lower = title.lower().strip()
        if title_lower in HEADING_NORMALIZATION:
            return HEADING_NORMALIZATION[title_lower]
        
        # Apply level-based formatting
        if level <= 2:
            return title.upper()
        else:
            return title.title()
    
    def shorten_narrative_heading(self, title: str) -> str:
        """Shorten verbose narrative headings to IEEE standard names."""
        title_lower = title.lower().strip()
        
        # Remove trailing colon
        title_lower = re.sub(r':$', '', title_lower)
        
        # Check exact match first
        if title_lower in HEADING_NORMALIZATION:
            return HEADING_NORMALIZATION[title_lower]
        
        # Check for partial matches
        for narrative, standard in HEADING_NORMALIZATION.items():
            if narrative in title_lower or title_lower in narrative:
                return standard
        
        # Check keyword-based matching
        if any(kw in title_lower for kw in ['introduction', 'intro']):
            return "INTRODUCTION"
        if any(kw in title_lower for kw in ['literature', 'related', 'prior', 'previous']):
            return "RELATED WORK"
        if any(kw in title_lower for kw in ['method', 'approach', 'materials']):
            return "METHODOLOGY"
        if any(kw in title_lower for kw in ['design', 'architecture', 'proposed system']):
            return "SYSTEM DESIGN"
        if any(kw in title_lower for kw in ['implement', 'development']):
            return "IMPLEMENTATION"
        if any(kw in title_lower for kw in ['result', 'finding', 'analysis', 'discussion', 'experiment']):
            return "RESULTS AND DISCUSSION"
        if any(kw in title_lower for kw in ['conclusion', 'summary', 'future']):
            return "CONCLUSION"
        if any(kw in title_lower for kw in ['reference', 'bibliography', 'citation']):
            return "REFERENCES"
        
        return title.upper() if title else title
    
    def normalize_all_headings(self, sections: List[Section]) -> List[Section]:
        """Normalize all section headings to IEEE style."""
        for section in sections:
            cat = self._get_category(section)
            
            # Special handling for certain categories
            if cat == IEEECategory.ABSTRACT:
                section.title = "Abstract"
            elif cat == IEEECategory.KEYWORDS:
                section.title = "Index Terms"
            elif cat == IEEECategory.REFERENCES:
                section.title = "REFERENCES"
            elif section.level == 1:
                # Apply heading normalization for main sections
                section.title = self.shorten_narrative_heading(section.title)
            elif section.level == 2:
                # Subsections: ALL CAPS
                section.title = self.normalize_heading(section.title, 2)
            else:
                section.title = self.normalize_heading(section.title, section.level)
        
        return sections
    
    # ==================== SUBSECTION PROMOTION ====================
    
    def promote_subsections(self, sections: List[Section]) -> List[Section]:
        """
        Promote certain subsections to main section level.
        Prevents wrong nesting (e.g., METHODOLOGY under INTRODUCTION).
        """
        for section in sections:
            title_lower = section.title.lower().strip()
            
            # Check if this should be promoted to main section
            for promote_term in PROMOTE_TO_MAIN:
                if promote_term in title_lower or title_lower in promote_term:
                    if section.level > 1:
                        logger.info(f"Promoting subsection '{section.title}' to main section")
                    section.level = 1
                    section.title = self.shorten_narrative_heading(section.title)
                    break
        
        return sections
    
    # ==================== DUPLICATE REMOVAL ====================
    
    def remove_duplicate_headings(self, sections: List[Section]) -> List[Section]:
        """Remove duplicate section titles and repeated heading blocks."""
        seen_titles = set()
        deduplicated = []
        
        for section in sections:
            # Normalize title for comparison
            title_normalized = re.sub(r'[^a-z\s]', '', section.title.lower()).strip()
            title_normalized = re.sub(r'\s+', ' ', title_normalized)
            
            # Skip if we've seen this exact title
            if title_normalized in seen_titles:
                # Merge content into existing section
                existing = next((s for s in deduplicated 
                               if re.sub(r'[^a-z\s]', '', s.title.lower()).strip() == title_normalized), None)
                
                if existing:
                    new_content = section.rewritten_content or section.original_content
                    existing_content = existing.rewritten_content or existing.original_content
                    
                    # Only merge if content is different and substantial
                    if new_content and len(new_content) > 50 and new_content not in existing_content:
                        existing.rewritten_content = existing_content + "\n\n" + new_content
                        existing.calculate_word_count()
                        logger.info(f"Merged duplicate section '{section.title}'")
                continue
            
            # Skip empty or very short sections
            content = section.rewritten_content or section.original_content
            if len(content.strip()) < 50:
                logger.info(f"Skipping short section '{section.title}': {len(content)} chars")
                continue
            
            seen_titles.add(title_normalized)
            deduplicated.append(section)
        
        return deduplicated
    
    # ==================== HEADING ECHO REMOVAL ====================
    
    def remove_heading_echo_from_content(self, sections: List[Section]) -> List[Section]:
        """
        Remove heading text that is echoed/repeated at the start of section content.
        Common artifact: heading is "INTRODUCTION" and content starts with
        "Introduction\nThe study presents..." — strips that first line.
        """
        for section in sections:
            content = section.rewritten_content or section.original_content
            if not content:
                continue
            
            title_lower = section.title.lower().strip()
            title_upper = section.title.upper().strip()
            
            # Split content into lines
            lines = content.split('\n')
            cleaned_lines = []
            skip_count = 0
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                stripped_lower = stripped.lower()
                
                # Only check the first few lines for echo
                if i < 3 and skip_count == i:
                    # Check if this line is just the heading repeated
                    heading_clean = re.sub(r'[^a-z\s]', '', title_lower).strip()
                    line_clean = re.sub(r'[^a-z\s]', '', stripped_lower).strip()
                    
                    if not line_clean:
                        skip_count += 1
                        continue
                    
                    # Exact or near-exact match to heading
                    if (line_clean == heading_clean or 
                        stripped_lower == title_lower or
                        stripped == title_upper or
                        # Heading with colon or dash suffix
                        re.match(rf'^{re.escape(heading_clean)}\s*[:—\-]?\s*$', line_clean)):
                        skip_count += 1
                        logger.info(f"Removed heading echo from '{section.title}': '{stripped[:60]}'")
                        continue
                
                cleaned_lines.append(line)
            
            cleaned = '\n'.join(cleaned_lines).strip()
            if cleaned != content.strip():
                section.rewritten_content = cleaned
                section.original_content = cleaned
        
        return sections
    
    # ==================== ENSURE INTRODUCTION NOT EMPTY ====================
    
    def ensure_introduction_content(self, sections: List[Section]) -> List[Section]:
        """
        Ensure INTRODUCTION is never empty.
        If classifier misplaced intro text, move it back.
        """
        intro_section = None
        first_content_section = None
        
        for section in sections:
            cat = self._get_category(section)
            
            if cat == IEEECategory.INTRODUCTION:
                intro_section = section
            elif intro_section is None and cat not in [IEEECategory.ABSTRACT, IEEECategory.KEYWORDS, IEEECategory.TITLE]:
                if first_content_section is None:
                    content = section.rewritten_content or section.original_content
                    if len(content.strip()) > 100:
                        first_content_section = section
        
        # If intro is empty but we have content elsewhere, move it
        if intro_section:
            intro_content = intro_section.rewritten_content or intro_section.original_content
            
            if len(intro_content.strip()) < 50 and first_content_section:
                # Move first content section's content to introduction
                first_content = first_content_section.rewritten_content or first_content_section.original_content
                intro_section.rewritten_content = first_content
                intro_section.calculate_word_count()
                
                # Mark first content section for removal
                first_content_section.rewritten_content = ""
                first_content_section.original_content = ""
                
                logger.info(f"Moved content from '{first_content_section.title}' to INTRODUCTION")
        
        return sections
    
    # ==================== SECTION REORDERING ====================
    
    def reorder_sections(self, sections: List[Section]) -> List[Section]:
        """Reorder sections according to IEEE structure."""
        # Group sections by category
        categorized: Dict[IEEECategory, List[Section]] = {}
        other_sections: List[Section] = []
        
        for section in sections:
            content = section.rewritten_content or section.original_content
            if len(content.strip()) < 30:
                continue  # Skip empty sections
                
            cat = self._get_category(section)
            if cat == IEEECategory.OTHER:
                other_sections.append(section)
            else:
                if cat not in categorized:
                    categorized[cat] = []
                categorized[cat].append(section)
        
        # Build ordered list
        ordered = []
        
        for category in IEEE_SECTION_ORDER:
            if category in categorized:
                ordered.extend(categorized[category])
        
        # Insert "other" sections before Conclusion
        conclusion_idx = None
        for i, section in enumerate(ordered):
            cat = self._get_category(section)
            if cat == IEEECategory.CONCLUSION:
                conclusion_idx = i
                break
        
        if conclusion_idx is not None and other_sections:
            ordered = ordered[:conclusion_idx] + other_sections + ordered[conclusion_idx:]
        else:
            refs_idx = None
            for i, section in enumerate(ordered):
                cat = self._get_category(section)
                if cat == IEEECategory.REFERENCES:
                    refs_idx = i
                    break
            
            if refs_idx is not None:
                ordered = ordered[:refs_idx] + other_sections + ordered[refs_idx:]
            else:
                ordered.extend(other_sections)
        
        return ordered
    
    # ==================== SEMANTIC DEDUPLICATION ====================
    
    def deduplicate_sections(self, sections: List[Section]) -> List[Section]:
        """Remove or merge duplicate/similar sections."""
        seen_categories = {}
        deduplicated = []
        
        for section in sections:
            cat = self._get_category(section)
            title_lower = section.title.lower().strip()
            
            # Check for duplicate categories (keep first, merge content)
            if cat != IEEECategory.OTHER and cat in seen_categories:
                existing_idx = seen_categories[cat]
                existing = deduplicated[existing_idx]
                
                content = section.rewritten_content or section.original_content
                existing_content = existing.rewritten_content or existing.original_content
                
                if not self._is_similar_content(existing_content, content):
                    merged_content = existing_content + "\n\n" + content
                    existing.rewritten_content = merged_content
                    existing.original_content = merged_content
                    existing.calculate_word_count()
                
                continue
            
            # Check for similar titles
            is_duplicate = False
            for idx, existing in enumerate(deduplicated):
                if self._is_similar_title(title_lower, existing.title.lower()):
                    content = section.rewritten_content or section.original_content
                    existing_content = existing.rewritten_content or existing.original_content
                    
                    if not self._is_similar_content(existing_content, content):
                        merged = existing_content + "\n\n" + content
                        existing.rewritten_content = merged
                        existing.calculate_word_count()
                    
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                if cat != IEEECategory.OTHER:
                    seen_categories[cat] = len(deduplicated)
                deduplicated.append(section)
        
        return deduplicated
    
    def _is_similar_title(self, title1: str, title2: str) -> bool:
        """Check if two titles are semantically similar."""
        t1 = re.sub(r'[^a-z\s]', '', title1.lower())
        t2 = re.sub(r'[^a-z\s]', '', title2.lower())
        
        if t1 == t2:
            return True
        if t1 in t2 or t2 in t1:
            return True
        
        words1 = set(t1.split())
        words2 = set(t2.split())
        
        if len(words1) > 0 and len(words2) > 0:
            overlap = len(words1 & words2) / max(len(words1), len(words2))
            if overlap > 0.7:
                return True
        
        return False
    
    def _is_similar_content(self, content1: str, content2: str) -> bool:
        """Check if content is too similar."""
        c1 = re.sub(r'\s+', '', content1[:200].lower())
        c2 = re.sub(r'\s+', '', content2[:200].lower())
        
        return c1 == c2 or c1 in c2 or c2 in c1
    
    # ==================== MERGE OBJECTIVES INTO INTRODUCTION ====================
    
    def merge_objectives_into_intro(self, sections: List[Section]) -> List[Section]:
        """Move Objectives/Aim sections into Introduction."""
        intro_section = None
        sections_to_merge = []
        remaining_sections = []
        
        for section in sections:
            title_lower = section.title.lower().strip()
            cat = self._get_category(section)
            
            if cat == IEEECategory.INTRODUCTION:
                intro_section = section
                remaining_sections.append(section)
                continue
            
            should_merge = any(term in title_lower for term in MERGE_INTO_INTRO)
            
            if should_merge:
                sections_to_merge.append(section)
            else:
                remaining_sections.append(section)
        
        if intro_section and sections_to_merge:
            intro_content = intro_section.rewritten_content or intro_section.original_content
            
            for merge_section in sections_to_merge:
                merge_content = merge_section.rewritten_content or merge_section.original_content
                intro_content += f"\n\n**{merge_section.title}**\n\n{merge_content}"
            
            intro_section.rewritten_content = intro_content
            intro_section.calculate_word_count()
        
        return remaining_sections
    
    # ==================== REMOVE NON-PAPER SECTIONS ====================
    
    def remove_non_paper_sections(self, sections: List[Section]) -> List[Section]:
        """Remove sections that are not part of the actual paper."""
        filtered = []
        
        for section in sections:
            title_lower = section.title.lower().strip()
            content_lower = (section.original_content or "").lower()[:200]
            
            is_non_paper = any(term in title_lower or term in content_lower 
                              for term in NON_PAPER_SECTIONS)
            
            if not is_non_paper:
                filtered.append(section)
            else:
                logger.info(f"Removed non-paper section: {section.title}")
        
        return filtered
    
    # ==================== REFERENCE FORMATTING ====================
    
    def format_references_ieee(self, references_content: str, citation_map: Dict[str, int] = None) -> str:
        """
        Format reference list in IEEE numbered format.
        Split merged references into separate numbered entries.
        Handles: numbered refs, blank-line separated refs, period-based merges,
        and semicolon-separated refs.
        """
        # Step 1: Pre-split merged references that are on a single line
        # Detect patterns like "Author1 (2020). Title1. Journal. Author2 (2021). Title2."
        raw_text = references_content.strip()
        
        # Split on semicolons that separate distinct references
        raw_text = re.sub(r';\s*(?=[A-Z][a-z]+[,\s])', '\n', raw_text)
        
        lines = raw_text.split('\n')
        formatted_refs = []
        ref_num = 1
        current_ref = []
        
        for line in lines:
            line = line.strip()
            if not line:
                # End of a reference
                if current_ref:
                    ref_text = ' '.join(current_ref)
                    ref_text = re.sub(r'^[\[\(]?\d+[\]\)]?\s*\.?\s*', '', ref_text)
                    if ref_text.strip():
                        formatted_refs.append(f"[{ref_num}] {ref_text.strip()}")
                        ref_num += 1
                    current_ref = []
                continue
            
            # Check if this line starts a new reference (numbered)
            if re.match(r'^[\[\(]?\d+[\]\)]?\s*\.?\s+', line):
                # Save previous reference
                if current_ref:
                    ref_text = ' '.join(current_ref)
                    ref_text = re.sub(r'^[\[\(]?\d+[\]\)]?\s*\.?\s*', '', ref_text)
                    if ref_text.strip():
                        formatted_refs.append(f"[{ref_num}] {ref_text.strip()}")
                        ref_num += 1
                current_ref = [re.sub(r'^[\[\(]?\d+[\]\)]?\s*\.?\s*', '', line)]
            else:
                current_ref.append(line)
        
        # Don't forget the last reference
        if current_ref:
            ref_text = ' '.join(current_ref)
            ref_text = re.sub(r'^[\[\(]?\d+[\]\)]?\s*\.?\s*', '', ref_text)
            if ref_text.strip():
                formatted_refs.append(f"[{ref_num}] {ref_text.strip()}")
        
        # Step 2: If we only got a single giant block, try period-based splitting
        if len(formatted_refs) <= 1 and len(raw_text) > 200:
            # Try splitting on author-year boundaries: ". Author" patterns
            parts = re.split(r'(?<=\.)\s+(?=[A-Z][a-z]+[,\s])', raw_text)
            if len(parts) > 1:
                formatted_refs = []
                ref_num = 1
                for part in parts:
                    part = part.strip()
                    part = re.sub(r'^[\[\(]?\d+[\]\)]?\s*\.?\s*', '', part)
                    if part and len(part) > 10:
                        formatted_refs.append(f"[{ref_num}] {part}")
                        ref_num += 1
        
        return '\n'.join(formatted_refs)
    
    def convert_citations_to_ieee(self, sections: List[Section]) -> Tuple[List[Section], Dict[str, int]]:
        """Convert author-year citations to IEEE numeric style [n]."""
        citation_map = {}
        citation_counter = 1
        
        for section in sections:
            cat = self._get_category(section)
            
            if cat == IEEECategory.REFERENCES:
                continue
            
            content = section.rewritten_content or section.original_content
            
            def replace_citation(match):
                nonlocal citation_counter
                author = match.group(1)
                year = match.group(2)
                key = f"{author}_{year}"
                
                if key not in citation_map:
                    citation_map[key] = citation_counter
                    citation_counter += 1
                
                return f"[{citation_map[key]}]"
            
            converted_content = self.author_year_pattern.sub(replace_citation, content)
            
            # Also handle (Author et al., 2020) format
            et_al_pattern = re.compile(r'\(([A-Z][a-z]+)\s+et\s+al\.?,?\s*(\d{4})\)', re.IGNORECASE)
            converted_content = et_al_pattern.sub(replace_citation, converted_content)
            
            section.rewritten_content = converted_content
        
        return sections, citation_map
    
    # ==================== IEEE NUMBERING ====================
    
    def apply_ieee_numbering(self, sections: List[Section]) -> List[Section]:
        """
        Apply IEEE-style numbering:
        - Main sections: I., II., III. (Roman numerals)
        - Subsections: A., B., C.
        - Sub-subsections: 1), 2), 3)
        """
        main_counter = 0
        sub_counter = 0
        subsub_counter = 0
        
        for section in sections:
            cat = self._get_category(section)
            
            # Skip numbering for special sections
            if cat in [IEEECategory.ABSTRACT, IEEECategory.KEYWORDS, 
                      IEEECategory.TITLE, IEEECategory.REFERENCES]:
                section.ieee_number = ""
                continue
            
            level = section.level
            
            if level == 1:
                main_counter += 1
                sub_counter = 0
                subsub_counter = 0
                
                if main_counter <= 20:
                    section.ieee_number = f"{ROMAN_NUMERALS[main_counter]}."
                else:
                    section.ieee_number = f"{main_counter}."
                
                # Ensure title is ALL CAPS
                section.title = section.title.upper()
                    
            elif level == 2:
                sub_counter += 1
                subsub_counter = 0
                
                # Letters for subsections
                section.ieee_number = f"{chr(64 + sub_counter)}."
                section.title = section.title.upper()  # Subsections also ALL CAPS
                
            elif level >= 3:
                subsub_counter += 1
                section.ieee_number = f"{subsub_counter})"
        
        return sections
    
    # ==================== IEEE COMPLIANCE VALIDATION ====================
    
    def validate_ieee_compliance(self, sections: List[Section]) -> Dict:
        """
        Final IEEE validation pass before export.
        Checks: numbering hierarchy, empty sections, duplicates, reference format, word limits.
        """
        report = {
            "is_compliant": True,
            "errors": [],
            "warnings": [],
            "checks": {},
            "stats": {}
        }
        
        existing_categories = set()
        for section in sections:
            cat = self._get_category(section)
            existing_categories.add(cat)
        
        # Check 1: Required sections
        required = [IEEECategory.ABSTRACT, IEEECategory.INTRODUCTION, IEEECategory.CONCLUSION]
        for req in required:
            if req not in existing_categories:
                report["errors"].append(f"Missing required section: {self.section_names.get(req, str(req))}")
                report["is_compliant"] = False
        
        # Check 2: Roman numeral numbering for main sections
        main_sections_valid = True
        for section in sections:
            cat = self._get_category(section)
            if section.level == 1 and cat not in [IEEECategory.ABSTRACT, IEEECategory.KEYWORDS, 
                                                    IEEECategory.REFERENCES, IEEECategory.TITLE]:
                if not section.ieee_number:
                    main_sections_valid = False
                    report["warnings"].append(f"Section '{section.title}' missing numbering")
                elif not any(r + '.' == section.ieee_number for r in ROMAN_NUMERALS[1:21]):
                    main_sections_valid = False
                    report["warnings"].append(f"Section '{section.title}' has non-Roman numbering")
        
        report["checks"]["roman_numeral_numbering"] = main_sections_valid
        
        # Check 3: Empty sections
        empty_sections = []
        for section in sections:
            content = section.rewritten_content or section.original_content
            cat = self._get_category(section)
            
            if len(content.strip()) < 50 and cat not in [IEEECategory.KEYWORDS]:
                empty_sections.append(section.title)
        
        if empty_sections:
            report["warnings"].append(f"Near-empty sections: {', '.join(empty_sections)}")
        report["checks"]["no_empty_sections"] = len(empty_sections) == 0
        
        # Check 4: Duplicate headings
        titles_seen = set()
        duplicates = []
        for section in sections:
            title_norm = section.title.lower().strip()
            if title_norm in titles_seen:
                duplicates.append(section.title)
            titles_seen.add(title_norm)
        
        if duplicates:
            report["warnings"].append(f"Duplicate headings: {', '.join(duplicates)}")
        report["checks"]["no_duplicates"] = len(duplicates) == 0
        
        # Check 5: Reference numbering
        has_references = IEEECategory.REFERENCES in existing_categories
        if has_references:
            for section in sections:
                cat = self._get_category(section)
                if cat == IEEECategory.REFERENCES:
                    content = section.rewritten_content or section.original_content
                    # Check for [1], [2] format
                    if not re.search(r'\[\d+\]', content):
                        report["warnings"].append("References may not be in IEEE [n] format")
        else:
            report["warnings"].append("No References section found")
        
        report["checks"]["has_references"] = has_references
        
        # Check 6: Section word limits (thresholds match config: 180/450)
        total_words = 0
        sections_under = 0
        sections_over = 0
        min_words = self.settings.min_section_words  # 180
        max_words = self.settings.max_section_words  # 450
        
        for section in sections:
            word_count = section.word_count or len((section.rewritten_content or section.original_content).split())
            total_words += word_count
            cat = self._get_category(section)
            
            if cat not in [IEEECategory.KEYWORDS, IEEECategory.REFERENCES, IEEECategory.TITLE, IEEECategory.ABSTRACT]:
                if word_count < min_words:
                    sections_under += 1
                elif word_count > max_words:
                    sections_over += 1
        
        report["stats"]["total_words"] = total_words
        report["stats"]["section_count"] = len(sections)
        report["stats"]["sections_under_min"] = sections_under
        report["stats"]["sections_over_max"] = sections_over
        
        # Check 7: Uppercase main headings
        uppercase_valid = True
        for section in sections:
            if section.level == 1:
                cat = self._get_category(section)
                if cat not in [IEEECategory.ABSTRACT, IEEECategory.KEYWORDS]:
                    if section.title != section.title.upper():
                        uppercase_valid = False
                        report["warnings"].append(f"Section '{section.title}' should be ALL CAPS")
        
        report["checks"]["uppercase_headings"] = uppercase_valid
        
        return report
    
    # ==================== FULL FORMATTING PIPELINE ====================
    
    def format_document(
        self,
        sections: List[Section],
        context: GlobalContext,
    ) -> Tuple[List[Section], Dict]:
        """
        Apply full IEEE formatting pipeline.
        
        Pipeline Order:
        1. Clean content (HTML, placeholders)
        2. Remove non-paper sections
        3. Promote subsections (prevent wrong nesting)
        4. Merge objectives into introduction
        5. Deduplicate sections
        6. Remove duplicate headings
        7. Ensure introduction has content
        8. Ensure required sections
        9. Reorder sections
        10. Normalize headings
        11. Normalize Abstract
        12. Normalize Keywords/Index Terms
        13. Convert citations
        14. Format references
        15. Apply IEEE numbering
        16. Final validation
        """
        logger.info("Starting IEEE formatting pipeline...")
        
        # Step 1: Clean content
        for section in sections:
            content = section.rewritten_content or section.original_content
            content = self.clean_content(content, context)
            section.rewritten_content = content
            section.original_content = content
        
        # Step 2: Remove non-paper sections
        sections = self.remove_non_paper_sections(sections)
        
        # Step 3: Promote subsections (prevent METHODOLOGY under INTRODUCTION)
        sections = self.promote_subsections(sections)
        
        # Step 4: Merge objectives into introduction
        sections = self.merge_objectives_into_intro(sections)
        
        # Step 5: Semantic deduplication
        sections = self.deduplicate_sections(sections)
        
        # Step 6: Remove duplicate headings
        sections = self.remove_duplicate_headings(sections)
        
        # Step 7: Ensure introduction has content
        sections = self.ensure_introduction_content(sections)
        
        # Step 8: Ensure required sections
        sections = self.ensure_required_sections(sections, context)
        
        # Step 9: Reorder sections
        sections = self.reorder_sections(sections)
        
        # Step 10: Normalize headings
        sections = self.normalize_all_headings(sections)
        
        # Step 11: Normalize Abstract
        sections = self.normalize_abstract(sections)
        
        # Step 12: Normalize Keywords to Index Terms
        sections = self.normalize_keywords(sections)
        
        # Step 13: Convert citations
        sections, citation_map = self.convert_citations_to_ieee(sections)
        
        # Step 14: Format references
        for section in sections:
            cat = self._get_category(section)
            if cat == IEEECategory.REFERENCES:
                content = section.rewritten_content or section.original_content
                section.rewritten_content = self.format_references_ieee(content, citation_map)
                section.original_content = section.rewritten_content
        
        # Step 15: Remove heading echoes from content body
        sections = self.remove_heading_echo_from_content(sections)
        
        # Step 16: Final content cleaning pass (catch leftover HTML/placeholders)
        for section in sections:
            content = section.rewritten_content or section.original_content
            content = self.clean_content(content, context)
            section.rewritten_content = content
            section.original_content = content
        
        # Step 17: Apply IEEE numbering
        sections = self.apply_ieee_numbering(sections)
        
        # Step 18: Final validation
        validation_report = self.validate_ieee_compliance(sections)
        
        logger.info(f"IEEE formatting complete. Compliant: {validation_report['is_compliant']}")
        
        return sections, validation_report
    
    # ==================== HELPER METHODS ====================
    
    def _get_category(self, section: Section) -> IEEECategory:
        """Get section category as IEEECategory enum."""
        if isinstance(section.category, str):
            return IEEECategory(section.category)
        return section.category
    
    def ensure_required_sections(
        self,
        sections: List[Section],
        context: GlobalContext,
    ) -> List[Section]:
        """Ensure all required IEEE sections are present."""
        existing_categories = {self._get_category(s) for s in sections}
        
        required = [IEEECategory.ABSTRACT, IEEECategory.INTRODUCTION, IEEECategory.CONCLUSION]
        
        for cat in required:
            if cat not in existing_categories:
                placeholder = Section(
                    title=self.section_names.get(cat, str(cat)),
                    original_content=f"[{self.section_names.get(cat, str(cat))} content to be added]",
                    category=cat,
                    level=1,
                )
                sections.append(placeholder)
        
        if context.keywords and IEEECategory.KEYWORDS not in existing_categories:
            keywords_text = "Index Terms— " + ", ".join(context.keywords) + "."
            keywords_section = Section(
                title="Index Terms",
                original_content=keywords_text,
                rewritten_content=keywords_text,
                category=IEEECategory.KEYWORDS,
                level=1,
                is_processed=True,
            )
            sections.append(keywords_section)
        
        return sections
    
    # ==================== SECTION STATISTICS ====================
    
    def calculate_section_stats(self, sections: List[Section]) -> Dict:
        """
        Calculate statistics for sections.
        
        Args:
            sections: List of sections
            
        Returns:
            Dictionary with stats: total_sections, total_words, sections_in_range
        """
        if not sections:
            return {
                "total_sections": 0,
                "total_words": 0,
                "sections_in_range": 0,
                "sections_under": 0,
                "sections_over": 0,
            }
        
        total_sections = len(sections)
        total_words = 0
        sections_in_range = 0
        sections_under = 0
        sections_over = 0
        
        min_words = self.settings.min_section_words
        max_words = self.settings.max_section_words
        
        for section in sections:
            # Calculate word count
            content = section.rewritten_content or section.original_content or ""
            word_count = section.word_count or len(content.split())
            total_words += word_count
            
            # Check if in range
            cat = self._get_category(section)
            
            # Skip special sections for range calculation
            if cat in [IEEECategory.KEYWORDS, IEEECategory.REFERENCES, IEEECategory.TITLE]:
                sections_in_range += 1
                continue
            
            if word_count < min_words:
                sections_under += 1
            elif word_count > max_words:
                sections_over += 1
            else:
                sections_in_range += 1
        
        return {
            "total_sections": total_sections,
            "total_words": total_words,
            "sections_in_range": sections_in_range,
            "sections_under": sections_under,
            "sections_over": sections_over,
        }
