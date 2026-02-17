"""
PDF/Document Extraction Service using Docling.

Extracts:
- Text with structure (headings, paragraphs)
- Tables
- Images
- Metadata
"""

import asyncio
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.pipeline.simple_pipeline import SimplePipeline

from app.config import get_settings

settings = get_settings()


class OutputFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    TEXT = "text"


@dataclass
class ExtractedTable:
    """Extracted table data."""
    index: int
    page: int
    markdown: str
    csv: Optional[str] = None


@dataclass
class ExtractedImage:
    """Extracted image reference."""
    index: int
    page: int
    path: str
    caption: Optional[str] = None


@dataclass
class ExtractionResult:
    """Complete extraction result."""
    filename: str
    num_pages: int
    
    # Content
    markdown: str
    text: str
    
    # Structured data
    tables: list[ExtractedTable] = field(default_factory=list)
    images: list[ExtractedImage] = field(default_factory=list)
    
    # Metadata
    title: Optional[str] = None
    author: Optional[str] = None
    language: Optional[str] = None
    
    # Document structure
    headings: list[dict] = field(default_factory=list)
    
    def to_dict(self):
        return {
            "filename": self.filename,
            "num_pages": self.num_pages,
            "markdown": self.markdown,
            "text": self.text,
            "tables": [
                {"index": t.index, "page": t.page, "markdown": t.markdown, "csv": t.csv}
                for t in self.tables
            ],
            "images": [
                {"index": i.index, "page": i.page, "path": i.path, "caption": i.caption}
                for i in self.images
            ],
            "title": self.title,
            "author": self.author,
            "language": self.language,
            "headings": self.headings
        }


class DocumentExtractor:
    """Extract content from PDF and other documents using Docling."""
    
    def __init__(self, enable_ocr: bool = True):
        self.enable_ocr = enable_ocr
        self._converter: Optional[DocumentConverter] = None
    
    @property
    def converter(self) -> DocumentConverter:
        if self._converter is None:
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = self.enable_ocr
            pipeline_options.do_table_structure = True
            
            self._converter = DocumentConverter(
                allowed_formats=[
                    InputFormat.PDF,
                    InputFormat.IMAGE,
                    InputFormat.DOCX,
                    InputFormat.PPTX,
                    InputFormat.HTML,
                ],
                format_options={
                    InputFormat.PDF: pipeline_options
                }
            )
        return self._converter
    
    async def extract(
        self,
        file_path: Path,
        output_dir: Optional[Path] = None,
        extract_images: bool = True
    ) -> ExtractionResult:
        """
        Extract content from a document.
        
        Args:
            file_path: Path to the document
            output_dir: Directory to save extracted images
            extract_images: Whether to extract images
            
        Returns:
            ExtractionResult with all extracted content
        """
        # Run Docling conversion in thread pool (CPU-bound)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._convert_sync,
            file_path,
            output_dir,
            extract_images
        )
        return result
    
    def _convert_sync(
        self,
        file_path: Path,
        output_dir: Optional[Path],
        extract_images: bool
    ) -> ExtractionResult:
        """Synchronous conversion (runs in thread pool)."""
        # Convert document
        conversion_result = self.converter.convert(str(file_path))
        doc = conversion_result.document
        
        # Export to different formats
        markdown = doc.export_to_markdown()
        text = doc.export_to_text()
        
        # Extract tables
        tables = []
        for i, table in enumerate(doc.tables):
            tables.append(ExtractedTable(
                index=i,
                page=table.prov[0].page_no if table.prov else 0,
                markdown=table.export_to_markdown(),
                csv=table.export_to_dataframe().to_csv(index=False) if hasattr(table, 'export_to_dataframe') else None
            ))
        
        # Extract images if requested
        images = []
        if extract_images and output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            for i, picture in enumerate(doc.pictures):
                if picture.image:
                    img_path = output_dir / f"image_{i:03d}.png"
                    picture.image.save(str(img_path))
                    images.append(ExtractedImage(
                        index=i,
                        page=picture.prov[0].page_no if picture.prov else 0,
                        path=str(img_path),
                        caption=picture.caption if hasattr(picture, 'caption') else None
                    ))
        
        # Extract headings/structure
        headings = []
        for item in doc.document_items:
            if hasattr(item, 'label') and 'heading' in item.label.lower():
                headings.append({
                    "level": 1,  # Simplified
                    "text": item.text if hasattr(item, 'text') else str(item),
                    "page": item.prov[0].page_no if hasattr(item, 'prov') and item.prov else 0
                })
        
        # Get metadata
        title = doc.title if hasattr(doc, 'title') else None
        author = doc.author if hasattr(doc, 'author') else None
        
        return ExtractionResult(
            filename=file_path.name,
            num_pages=len(doc.pages) if hasattr(doc, 'pages') else 0,
            markdown=markdown,
            text=text,
            tables=tables,
            images=images,
            title=title,
            author=author,
            language=None,  # Could add detection
            headings=headings
        )


# Singleton extractor
_extractor: Optional[DocumentExtractor] = None


def get_extractor() -> DocumentExtractor:
    global _extractor
    if _extractor is None:
        _extractor = DocumentExtractor(enable_ocr=settings.enable_ocr)
    return _extractor
