"""
Utility functions for IEEE Report Restructurer.
"""

import re
from typing import List


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def truncate_text(text: str, max_chars: int = 500) -> str:
    """Truncate text to maximum characters."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs."""
    paragraphs = text.split('\n\n')
    return [p.strip() for p in paragraphs if p.strip()]


def roman_to_int(roman: str) -> int:
    """Convert Roman numeral to integer."""
    roman_values = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50,
        'C': 100, 'D': 500, 'M': 1000
    }
    result = 0
    prev_value = 0
    
    for char in reversed(roman.upper()):
        value = roman_values.get(char, 0)
        if value < prev_value:
            result -= value
        else:
            result += value
        prev_value = value
    
    return result


def int_to_roman(num: int) -> str:
    """Convert integer to Roman numeral."""
    if num <= 0:
        return ""
    
    values = [
        (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
        (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
        (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')
    ]
    
    result = ""
    for value, numeral in values:
        while num >= value:
            result += numeral
            num -= value
    
    return result


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system use."""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename


def estimate_reading_time(word_count: int) -> int:
    """Estimate reading time in minutes (average 200 words/min)."""
    return max(1, round(word_count / 200))


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
