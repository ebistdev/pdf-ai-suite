# PDF AI Suite - Market Research & Technical Analysis
> Generated: 2026-02-16

## Executive Summary
Building an AI-powered PDF extraction tool that intelligently identifies and extracts:
- Tables (with structure preservation)
- Text (with paragraph/heading detection)
- Images, graphs, schematics
- Multi-language support
- Concise, itemized output

**Key Differentiator:** User-friendly interface + accurate structure detection + affordable pricing

---

## Competitive Landscape

### Open Source Tools

#### 1. Docling (IBM/LF AI Foundation)
- **URL:** https://github.com/docling-project/docling
- **License:** MIT
- **Strengths:**
  - Multiple formats: PDF, DOCX, PPTX, XLSX, HTML, images, LaTeX, audio
  - Advanced PDF understanding: layout, reading order, table structure, formulas
  - VLM support (GraniteDocling 258M model)
  - OCR for scanned PDFs
  - LangChain/LlamaIndex integrations
  - MCP server for agents
  - Local execution (air-gapped)
- **Weaknesses:**
  - Requires Python 3.10+
  - Learning curve for advanced features
  - CLI-focused, no native web UI
- **Coming Soon:** Metadata extraction, chart understanding, molecular structures

#### 2. Marker (Datalab/VikParuchuri)
- **URL:** https://github.com/datalab-to/marker
- **License:** GPL + Commercial (free for <$2M revenue/funding)
- **Strengths:**
  - PDF to Markdown/JSON/HTML/chunks
  - Tables, forms, equations, inline math, code blocks
  - Hybrid LLM mode for highest accuracy (Gemini integration)
  - 25 pages/sec on H100
  - Benchmarks favorably vs LlamasParse, Mathpix
- **Weaknesses:**
  - GPL license requires commercial license for serious use
  - GPU recommended for best performance
- **Pricing:** Hosted API at $0.25/100 pages (1/4 competitors)

#### 3. Unstructured
- **URL:** https://github.com/Unstructured-IO/unstructured
- **License:** Apache 2.0
- **Strengths:**
  - ETL pipeline focus for LLMs
  - Multiple formats: PDF, HTML, DOCX, images
  - Connectors for various data sources
  - Chunking and embedding support
- **Weaknesses:**
  - Heavy dependencies
  - Enterprise product push
  - Slower than alternatives

#### 4. PyMuPDF
- **URL:** https://pypi.org/project/PyMuPDF/
- **License:** AGPL + Commercial
- **Strengths:**
  - Very fast (C bindings via MuPDF)
  - Full PDF manipulation: extract, create, annotate
  - Mature, well-documented
  - v1.27.1 (Feb 2026)
- **Weaknesses:**
  - AGPL requires open-sourcing or commercial license
  - Lower-level API, more manual work
  - No AI/ML features built-in

### Commercial Solutions

| Product | Price | Features |
|---------|-------|----------|
| Mathpix | $10/mo (100 pages) | Best for math/LaTeX |
| LlamaParse | $0.003/page | RAG-optimized |
| Adobe PDF Services | $0.05/page | Enterprise-grade |
| Amazon Textract | $0.015/page | AWS integration |
| Google Document AI | $0.01/page | GCP integration |

---

## Technical Stack Decision

### Recommended: Docling + Custom Frontend

**Why:**
1. MIT license - no restrictions
2. Best structure detection (IBM research backing)
3. VLM support for complex documents
4. Multi-format out of the box
5. Active development (LF AI Foundation)

**Alternative: Marker for Markdown-focused**
- Better for clean markdown output
- Hybrid LLM mode is compelling
- But GPL licensing is restrictive

### Architecture

```
┌─────────────────────────────────────────────┐
│              Web UI (React/Svelte)          │
├─────────────────────────────────────────────┤
│              FastAPI Backend                │
├─────────────────────────────────────────────┤
│    ┌─────────────┐    ┌─────────────────┐   │
│    │   Docling   │    │  LLM Enhancer   │   │
│    │   Engine    │    │  (GPT-4/Claude) │   │
│    └─────────────┘    └─────────────────┘   │
├─────────────────────────────────────────────┤
│              File Storage (S3/Local)        │
└─────────────────────────────────────────────┘
```

---

## Our Differentiators

### 1. **Smart Structure Detection**
- Auto-detect document type (invoice, report, academic paper, form)
- Template-aware extraction

### 2. **Itemized Output**
- Concise bullet-point summaries
- Structured JSON for integration
- Human-readable reports

### 3. **Multi-Language First**
- OCR in 100+ languages
- Translation integration option

### 4. **Graph/Schematic AI**
- Vision model for diagram understanding
- Data extraction from charts
- Schematic component identification

### 5. **Simple Pricing**
- Free tier: 50 pages/month
- Pro: $15/mo for 500 pages
- Business: $49/mo for 3000 pages

---

## MVP Features (v0.1)

1. **Upload Interface**
   - Drag-drop PDF upload
   - URL input
   - Batch upload (ZIP)

2. **Extraction Options**
   - Tables → CSV/JSON
   - Text → Markdown (with headings)
   - Images → Separate files with captions
   - Full document → Structured JSON

3. **Output Formats**
   - Markdown
   - JSON (structured)
   - Plain text
   - HTML

4. **Basic Settings**
   - OCR on/off
   - Language selection
   - Output format preference

---

## Development Phases

### Phase 1: MVP (2 weeks)
- Single PDF upload
- Docling integration
- Basic extraction (tables, text, images)
- Markdown output
- Simple web UI

### Phase 2: Enhancement (2 weeks)
- Batch processing
- LLM enhancement option
- Multiple output formats
- API endpoints

### Phase 3: Polish (1 week)
- User accounts
- Usage tracking
- Stripe integration
- Landing page

---

## Tech Stack

| Component | Choice |
|-----------|--------|
| Backend | FastAPI (Python 3.11+) |
| PDF Engine | Docling |
| Frontend | SvelteKit |
| Database | PostgreSQL |
| Queue | Redis + Celery |
| Storage | S3-compatible |
| Auth | Supabase / Clerk |
| Payments | Stripe |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Docling accuracy issues | Fallback to PyMuPDF + custom logic |
| Large file handling | Async processing, page limits |
| GPU requirements | Start CPU-only, add GPU tier |
| Complex documents fail | LLM cleanup pass option |

---

## Revenue Model

### Target: $5K MRR in 6 months

- **Free:** 50 pages/mo (acquire users)
- **Pro ($15/mo):** 500 pages, priority processing
- **Business ($49/mo):** 3000 pages, API access, batch
- **Enterprise:** Custom pricing, on-prem option

### Customer Segments
1. Researchers/academics (papers → notes)
2. Legal/compliance (contract extraction)
3. Finance (invoice/receipt processing)
4. Developers (RAG pipeline prep)

---

## Next Steps

1. [x] Research complete
2. [ ] Initialize project structure
3. [ ] Set up Docling
4. [ ] Build basic upload → extract → download flow
5. [ ] Deploy MVP
6. [ ] Launch on Product Hunt / HN
