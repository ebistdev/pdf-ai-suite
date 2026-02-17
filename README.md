# PDF AI Suite 📄🤖

AI-powered PDF extraction that actually works. Extract tables, text, images, and structure from any PDF.

## Features

- 🗂️ **Smart Extraction**: Tables → CSV, Text → Markdown, Images → Files
- 📐 **Structure Detection**: Headings, paragraphs, lists preserved
- 🌍 **Multi-Language**: OCR in 100+ languages
- 📊 **Graph Understanding**: Extract data from charts and diagrams
- ⚡ **Fast**: Process documents in seconds, not minutes

## Quick Start

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Tech Stack

- **Backend**: FastAPI + Docling + Celery
- **Frontend**: SvelteKit
- **Database**: PostgreSQL + Redis

## License

MIT
