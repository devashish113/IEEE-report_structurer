"""
Context Extractor for IEEE Report Restructurer.
Extracts global context (title, domain, objective, keywords) from the document.
"""

import json
import re
from typing import Optional
from ..models.document import GlobalContext
from ..prompts.templates import CONTEXT_EXTRACTION_PROMPT
from ..config import get_settings


class ContextExtractor:
    """Service for extracting global context from documents."""
    
    def __init__(self, llm_service=None):
        self.settings = get_settings()
        self.llm_service = llm_service
    
    def set_llm_service(self, llm_service):
        """Set the LLM service for AI-based extraction."""
        self.llm_service = llm_service
    
    async def extract_context(self, full_text: str) -> GlobalContext:
        """
        Extract global context from the document.
        
        Args:
            full_text: Full document text
            
        Returns:
            GlobalContext object
        """
        context = GlobalContext()
        
        # Try heuristic extraction first
        context = self._heuristic_extraction(full_text, context)
        
        # Use LLM for better extraction if available
        if self.llm_service:
            try:
                context = await self._llm_extraction(full_text, context)
            except Exception as e:
                print(f"LLM extraction failed, using heuristics: {e}")
        
        return context
    
    def _heuristic_extraction(self, text: str, context: GlobalContext) -> GlobalContext:
        """
        Extract context using rule-based heuristics.
        """
        lines = text.split('\n')
        
        # Extract title (usually first non-empty line)
        for line in lines[:10]:
            line = line.strip()
            if line and len(line) > 5 and len(line) < 200:
                context.project_title = line
                break
        
        # Extract keywords if labeled
        keywords_match = re.search(
            r'(?:keywords?|index terms?)[:\s-]+([^\n]+)',
            text,
            re.IGNORECASE
        )
        if keywords_match:
            keywords_text = keywords_match.group(1)
            # Split by common separators
            keywords = re.split(r'[,;•·]', keywords_text)
            context.keywords = [k.strip() for k in keywords if k.strip()][:10]
        
        # Extract abstract
        abstract_match = re.search(
            r'(?:abstract)[:\s-]*\n?(.+?)(?=\n\s*(?:keywords?|introduction|1\.|I\.))',
            text,
            re.IGNORECASE | re.DOTALL
        )
        if abstract_match:
            context.abstract_text = abstract_match.group(1).strip()[:1000]
        
        # Try to infer domain from keywords or content
        domain_keywords = {
            "machine learning": "Machine Learning",
            "deep learning": "Deep Learning",
            "neural network": "Deep Learning",
            "web application": "Web Development",
            "mobile app": "Mobile Development",
            "iot": "Internet of Things",
            "cloud": "Cloud Computing",
            "blockchain": "Blockchain",
            "security": "Cybersecurity",
            "nlp": "Natural Language Processing",
            "computer vision": "Computer Vision",
            "database": "Database Systems",
            "network": "Networking",
        }
        
        text_lower = text.lower()
        for keyword, domain in domain_keywords.items():
            if keyword in text_lower:
                context.domain = domain
                break
        
        # Extract objective from introduction or abstract
        objective_patterns = [
            r'(?:objective|aim|goal|purpose)[:\s]+([^.]+\.)',
            r'(?:this paper|this project|this work|we propose)[:\s]*([^.]+\.)',
        ]
        for pattern in objective_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                context.objective = match.group(1).strip()[:500]
                break
        
        return context
    
    async def _llm_extraction(self, text: str, existing_context: GlobalContext) -> GlobalContext:
        """
        Use LLM to extract context.
        """
        # Use first 3000 chars for context extraction
        truncated_text = text[:3000]
        
        prompt = CONTEXT_EXTRACTION_PROMPT.format(document_text=truncated_text)
        
        response = await self.llm_service.generate(prompt)
        
        # Parse JSON response
        try:
            # Clean potential markdown formatting
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```(?:json)?\s*', '', response)
                response = re.sub(r'\s*```$', '', response)
            
            data = json.loads(response)
            
            # Update context with LLM results
            if data.get("project_title"):
                existing_context.project_title = data["project_title"]
            if data.get("domain"):
                existing_context.domain = data["domain"]
            if data.get("objective"):
                existing_context.objective = data["objective"]
            if data.get("keywords"):
                existing_context.keywords = data["keywords"][:10]
            if data.get("authors"):
                existing_context.authors = data["authors"]
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse LLM context response: {e}")
        
        return existing_context
    
    def generate_context_summary(self, context: GlobalContext) -> str:
        """
        Generate a summary string from the context.
        """
        parts = []
        
        if context.project_title:
            parts.append(f"Title: {context.project_title}")
        if context.domain:
            parts.append(f"Domain: {context.domain}")
        if context.objective:
            parts.append(f"Objective: {context.objective}")
        if context.keywords:
            parts.append(f"Keywords: {', '.join(context.keywords)}")
        
        return "\n".join(parts)
