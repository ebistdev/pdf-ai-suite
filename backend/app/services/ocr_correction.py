"""
Smart OCR Correction Service.

Uses LLM to fix common OCR errors:
- Character substitutions (0/O, 1/l/I, rn/m)
- Word boundary issues
- Language-specific corrections
- Context-aware fixes
"""

import re
from typing import Optional
import httpx

from app.config import get_settings

settings = get_settings()


# Common OCR character confusions
OCR_CONFUSIONS = {
    '0': ['O', 'o', 'Q'],
    'O': ['0', 'Q', 'o'],
    '1': ['l', 'I', '|', 'i'],
    'l': ['1', 'I', '|', 'i'],
    'I': ['1', 'l', '|'],
    '5': ['S', 's'],
    'S': ['5', '$'],
    '8': ['B', '&'],
    'B': ['8', '&'],
    'rn': ['m'],
    'vv': ['w'],
    'cl': ['d'],
    'cj': ['g'],
}


def quick_fix_ocr(text: str) -> str:
    """
    Apply quick rule-based OCR corrections.
    
    Fixes obvious errors without AI.
    """
    corrections = [
        # Common word fixes
        (r'\btne\b', 'the'),
        (r'\bTne\b', 'The'),
        (r'\band\b', 'and'),
        (r'\bvvith\b', 'with'),
        (r'\bfrorn\b', 'from'),
        (r'\bthat\b', 'that'),
        (r'\bvvas\b', 'was'),
        
        # Number/letter confusions in common contexts
        (r'\b(\d+)[oO](\d+)\b', r'\g<1>0\g<2>'),  # 1O0 -> 100
        (r'\b[Il](\d{2,})\b', r'1\g<1>'),  # I23 -> 123
        
        # Punctuation fixes
        (r'\s+\.', '.'),
        (r'\s+,', ','),
        (r',,', ','),
        (r'\.\.(?!\.)', '.'),
        
        # Spacing fixes
        (r'([a-z])([A-Z])', r'\g<1> \g<2>'),  # missingSpace -> missing Space
        (r'\s{2,}', ' '),  # Multiple spaces
    ]
    
    result = text
    for pattern, replacement in corrections:
        result = re.sub(pattern, replacement, result)
    
    return result


async def smart_fix_ocr(
    text: str,
    language: str = "en",
    context: Optional[str] = None
) -> dict:
    """
    Use AI to fix OCR errors with context awareness.
    
    Args:
        text: OCR text to fix
        language: Language code
        context: Optional context about the document
        
    Returns:
        {
            "corrected_text": "...",
            "corrections": [{"original": "...", "corrected": "...", "confidence": 0.95}],
            "confidence": 0.92
        }
    """
    if not settings.anthropic_api_key and not settings.openai_api_key:
        # Fall back to rule-based correction
        corrected = quick_fix_ocr(text)
        return {
            "corrected_text": corrected,
            "corrections": [],
            "confidence": 0.7,
            "method": "rule-based"
        }
    
    prompt = f"""Fix OCR errors in this text. The text was extracted via OCR and may contain character recognition errors.

LANGUAGE: {language}
{f"CONTEXT: {context}" if context else ""}

TEXT TO FIX:
{text[:5000]}

INSTRUCTIONS:
1. Fix character confusion errors (0/O, 1/l/I, rn/m, etc.)
2. Fix word boundary issues
3. Fix obvious spelling errors caused by OCR
4. Preserve intentional formatting and structure
5. Do NOT change content meaning, only fix recognition errors

Return JSON:
{{
    "corrected_text": "the corrected text",
    "corrections": [
        {{"original": "tne", "corrected": "the", "confidence": 0.99}},
        ...
    ],
    "overall_confidence": 0.95
}}

Return ONLY valid JSON."""

    try:
        if settings.anthropic_api_key:
            result = await _call_anthropic(prompt)
        else:
            result = await _call_openai(prompt)
        
        # Parse response
        import json
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        
        data = json.loads(clean)
        data["method"] = "ai"
        return data
    except Exception as e:
        # Fall back to rule-based
        corrected = quick_fix_ocr(text)
        return {
            "corrected_text": corrected,
            "corrections": [],
            "confidence": 0.7,
            "method": "rule-based",
            "ai_error": str(e)
        }


def calculate_ocr_confidence(text: str) -> dict:
    """
    Estimate OCR quality/confidence based on text analysis.
    
    Returns confidence score and issues found.
    """
    issues = []
    total_words = len(text.split())
    
    # Check for common OCR error patterns
    suspicious_patterns = [
        (r'\b[Il1]{2,}\b', "Ambiguous I/l/1 sequences"),
        (r'\b\w*[0O]{2,}\w*\b', "Ambiguous 0/O sequences"),
        (r'\brn\b', "Possible 'm' as 'rn'"),
        (r'\bvv\b', "Possible 'w' as 'vv'"),
        (r'[^\x00-\x7F]', "Non-ASCII characters"),
        (r'\s{3,}', "Unusual spacing"),
        (r'[A-Z]{10,}', "Long uppercase sequences"),
    ]
    
    issue_count = 0
    for pattern, description in suspicious_patterns:
        matches = re.findall(pattern, text)
        if matches:
            issues.append({
                "type": description,
                "count": len(matches),
                "examples": matches[:3]
            })
            issue_count += len(matches)
    
    # Calculate confidence
    if total_words == 0:
        confidence = 0
    else:
        error_rate = issue_count / total_words
        confidence = max(0, min(1, 1 - (error_rate * 2)))
    
    return {
        "confidence": round(confidence, 3),
        "total_words": total_words,
        "potential_issues": issue_count,
        "issues": issues,
        "quality": "high" if confidence > 0.9 else "medium" if confidence > 0.7 else "low"
    }


async def _call_anthropic(prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


async def _call_openai(prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4096,
                "temperature": 0.1
            },
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
