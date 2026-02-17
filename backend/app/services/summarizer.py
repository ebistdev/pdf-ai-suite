"""
AI Summarizer for concise, itemized output.

Takes extracted content and produces:
- Concise bullet-point summaries
- Key items/facts extracted
- Structured data from tables/graphs
"""

import json
from typing import Optional
import httpx

from app.config import get_settings

settings = get_settings()


async def create_concise_summary(
    markdown_content: str,
    tables: list[dict],
    num_pages: int,
    max_bullets: int = 20
) -> dict:
    """
    Create a concise, itemized summary of document content.
    
    Returns:
        {
            "summary": "Brief overview",
            "key_points": ["point 1", "point 2", ...],
            "tables_summary": [{"title": "...", "key_data": [...]}],
            "figures_mentioned": ["fig1", "fig2"],
            "important_numbers": [{"value": "...", "context": "..."}]
        }
    """
    if not settings.anthropic_api_key and not settings.openai_api_key:
        # Return basic summary without AI
        return {
            "summary": f"Document with {num_pages} pages and {len(tables)} tables.",
            "key_points": [],
            "tables_summary": [],
            "figures_mentioned": [],
            "important_numbers": []
        }
    
    prompt = f"""Analyze this document and create a concise, itemized summary.

DOCUMENT CONTENT:
{markdown_content[:15000]}  # Truncate for API limits

NUMBER OF TABLES: {len(tables)}

INSTRUCTIONS:
1. Write a 1-2 sentence summary
2. Extract up to {max_bullets} key points as bullet items
3. Identify important numbers/statistics with context
4. Note any figures or diagrams mentioned
5. Summarize key data from tables

OUTPUT FORMAT (JSON only):
{{
    "summary": "Brief 1-2 sentence overview",
    "key_points": ["Key point 1", "Key point 2", ...],
    "tables_summary": [{{"title": "Table name/topic", "key_data": ["fact1", "fact2"]}}],
    "figures_mentioned": ["Figure 1: Description", ...],
    "important_numbers": [{{"value": "42%", "context": "market share"}}]
}}

Return ONLY valid JSON."""

    try:
        if settings.anthropic_api_key:
            result = await _call_anthropic(prompt)
        else:
            result = await _call_openai(prompt)
        
        # Parse JSON response
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        
        return json.loads(clean)
    except Exception as e:
        return {
            "summary": f"Document with {num_pages} pages.",
            "key_points": [],
            "error": str(e)
        }


async def extract_structured_data(
    content: str,
    extraction_type: str = "auto"
) -> dict:
    """
    Extract structured data based on document type.
    
    Types: invoice, receipt, form, report, academic, contract
    """
    prompt = f"""Extract structured data from this document.

DOCUMENT:
{content[:10000]}

Identify the document type and extract relevant fields.

For INVOICES/RECEIPTS:
- vendor, date, items, totals, payment info

For FORMS:
- field names and values

For REPORTS:
- title, authors, date, key findings, conclusions

For CONTRACTS:
- parties, dates, terms, obligations

OUTPUT FORMAT (JSON):
{{
    "document_type": "invoice|receipt|form|report|academic|contract|other",
    "confidence": 0.95,
    "extracted_fields": {{
        "field_name": "value",
        ...
    }},
    "line_items": [
        {{"description": "...", "quantity": 1, "amount": "..."}}
    ]
}}

Return ONLY valid JSON."""

    try:
        if settings.anthropic_api_key:
            result = await _call_anthropic(prompt)
        else:
            result = await _call_openai(prompt)
        
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        
        return json.loads(clean)
    except Exception as e:
        return {"error": str(e), "document_type": "unknown"}


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
                "max_tokens": 2048,
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
                "max_tokens": 2048,
                "temperature": 0.1
            },
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
