"""
Chart and Graph Data Extraction.

Uses vision models to extract data from:
- Bar charts
- Line graphs
- Pie charts
- Tables rendered as images
"""

import base64
import json
from pathlib import Path
from typing import Optional
import httpx

from app.config import get_settings

settings = get_settings()


async def extract_chart_data(
    image_path: str,
    chart_type: Optional[str] = None
) -> dict:
    """
    Extract data from a chart/graph image using vision AI.
    
    Args:
        image_path: Path to the chart image
        chart_type: Optional hint (bar, line, pie, scatter, table)
        
    Returns:
        {
            "chart_type": "bar",
            "title": "Sales by Quarter",
            "data": [{"label": "Q1", "value": 1200}, ...],
            "x_axis": "Quarter",
            "y_axis": "Sales ($)",
            "insights": ["Q3 had highest sales"]
        }
    """
    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    
    # Determine image type
    suffix = Path(image_path).suffix.lower()
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }.get(suffix, "image/png")
    
    prompt = """Analyze this chart/graph image and extract the data.

Return a JSON object with:
1. "chart_type": The type of chart (bar, line, pie, scatter, area, table, other)
2. "title": The chart title if visible
3. "data": Array of data points. Format depends on chart type:
   - Bar/Line: [{"label": "X value", "value": Y value}, ...]
   - Pie: [{"label": "Category", "value": percentage}, ...]
   - Scatter: [{"x": X, "y": Y}, ...]
   - Table: [{"column1": "value", "column2": "value"}, ...]
4. "x_axis": X-axis label if visible
5. "y_axis": Y-axis label if visible
6. "legend": Array of legend items if present
7. "insights": 2-3 key insights from the data

Be as accurate as possible with the values. If you can't read exact values, estimate based on the scale.

Return ONLY valid JSON, no explanation."""

    try:
        if settings.anthropic_api_key:
            result = await _call_anthropic_vision(prompt, image_data, media_type)
        elif settings.openai_api_key:
            result = await _call_openai_vision(prompt, image_data, media_type)
        else:
            return {"error": "No vision API configured", "chart_type": "unknown"}
        
        # Parse response
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        
        return json.loads(clean)
    except Exception as e:
        return {"error": str(e), "chart_type": "unknown"}


async def extract_diagram_info(
    image_path: str,
    diagram_type: Optional[str] = None
) -> dict:
    """
    Extract information from diagrams/schematics.
    
    Types: flowchart, circuit, architecture, org_chart, uml, other
    """
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    
    prompt = """Analyze this diagram/schematic and extract its information.

Return a JSON object with:
1. "diagram_type": Type (flowchart, circuit, architecture, org_chart, uml, process, network, other)
2. "title": Title if visible
3. "components": Array of identified components/nodes
   [{"id": "1", "label": "Start", "type": "node"}, ...]
4. "connections": Array of connections between components
   [{"from": "1", "to": "2", "label": "optional edge label"}, ...]
5. "hierarchy": For org charts or hierarchical diagrams
6. "description": Brief description of what the diagram shows
7. "key_elements": Most important elements to note

Return ONLY valid JSON."""

    try:
        if settings.anthropic_api_key:
            result = await _call_anthropic_vision(prompt, image_data, "image/png")
        elif settings.openai_api_key:
            result = await _call_openai_vision(prompt, image_data, "image/png")
        else:
            return {"error": "No vision API configured"}
        
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        
        return json.loads(clean)
    except Exception as e:
        return {"error": str(e)}


async def _call_anthropic_vision(prompt: str, image_base64: str, media_type: str) -> str:
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
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }]
            },
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


async def _call_openai_vision(prompt: str, image_base64: str, media_type: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{image_base64}"
                            }
                        }
                    ]
                }],
                "max_tokens": 2048
            },
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
