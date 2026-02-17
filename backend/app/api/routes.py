import uuid
import asyncio
import aiofiles
import zipfile
import io
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.config import get_settings
from app.services.extractor import get_extractor, OutputFormat
from app.services.languages import get_supported_languages, detect_language
from app.services.summarizer import create_concise_summary, extract_structured_data

settings = get_settings()
router = APIRouter()

# Ensure directories exist
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)


class ExtractionOptions(BaseModel):
    """Options for document extraction."""
    output_format: OutputFormat = OutputFormat.MARKDOWN
    extract_images: bool = True
    extract_tables: bool = True


class ExtractionResponse(BaseModel):
    """Response from extraction."""
    job_id: str
    filename: str
    num_pages: int
    content: str  # Main content in requested format
    tables_count: int
    images_count: int
    title: Optional[str] = None
    headings: list[dict] = []


class TableResponse(BaseModel):
    index: int
    page: int
    markdown: str
    csv: Optional[str] = None


class QuickExtractResponse(BaseModel):
    """Quick extraction response."""
    filename: str
    num_pages: int
    markdown: str
    text: str
    tables: list[TableResponse]
    images_extracted: int
    title: Optional[str] = None
    headings: list[dict] = []


@router.post("/extract", response_model=QuickExtractResponse)
async def extract_document(
    file: UploadFile = File(...),
    extract_images: bool = True,
    background_tasks: BackgroundTasks = None
):
    """
    Extract content from a PDF or document.
    
    Supported formats: PDF, DOCX, PPTX, HTML, Images
    
    Returns:
    - Markdown text with structure preserved
    - Plain text
    - Extracted tables (markdown + CSV)
    - Image count (images saved to job folder)
    """
    # Validate file size
    file.file.seek(0, 2)
    size_mb = file.file.tell() / (1024 * 1024)
    file.file.seek(0)
    
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_file_size_mb}MB"
        )
    
    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    
    # Save uploaded file
    upload_path = settings.upload_dir / f"{job_id}_{file.filename}"
    async with aiofiles.open(upload_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Output directory for this job
    job_output_dir = settings.output_dir / job_id
    
    try:
        # Extract
        extractor = get_extractor()
        result = await extractor.extract(
            file_path=upload_path,
            output_dir=job_output_dir if extract_images else None,
            extract_images=extract_images
        )
        
        # Build response
        tables = [
            TableResponse(
                index=t.index,
                page=t.page,
                markdown=t.markdown,
                csv=t.csv
            ) for t in result.tables
        ]
        
        return QuickExtractResponse(
            filename=result.filename,
            num_pages=result.num_pages,
            markdown=result.markdown,
            text=result.text,
            tables=tables,
            images_extracted=len(result.images),
            title=result.title,
            headings=result.headings
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    
    finally:
        # Clean up upload file
        if background_tasks:
            background_tasks.add_task(cleanup_file, upload_path)


@router.post("/extract/url")
async def extract_from_url(url: str, extract_images: bool = True):
    """Extract content from a URL (PDF or document link)."""
    import httpx
    
    # Download file
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, follow_redirects=True, timeout=60.0)
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to download: {str(e)}")
    
    # Get filename from URL
    filename = url.split("/")[-1].split("?")[0] or "document.pdf"
    
    # Generate job ID
    job_id = str(uuid.uuid4())[:8]
    
    # Save file
    upload_path = settings.upload_dir / f"{job_id}_{filename}"
    async with aiofiles.open(upload_path, 'wb') as f:
        await f.write(response.content)
    
    # Output directory
    job_output_dir = settings.output_dir / job_id
    
    try:
        extractor = get_extractor()
        result = await extractor.extract(
            file_path=upload_path,
            output_dir=job_output_dir if extract_images else None,
            extract_images=extract_images
        )
        
        tables = [
            TableResponse(
                index=t.index,
                page=t.page,
                markdown=t.markdown,
                csv=t.csv
            ) for t in result.tables
        ]
        
        return QuickExtractResponse(
            filename=result.filename,
            num_pages=result.num_pages,
            markdown=result.markdown,
            text=result.text,
            tables=tables,
            images_extracted=len(result.images),
            title=result.title,
            headings=result.headings
        )
        
    finally:
        # Clean up
        upload_path.unlink(missing_ok=True)


@router.get("/tables/{job_id}")
async def get_tables(job_id: str, format: str = "markdown"):
    """Get extracted tables from a job."""
    # This would need job storage - simplified for MVP
    raise HTTPException(status_code=501, detail="Table retrieval requires job storage (coming soon)")


@router.get("/images/{job_id}/{image_index}")
async def get_image(job_id: str, image_index: int):
    """Get an extracted image from a job."""
    image_path = settings.output_dir / job_id / f"image_{image_index:03d}.png"
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)


async def cleanup_file(path: Path):
    """Clean up uploaded file after processing."""
    try:
        path.unlink(missing_ok=True)
    except:
        pass


# ============ Languages ============

@router.get("/languages")
async def list_languages():
    """List supported OCR languages."""
    return get_supported_languages()


# ============ AI Summary ============

@router.post("/extract/summarize")
async def extract_with_summary(
    file: UploadFile = File(...),
    language: str = "en",
    max_bullets: int = 15
):
    """
    Extract content AND create a concise, itemized summary.
    
    Returns:
    - Standard extraction (markdown, text, tables)
    - AI-generated summary with key points
    - Important numbers and figures
    """
    # First do standard extraction
    file.file.seek(0, 2)
    size_mb = file.file.tell() / (1024 * 1024)
    file.file.seek(0)
    
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(status_code=413, detail=f"File too large")
    
    job_id = str(uuid.uuid4())[:8]
    upload_path = settings.upload_dir / f"{job_id}_{file.filename}"
    
    async with aiofiles.open(upload_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    try:
        extractor = get_extractor()
        result = await extractor.extract(file_path=upload_path, extract_images=False)
        
        # Create AI summary
        tables_data = [{"index": t.index, "markdown": t.markdown} for t in result.tables]
        summary = await create_concise_summary(
            result.markdown,
            tables_data,
            result.num_pages,
            max_bullets
        )
        
        # Detect language if not specified
        detected_lang = detect_language(result.text[:1000]) if result.text else language
        
        return {
            "filename": result.filename,
            "num_pages": result.num_pages,
            "language_detected": detected_lang,
            "summary": summary.get("summary", ""),
            "key_points": summary.get("key_points", []),
            "important_numbers": summary.get("important_numbers", []),
            "figures_mentioned": summary.get("figures_mentioned", []),
            "tables_summary": summary.get("tables_summary", []),
            "tables_count": len(result.tables),
            "markdown": result.markdown,
            "text": result.text
        }
    finally:
        upload_path.unlink(missing_ok=True)


@router.post("/extract/structured")
async def extract_structured(file: UploadFile = File(...)):
    """
    Extract structured data from documents like invoices, forms, receipts.
    
    Returns field-value pairs based on document type.
    """
    job_id = str(uuid.uuid4())[:8]
    upload_path = settings.upload_dir / f"{job_id}_{file.filename}"
    
    async with aiofiles.open(upload_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    try:
        extractor = get_extractor()
        result = await extractor.extract(file_path=upload_path, extract_images=False)
        
        # Extract structured data
        structured = await extract_structured_data(result.text)
        
        return {
            "filename": result.filename,
            "document_type": structured.get("document_type", "unknown"),
            "confidence": structured.get("confidence", 0),
            "extracted_fields": structured.get("extracted_fields", {}),
            "line_items": structured.get("line_items", []),
            "raw_text": result.text[:2000]  # First 2000 chars for reference
        }
    finally:
        upload_path.unlink(missing_ok=True)


# ============ Batch Processing ============

@router.post("/extract/batch")
async def extract_batch(
    files: List[UploadFile] = File(...),
    output_format: str = "markdown",
    extract_images: bool = False
):
    """
    Process multiple documents at once.
    
    Returns results for each file or a ZIP with all outputs.
    """
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per batch")
    
    results = []
    
    for file in files:
        job_id = str(uuid.uuid4())[:8]
        upload_path = settings.upload_dir / f"{job_id}_{file.filename}"
        
        try:
            async with aiofiles.open(upload_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
            
            extractor = get_extractor()
            result = await extractor.extract(file_path=upload_path, extract_images=False)
            
            results.append({
                "filename": result.filename,
                "num_pages": result.num_pages,
                "success": True,
                "content": result.markdown if output_format == "markdown" else result.text,
                "tables_count": len(result.tables)
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
        finally:
            upload_path.unlink(missing_ok=True)
    
    return {
        "total_files": len(files),
        "successful": sum(1 for r in results if r.get("success")),
        "failed": sum(1 for r in results if not r.get("success")),
        "results": results
    }


@router.post("/extract/batch/zip")
async def extract_batch_to_zip(
    files: List[UploadFile] = File(...),
    output_format: str = "markdown"
):
    """
    Process multiple documents and return a ZIP file with all outputs.
    """
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per batch")
    
    # Create in-memory ZIP
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            job_id = str(uuid.uuid4())[:8]
            upload_path = settings.upload_dir / f"{job_id}_{file.filename}"
            
            try:
                async with aiofiles.open(upload_path, 'wb') as f:
                    content = await file.read()
                    await f.write(content)
                
                extractor = get_extractor()
                result = await extractor.extract(file_path=upload_path, extract_images=False)
                
                # Add to ZIP
                base_name = Path(file.filename).stem
                
                if output_format == "markdown":
                    zip_file.writestr(f"{base_name}.md", result.markdown)
                elif output_format == "text":
                    zip_file.writestr(f"{base_name}.txt", result.text)
                elif output_format == "json":
                    import json
                    data = {
                        "filename": result.filename,
                        "num_pages": result.num_pages,
                        "markdown": result.markdown,
                        "text": result.text,
                        "tables": [{"markdown": t.markdown, "csv": t.csv} for t in result.tables],
                        "headings": result.headings
                    }
                    zip_file.writestr(f"{base_name}.json", json.dumps(data, indent=2))
                
                # Add tables as CSV
                for i, table in enumerate(result.tables):
                    if table.csv:
                        zip_file.writestr(f"{base_name}_table_{i+1}.csv", table.csv)
                        
            except Exception as e:
                zip_file.writestr(f"{Path(file.filename).stem}_error.txt", f"Error: {str(e)}")
            finally:
                upload_path.unlink(missing_ok=True)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=extracted_documents.zip"}
    )


# ============ Paragraph Structure ============

@router.post("/extract/structure")
async def extract_with_structure(file: UploadFile = File(...)):
    """
    Extract with detailed paragraph structure.
    
    Identifies:
    - Headings (H1-H6)
    - Paragraphs
    - Lists (bullet, numbered)
    - Code blocks
    - Quotes
    """
    job_id = str(uuid.uuid4())[:8]
    upload_path = settings.upload_dir / f"{job_id}_{file.filename}"
    
    async with aiofiles.open(upload_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    try:
        extractor = get_extractor()
        result = await extractor.extract(file_path=upload_path, extract_images=False)
        
        # Parse markdown to identify structure
        structure = parse_document_structure(result.markdown)
        
        return {
            "filename": result.filename,
            "num_pages": result.num_pages,
            "structure": structure,
            "headings": result.headings,
            "markdown": result.markdown
        }
    finally:
        upload_path.unlink(missing_ok=True)


def parse_document_structure(markdown: str) -> list[dict]:
    """Parse markdown into structural elements."""
    import re
    
    elements = []
    lines = markdown.split('\n')
    current_para = []
    in_code_block = False
    in_list = False
    
    for i, line in enumerate(lines):
        # Code blocks
        if line.startswith('```'):
            if in_code_block:
                elements.append({"type": "code_block", "content": '\n'.join(current_para)})
                current_para = []
                in_code_block = False
            else:
                if current_para:
                    elements.append({"type": "paragraph", "content": '\n'.join(current_para)})
                    current_para = []
                in_code_block = True
            continue
        
        if in_code_block:
            current_para.append(line)
            continue
        
        # Headings
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            if current_para:
                elements.append({"type": "paragraph", "content": '\n'.join(current_para)})
                current_para = []
            level = len(heading_match.group(1))
            elements.append({"type": f"heading_{level}", "content": heading_match.group(2)})
            continue
        
        # Lists
        list_match = re.match(r'^[\s]*[-*+]\s+(.+)$', line) or re.match(r'^[\s]*\d+\.\s+(.+)$', line)
        if list_match:
            if current_para and not in_list:
                elements.append({"type": "paragraph", "content": '\n'.join(current_para)})
                current_para = []
            in_list = True
            current_para.append(line)
            continue
        
        if in_list and line.strip() == '':
            elements.append({"type": "list", "content": '\n'.join(current_para)})
            current_para = []
            in_list = False
            continue
        
        # Regular paragraphs
        if line.strip():
            current_para.append(line)
        elif current_para:
            elem_type = "list" if in_list else "paragraph"
            elements.append({"type": elem_type, "content": '\n'.join(current_para)})
            current_para = []
            in_list = False
    
    # Final element
    if current_para:
        elem_type = "list" if in_list else "paragraph"
        elements.append({"type": elem_type, "content": '\n'.join(current_para)})
    
    return elements
