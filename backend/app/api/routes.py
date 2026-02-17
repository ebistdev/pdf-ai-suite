import uuid
import aiofiles
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.config import get_settings
from app.services.extractor import get_extractor, OutputFormat

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
