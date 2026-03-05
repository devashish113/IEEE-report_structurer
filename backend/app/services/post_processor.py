"""
Post-Processing Module for IEEE Report Restructurer.
Runs after the formatter pipeline and before export to catch remaining artifacts.
Handles: heading-echo removal, final content cleaning, and section word count logging.
"""

import re
import logging
from typing import List, Dict

from ..models.section import Section, IEEECategory
from ..config import get_settings

logger = logging.getLogger(__name__)

# HTML artifacts to strip (final pass)
FINAL_HTML_PATTERNS = [
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
    r'</?h[1-6][^>]*>',
    r'</?table[^>]*>',
    r'</?tr[^>]*>',
    r'</?td[^>]*>',
    r'</?th[^>]*>',
    r'</?ul[^>]*>',
    r'</?ol[^>]*>',
    r'</?li[^>]*>',
    r'</?a[^>]*>',
    r'&nbsp;',
    r'&amp;',
    r'&lt;',
    r'&gt;',
    r'&quot;',
    r'&#\d+;',
]

# Placeholder patterns to strip (final pass)
FINAL_PLACEHOLDER_PATTERNS = [
    r'\[Your Name\]',
    r'\[Author Name\]',
    r'\[Name\]',
    r'\[Date\]',
    r'\[Title\]',
    r'\[Institution\]',
    r'\[University\]',
    r'\[College Name\]',
    r'\[Department\]',
    r'\[Email\]',
    r'\[Phone\]',
    r'\[Address\]',
    r'\[Insert .+?\]',
    r'\[TODO.*?\]',
    r'\[TBD.*?\]',
    r'\[PLACEHOLDER.*?\]',
    r'\[Your .+?\]',
    r'<Your Name>',
    r'<Author>',
    r'<College Name>',
    r'<University>',
    r'<Department>',
]


class PostProcessor:
    """Post-processing module that runs after IEEE formatting and before export."""

    def __init__(self):
        self.settings = get_settings()

    def _get_category_value(self, section: Section) -> str:
        """Get category as string value."""
        if isinstance(section.category, str):
            return section.category
        return section.category.value

    # ==================== HEADING ECHO REMOVAL ====================

    def remove_heading_echoes(self, sections: List[Section]) -> List[Section]:
        """
        Remove heading text that is duplicated at the start of section content.
        Catches patterns like:
          Heading: "INTRODUCTION"
          Content: "Introduction\nThe study presents..."
        """
        for section in sections:
            content = section.rewritten_content or section.original_content
            if not content:
                continue

            title_lower = section.title.lower().strip()
            lines = content.split('\n')
            cleaned_lines = []
            removed_any = False

            for i, line in enumerate(lines):
                stripped = line.strip()
                stripped_lower = stripped.lower()

                # Only check the first 3 lines for echoes
                if i < 3 and not removed_any:
                    if not stripped:
                        continue  # skip blank lines at start

                    # Normalize for comparison
                    heading_clean = re.sub(r'[^a-z\s]', '', title_lower).strip()
                    line_clean = re.sub(r'[^a-z\s]', '', stripped_lower).strip()

                    # Check for match
                    if (line_clean == heading_clean or
                        stripped_lower == title_lower or
                        stripped == section.title.upper().strip()):
                        logger.info(f"PostProcessor: removed heading echo '{stripped[:50]}' from '{section.title}'")
                        removed_any = True
                        continue

                cleaned_lines.append(line)

            if removed_any:
                cleaned = '\n'.join(cleaned_lines).strip()
                section.rewritten_content = cleaned
                section.original_content = cleaned

        return sections

    # ==================== FINAL CONTENT CLEANING ====================

    def final_content_clean(self, sections: List[Section]) -> List[Section]:
        """
        Final cleaning pass to catch any leftover HTML tags, placeholders,
        or markup artifacts that survived earlier pipeline stages.
        """
        for section in sections:
            content = section.rewritten_content or section.original_content
            if not content:
                continue

            original = content

            # Strip leftover HTML
            for pattern in FINAL_HTML_PATTERNS:
                content = re.sub(pattern, ' ', content, flags=re.IGNORECASE)

            # Strip leftover placeholders
            for pattern in FINAL_PLACEHOLDER_PATTERNS:
                content = re.sub(pattern, '', content, flags=re.IGNORECASE)

            # Clean up markdown bold/italic artifacts that shouldn't be in IEEE output
            # But preserve ** around subsection headings within content
            content = re.sub(r'\*{3,}', '', content)  # *** or more

            # Clean up multiple spaces and excessive blank lines
            content = re.sub(r'[ \t]+', ' ', content)
            content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
            content = content.strip()

            if content != original:
                section.rewritten_content = content
                section.original_content = content
                logger.info(f"PostProcessor: cleaned content in '{section.title}'")

        return sections

    # ==================== SECTION WORD COUNT LOGGING ====================

    def log_section_word_counts(self, sections: List[Section]) -> List[Dict]:
        """
        Log per-section word counts: original word count, final word count.
        Returns the log entries for inclusion in processing results.
        """
        settings = self.settings
        word_count_log = []

        logger.info("=== Final Section Word Count Report ===")

        for section in sections:
            content = section.rewritten_content or section.original_content or ""
            word_count = len(content.split())
            section.word_count = word_count

            cat_value = self._get_category_value(section)

            # Determine status
            skip_cats = [IEEECategory.ABSTRACT.value, IEEECategory.KEYWORDS.value,
                         IEEECategory.REFERENCES.value, IEEECategory.TITLE.value]

            if cat_value in skip_cats:
                status = "exempt"
            elif word_count < settings.min_section_words:
                status = "UNDER_MIN"
            elif word_count > settings.max_section_words:
                status = "OVER_MAX"
            else:
                status = "OK"

            entry = {
                "section": section.title,
                "ieee_number": section.ieee_number or "",
                "word_count": word_count,
                "status": status,
                "target": settings.target_section_words,
            }
            word_count_log.append(entry)

            logger.info(
                f"  {entry['ieee_number']} {entry['section']}: "
                f"{word_count} words [{status}]"
            )

        logger.info("=======================================")

        return word_count_log

    # ==================== ORCHESTRATOR ====================

    def run_post_processing(self, sections: List[Section]) -> tuple:
        """
        Run all post-processing steps in order.

        Returns:
            Tuple of (processed_sections, word_count_log)
        """
        logger.info("Starting post-processing pipeline...")

        # Step 1: Remove heading echoes
        sections = self.remove_heading_echoes(sections)

        # Step 2: Final content cleaning
        sections = self.final_content_clean(sections)

        # Step 3: Log word counts
        word_count_log = self.log_section_word_counts(sections)

        logger.info("Post-processing complete.")

        return sections, word_count_log
