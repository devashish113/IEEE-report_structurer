"""
LLM Service for IEEE Report Restructurer.
Handles all interactions with the Groq API for text generation.
"""

import asyncio
import json
import logging
import os
import re
from typing import Optional, List

from groq import AsyncGroq

from ..config import get_settings
from ..models.section import Section, IEEECategory
from ..models.document import GlobalContext

logger = logging.getLogger(__name__)
from ..prompts.templates import (
    SECTION_REWRITE_PROMPT,
    SECTION_EXPAND_PROMPT,
    SECTION_COMPRESS_PROMPT,
    REFERENCE_FORMAT_PROMPT,
    SECTION_CLASSIFICATION_PROMPT,
    HEADING_INFERENCE_PROMPT,
    ABSTRACT_GENERATION_PROMPT,
)

# Titles to skip rewriting (pass through unchanged)
SKIP_REWRITE_TITLES = [
    "references",
    "bibliography",
    "appendix",
    "code",
    "logs",
    "abstract",
    "index terms",
]

# LLM timeout in seconds
LLM_TIMEOUT = 60

# Max retries for LLM calls
MAX_LLM_RETRIES = 2

# Chunk size for splitting large sections
CHUNK_MIN_WORDS = 400
CHUNK_MAX_WORDS = 600
LARGE_SECTION_THRESHOLD = 1200


class LLMService:
    """Service for LLM-based text generation using Groq API."""
    
    def __init__(self):
        self.settings = get_settings()
        # Initialize client once - do NOT recreate on each request
        self._client: Optional[AsyncGroq] = None
        self._semaphore = asyncio.Semaphore(self.settings.max_concurrent_llm_calls)
    
    @property
    def client(self) -> AsyncGroq:
        """Lazy initialization of AsyncGroq client with minimal setup."""
        if self._client is None:
            # Official minimal setup - only api_key, no proxies/transport/custom httpx
            self._client = AsyncGroq(
                api_key=self.settings.groq_api_key
            )
        return self._client
    
    def _should_skip_rewrite(self, title: str) -> bool:
        """Check if section title indicates it should skip rewriting."""
        title_lower = title.lower().strip()
        for skip_term in SKIP_REWRITE_TITLES:
            if skip_term in title_lower:
                return True
        return False
    
    def _split_into_chunks(self, text: str) -> List[str]:
        """
        Split large text into chunks of 400-600 words.
        Tries to split on paragraph boundaries.
        """
        words = text.split()
        total_words = len(words)
        
        if total_words <= LARGE_SECTION_THRESHOLD:
            return [text]
        
        chunks = []
        paragraphs = text.split('\n\n')
        
        current_chunk = []
        current_word_count = 0
        
        for para in paragraphs:
            para_words = len(para.split())
            
            # If adding this paragraph exceeds max, save current chunk
            if current_word_count + para_words > CHUNK_MAX_WORDS and current_word_count >= CHUNK_MIN_WORDS:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_word_count = para_words
            else:
                current_chunk.append(para)
                current_word_count += para_words
        
        # Add remaining content
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        # If paragraph splitting didn't work well, fall back to word-based splitting
        if len(chunks) == 1 and total_words > LARGE_SECTION_THRESHOLD:
            chunks = []
            chunk_size = 500  # Target middle of 400-600 range
            for i in range(0, total_words, chunk_size):
                chunk_words = words[i:i + chunk_size]
                chunks.append(' '.join(chunk_words))
        
        return chunks
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        """
        Generate text using Groq API with retry logic and timeout.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        async with self._semaphore:
            last_error = None
            for attempt in range(MAX_LLM_RETRIES):
                try:
                    # Official Groq API call pattern with timeout
                    response = await asyncio.wait_for(
                        self.client.chat.completions.create(
                            model=self.settings.groq_model,
                            messages=[
                                {
                                    "role": "system",
                                    "content": "You are an expert academic writer specializing in IEEE-format technical papers. Always provide clear, formal, and technically accurate content."
                                },
                                {"role": "user", "content": prompt}
                            ],
                            temperature=temperature,
                            max_tokens=max_tokens,
                        ),
                        timeout=LLM_TIMEOUT
                    )
                    return response.choices[0].message.content.strip()
                    
                except asyncio.TimeoutError:
                    last_error = f"LLM call timed out after {LLM_TIMEOUT} seconds"
                    if attempt < MAX_LLM_RETRIES - 1:
                        await asyncio.sleep(1)
                except Exception as e:
                    last_error = e
                    if attempt < MAX_LLM_RETRIES - 1:
                        delay = self.settings.retry_delay_seconds * (2 ** attempt)
                        await asyncio.sleep(delay)
            
            raise RuntimeError(f"LLM generation failed after {MAX_LLM_RETRIES} attempts: {last_error}")
    
    async def test_connection(self) -> str:
        """Test LLM connection with a simple prompt."""
        response = await asyncio.wait_for(
            self.client.chat.completions.create(
                model=self.settings.groq_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'LLM connection successful!' in exactly those words."}
                ],
                temperature=0.1,
                max_tokens=50,
            ),
            timeout=LLM_TIMEOUT
        )
        return response.choices[0].message.content.strip()
    
    async def rewrite_section(
        self,
        section: Section,
        context: GlobalContext,
        target_words: int = 300,
    ) -> str:
        """
        Rewrite a section in formal academic tone.
        Handles large sections by chunking.
        
        Args:
            section: The section to rewrite
            context: Global document context
            target_words: Target word count
            
        Returns:
            Rewritten content
        """
        content = section.original_content
        word_count = len(content.split())
        
        # If section is large, split and rewrite chunks separately
        if word_count > LARGE_SECTION_THRESHOLD:
            chunks = self._split_into_chunks(content)
            rewritten_chunks = []
            
            for i, chunk in enumerate(chunks):
                chunk_target = target_words // len(chunks) if len(chunks) > 1 else target_words
                chunk_target = max(chunk_target, 200)  # Minimum 200 words per chunk
                
                prompt = SECTION_REWRITE_PROMPT.format(
                    project_title=context.project_title,
                    domain=context.domain,
                    objective=context.objective,
                    section_title=f"{section.title} (Part {i+1}/{len(chunks)})",
                    section_content=chunk,
                    target_words=chunk_target,
                )
                
                rewritten_chunk = await self.generate(prompt, max_tokens=1500)
                rewritten_chunks.append(rewritten_chunk)
            
            # Merge rewritten chunks
            return "\n\n".join(rewritten_chunks)
        
        # Standard rewrite for normal-sized sections
        prompt = SECTION_REWRITE_PROMPT.format(
            project_title=context.project_title,
            domain=context.domain,
            objective=context.objective,
            section_title=section.title,
            section_content=section.original_content,
            target_words=target_words,
        )
        
        return await self.generate(prompt, max_tokens=1500)
    
    async def expand_section(
        self,
        section: Section,
        context: GlobalContext,
        target_words: int = 300,
    ) -> str:
        """
        Expand a section to meet minimum word count.
        
        Args:
            section: The section to expand
            context: Global document context
            target_words: Target word count
            
        Returns:
            Expanded content
        """
        current_content = section.rewritten_content or section.original_content
        current_words = len(current_content.split())
        
        prompt = SECTION_EXPAND_PROMPT.format(
            project_title=context.project_title,
            domain=context.domain,
            objective=context.objective,
            section_title=section.title,
            section_content=current_content,
            current_words=current_words,
            target_words=target_words,
        )
        
        return await self.generate(prompt, max_tokens=1500)
    
    async def compress_section(
        self,
        section: Section,
        context: GlobalContext,
        target_words: int = 350,
    ) -> str:
        """
        Compress a section to meet maximum word count.
        
        Args:
            section: The section to compress
            context: Global document context
            target_words: Target word count
            
        Returns:
            Compressed content
        """
        current_content = section.rewritten_content or section.original_content
        current_words = len(current_content.split())
        
        prompt = SECTION_COMPRESS_PROMPT.format(
            project_title=context.project_title,
            domain=context.domain,
            objective=context.objective,
            section_title=section.title,
            section_content=current_content,
            current_words=current_words,
            target_words=target_words,
        )
        
        return await self.generate(prompt, max_tokens=1500)
    
    async def format_references(self, references: List[str]) -> str:
        """
        Format references in IEEE style.
        
        Args:
            references: List of reference strings
            
        Returns:
            Formatted references
        """
        prompt = REFERENCE_FORMAT_PROMPT.format(
            references="\n".join(references)
        )
        
        return await self.generate(prompt, max_tokens=2000)
    
    async def classify_section(self, title: str, content: str) -> IEEECategory:
        """
        Classify a section into an IEEE category using LLM.
        
        Args:
            title: Section title
            content: Section content (first 500 chars)
            
        Returns:
            IEEECategory
        """
        prompt = SECTION_CLASSIFICATION_PROMPT.format(
            section_title=title,
            section_content=content[:500],
        )
        
        response = await self.generate(prompt, max_tokens=50, temperature=0.3)
        response = response.strip().lower()
        
        # Map response to category
        category_map = {
            "abstract": IEEECategory.ABSTRACT,
            "keywords": IEEECategory.KEYWORDS,
            "introduction": IEEECategory.INTRODUCTION,
            "related_work": IEEECategory.RELATED_WORK,
            "methodology": IEEECategory.METHODOLOGY,
            "system_design": IEEECategory.SYSTEM_DESIGN,
            "implementation": IEEECategory.IMPLEMENTATION,
            "results": IEEECategory.RESULTS,
            "conclusion": IEEECategory.CONCLUSION,
            "references": IEEECategory.REFERENCES,
        }
        
        return category_map.get(response, IEEECategory.OTHER)
    
    async def infer_headings(self, text: str) -> List[dict]:
        """
        Infer section headings for a document without clear structure.
        
        Args:
            text: Document text
            
        Returns:
            List of inferred section info
        """
        prompt = HEADING_INFERENCE_PROMPT.format(document_text=text[:5000])
        
        response = await self.generate(prompt, max_tokens=1000, temperature=0.5)
        
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\s*', '', response)
                response = re.sub(r'\s*```$', '', response)
            
            sections = json.loads(response)
            return sections
        except json.JSONDecodeError:
            return []
    
    async def generate_abstract(
        self,
        context: GlobalContext,
        sections_summary: str,
    ) -> str:
        """
        Generate an IEEE-style abstract.
        
        Args:
            context: Global document context
            sections_summary: Summary of main sections
            
        Returns:
            Generated abstract
        """
        prompt = ABSTRACT_GENERATION_PROMPT.format(
            project_title=context.project_title,
            domain=context.domain,
            objective=context.objective,
            keywords=", ".join(context.keywords),
            sections_summary=sections_summary,
        )
        
        return await self.generate(prompt, max_tokens=500)
    
    async def process_sections_parallel(
        self,
        sections: List[Section],
        context: GlobalContext,
        callback=None,
    ) -> List[Section]:
        """
        Process multiple sections in parallel with section length control.
        
        Section Length Control:
        - Target: 250-350 words per major section
        - If < 180 words: expand with technical detail
        - If > 450 words: compress while preserving meaning
        - Never expand/compress: Abstract, Index Terms, References
        
        Args:
            sections: List of sections to process
            context: Global document context
            callback: Optional callback for progress updates
            
        Returns:
            Processed sections with word count logging
        """
        # Section length control settings
        target_words = self.settings.target_section_words  # 300
        min_words = self.settings.min_section_words  # 180
        max_words = self.settings.max_section_words  # 450
        
        # Word count log
        word_count_log = []
        
        async def process_single(section: Section, index: int) -> Section:
            original_word_count = section.word_count or len(section.original_content.split())
            
            # Categories to never rewrite or expand/compress
            # Note: section.category is a string due to Pydantic use_enum_values=True
            skip_category_values = [
                IEEECategory.REFERENCES.value,
                IEEECategory.TITLE.value,
                IEEECategory.KEYWORDS.value,
                IEEECategory.ABSTRACT.value,
            ]
            
            # Skip sections by category (Abstract, Index Terms, References)
            cat_value = section.category if isinstance(section.category, str) else section.category.value
            if cat_value in skip_category_values:
                section.rewritten_content = section.original_content
                section.is_processed = True
                word_count_log.append({
                    "section": section.title,
                    "original": original_word_count,
                    "final": original_word_count,
                    "action": "skipped (special section)"
                })
                return section
            
            # Skip sections by title (References, Bibliography, Appendix, Code, Logs)
            if self._should_skip_rewrite(section.title):
                section.rewritten_content = section.original_content
                section.is_processed = True
                word_count_log.append({
                    "section": section.title,
                    "original": original_word_count,
                    "final": original_word_count,
                    "action": "skipped (title match)"
                })
                if callback:
                    await callback(index, len(sections))
                return section
            
            try:
                # Step 1: Rewrite section (handles chunking for large sections)
                section.rewritten_content = await self.rewrite_section(section, context, target_words)
                section.calculate_word_count()
                
                action = "rewritten"
                
                # Step 2: Section Length Control
                # If section < min_words (180): expand with technical detail
                if section.word_count < min_words:
                    section.rewritten_content = await self.expand_section(
                        section, context, 
                        target_words  # Expand to target (300)
                    )
                    section.calculate_word_count()
                    action = f"expanded ({section.word_count} words)"
                
                # If section > max_words (450): compress while preserving meaning
                elif section.word_count > max_words:
                    section.rewritten_content = await self.compress_section(
                        section, context,
                        target_words + 50  # Compress to 350 (allows some margin)
                    )
                    section.calculate_word_count()
                    action = f"compressed ({section.word_count} words)"
                
                section.is_processed = True
                
                # Log word counts
                word_count_log.append({
                    "section": section.title,
                    "original": original_word_count,
                    "final": section.word_count,
                    "action": action
                })
                
            except Exception as e:
                # On failure, keep original content
                section.rewritten_content = section.original_content
                section.is_processed = True
                word_count_log.append({
                    "section": section.title,
                    "original": original_word_count,
                    "final": original_word_count,
                    "action": f"failed: {str(e)[:50]}"
                })
                logger.warning(f"Failed to rewrite section '{section.title}': {e}")
            
            if callback:
                await callback(index, len(sections))
            
            return section
        
        # Process all sections concurrently
        tasks = [process_single(section, i) for i, section in enumerate(sections)]
        processed_sections = await asyncio.gather(*tasks)
        
        # Print word count summary
        logger.info("=== Section Word Count Summary ===")
        for log in word_count_log:
            logger.info(f"  {log['section']}: {log['original']} -> {log['final']} words ({log['action']})")
        logger.info("==================================")
        
        return list(processed_sections)

