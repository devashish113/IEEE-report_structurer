"""
Section model for IEEE Report Restructurer.
Represents individual sections of the document.
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class IEEECategory(str, Enum):
    """IEEE standard section categories."""
    TITLE = "title"
    ABSTRACT = "abstract"
    KEYWORDS = "keywords"
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHODOLOGY = "methodology"
    SYSTEM_DESIGN = "system_design"
    IMPLEMENTATION = "implementation"
    RESULTS = "results"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    OTHER = "other"


# IEEE section order for restructuring
IEEE_SECTION_ORDER = [
    IEEECategory.TITLE,
    IEEECategory.ABSTRACT,
    IEEECategory.KEYWORDS,
    IEEECategory.INTRODUCTION,
    IEEECategory.RELATED_WORK,
    IEEECategory.METHODOLOGY,
    IEEECategory.SYSTEM_DESIGN,
    IEEECategory.IMPLEMENTATION,
    IEEECategory.RESULTS,
    IEEECategory.CONCLUSION,
    IEEECategory.REFERENCES,
]


class Section(BaseModel):
    """Represents a section of the document."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    original_content: str
    rewritten_content: Optional[str] = None
    category: IEEECategory = IEEECategory.OTHER
    ieee_number: Optional[str] = None  # e.g., "I", "II", "A", "1"
    word_count: int = 0
    is_processed: bool = False
    subsections: List["Section"] = []
    level: int = 1  # 1 = main section, 2 = subsection, 3 = sub-subsection
    
    def calculate_word_count(self) -> int:
        """Calculate word count of rewritten or original content."""
        content = self.rewritten_content or self.original_content
        self.word_count = len(content.split())
        return self.word_count
    
    def get_content(self) -> str:
        """Get the current content (rewritten if available, else original)."""
        return self.rewritten_content or self.original_content
    
    class Config:
        use_enum_values = True


# Category mapping for section detection
CATEGORY_KEYWORDS = {
    IEEECategory.ABSTRACT: ["abstract", "summary", "overview"],
    IEEECategory.KEYWORDS: ["keywords", "key words", "index terms"],
    IEEECategory.INTRODUCTION: ["introduction", "background", "motivation"],
    IEEECategory.RELATED_WORK: ["related work", "literature review", "previous work", "state of the art"],
    IEEECategory.METHODOLOGY: ["methodology", "method", "approach", "proposed method", "proposed approach"],
    IEEECategory.SYSTEM_DESIGN: ["system design", "architecture", "design", "framework", "proposed system"],
    IEEECategory.IMPLEMENTATION: ["implementation", "development", "prototype", "experimental setup"],
    IEEECategory.RESULTS: ["results", "experiments", "evaluation", "findings", "analysis", "discussion"],
    IEEECategory.CONCLUSION: ["conclusion", "conclusions", "future work", "summary and conclusion"],
    IEEECategory.REFERENCES: ["references", "bibliography", "citations"],
}
