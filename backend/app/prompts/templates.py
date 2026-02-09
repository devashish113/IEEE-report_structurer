"""
LLM Prompt Templates for IEEE Report Restructurer.
Contains all prompts used for document processing.
"""

# Context extraction prompt
CONTEXT_EXTRACTION_PROMPT = """You are an academic document analyzer. Extract the following information from this document text:

DOCUMENT TEXT:
{document_text}

Extract and return a JSON object with these fields:
- project_title: The main title of the project/paper
- domain: The technical/academic domain (e.g., "Machine Learning", "Web Development", "IoT")
- objective: The main objective or goal of the project (1-2 sentences)
- keywords: A list of 5-7 relevant keywords
- authors: List of author names if mentioned

Return ONLY valid JSON, no other text. Example format:
{{
    "project_title": "...",
    "domain": "...",
    "objective": "...",
    "keywords": ["...", "..."],
    "authors": ["...", "..."]
}}"""


# Section classification prompt
SECTION_CLASSIFICATION_PROMPT = """You are an academic document structure analyzer. Given the following section title and content, classify it into one of these IEEE categories:

Categories:
- abstract: Paper abstract/summary
- keywords: Keywords/index terms section
- introduction: Introduction, background, motivation
- related_work: Literature review, related work, previous work
- methodology: Methodology, proposed method, approach
- system_design: System design, architecture, framework
- implementation: Implementation details, development
- results: Results, experiments, evaluation, discussion
- conclusion: Conclusion, future work
- references: References, bibliography
- other: Doesn't fit any category

SECTION TITLE: {section_title}

SECTION CONTENT (first 500 chars):
{section_content}

Return ONLY the category name as a single word (e.g., "introduction"), nothing else."""


# Section rewrite prompt - PRESERVES content, only improves style
SECTION_REWRITE_PROMPT = """You are an expert academic writer specializing in IEEE-format papers. Rewrite the following section to improve academic language while PRESERVING ALL content.

CONTEXT:
- Project Title: {project_title}
- Domain: {domain}
- Objective: {objective}

SECTION: {section_title}
ORIGINAL CONTENT:
{section_content}

CRITICAL REQUIREMENTS:
1. PRESERVE ALL original information - do NOT shorten or remove content
2. Use formal academic language (third person, passive voice where appropriate)
3. Maintain all technical accuracy and meaning
4. Remove any informal language, contractions, or colloquialisms
5. Improve clarity and logical flow
6. Use consistent terminology
7. Target approximately {target_words} words (but prioritize content preservation)
8. Ensure smooth paragraph transitions
9. You may ADD clarifying phrases but NEVER remove technical details

Return ONLY the rewritten content, no explanations or headers."""


# Section expansion prompt - AGGRESSIVE expansion
SECTION_EXPAND_PROMPT = """You are an expert academic writer. The following section is too short and MUST be expanded significantly.

CONTEXT:
- Project Title: {project_title}
- Domain: {domain}
- Objective: {objective}

SECTION: {section_title}
CURRENT CONTENT ({current_words} words):
{section_content}

EXPANSION REQUIREMENTS - YOU MUST:
1. Expand to AT LEAST {target_words} words (this is critical)
2. Add detailed technical explanations for each concept mentioned
3. Include supporting rationale and justifications
4. Add relevant background context
5. Explain WHY decisions were made, not just WHAT was done
6. Include implications and significance of each point
7. Add transitional sentences between paragraphs
8. Maintain formal academic tone throughout
9. Do NOT add fictional data or made-up results
10. Do NOT contradict the original content

TECHNIQUES TO ADD LENGTH:
- Explain technical terms when first introduced
- Add "This is significant because..." explanations
- Include comparisons to alternative approaches
- Elaborate on implementation considerations
- Discuss potential challenges and how they were addressed
- Add contextual background for each major point

Return ONLY the expanded content. It MUST be at least {target_words} words."""


# Section compression prompt - GENTLE compression, preserve meaning
SECTION_COMPRESS_PROMPT = """You are an expert academic editor. The following section needs gentle compression while preserving ALL key information.

CONTEXT:
- Project Title: {project_title}
- Domain: {domain}  
- Objective: {objective}

SECTION: {section_title}
CURRENT CONTENT ({current_words} words):
{section_content}

COMPRESSION REQUIREMENTS:
1. Target approximately {target_words} words
2. PRESERVE all technical details and key information
3. Remove ONLY redundant phrases and unnecessary repetition
4. Combine sentences where meaning is preserved
5. Remove filler words like "basically", "actually", "in fact"
6. Keep all data, numbers, and technical specifications
7. Maintain formal academic tone
8. Ensure compressed version remains coherent and complete
9. PRIORITIZE keeping content over hitting word target

DO NOT REMOVE:
- Technical explanations
- Results or findings
- Methodology details
- Key concepts

Return ONLY the compressed content, no explanations."""


# Reference formatting prompt
REFERENCE_FORMAT_PROMPT = """You are an expert in IEEE reference formatting. Convert the following references to proper IEEE numbered format.

ORIGINAL REFERENCES:
{references}

IEEE FORMAT REQUIREMENTS:
1. Number references sequentially: [1], [2], [3], etc.
2. Author names: First initials followed by last name (e.g., J. Smith)
3. For multiple authors: use "and" before last author, or "et al." for 4+ authors
4. Article titles in quotes
5. Journal/conference names in italics (indicate with *name*)
6. Include volume, issue, pages, year
7. For websites: include URL and access date

Example IEEE format:
[1] A. B. Author and C. D. Author, "Article title," *Journal Name*, vol. X, no. Y, pp. 1-10, Year.
[2] E. F. Author, "Conference paper title," in *Proc. Conference Name*, City, Country, Year, pp. 1-5.

Return the formatted references, each on a new line."""


# Heading inference prompt
HEADING_INFERENCE_PROMPT = """You are an academic document structure analyzer. The following text appears to be a continuous document without clear headings. Analyze the content and suggest how to split it into sections with appropriate headings.

DOCUMENT TEXT:
{document_text}

Based on the content, identify logical section breaks and suggest headings that would fit IEEE paper structure:
- Abstract
- Introduction
- Related Work/Literature Review
- Methodology
- System Design/Architecture
- Implementation
- Results/Experiments
- Conclusion

Return a JSON array where each item has:
- "heading": suggested section heading
- "start_text": first 50 characters of where this section starts
- "category": the IEEE category (abstract, introduction, methodology, etc.)

Return ONLY valid JSON array. Example:
[
    {{"heading": "Abstract", "start_text": "This paper presents...", "category": "abstract"}},
    {{"heading": "Introduction", "start_text": "In recent years...", "category": "introduction"}}
]"""


# Abstract generation prompt
ABSTRACT_GENERATION_PROMPT = """You are an expert academic writer. Generate a concise IEEE-style abstract for this paper.

CONTEXT:
- Project Title: {project_title}
- Domain: {domain}
- Objective: {objective}
- Keywords: {keywords}

MAIN SECTIONS SUMMARY:
{sections_summary}

ABSTRACT REQUIREMENTS:
1. 150-250 words
2. Include: background, objective, method, results, conclusion
3. Use formal academic tone
4. Be self-contained and informative
5. Do not use references in the abstract
6. Start with context/motivation, end with key findings

Return ONLY the abstract text, no labels or explanations."""
