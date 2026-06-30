# DocQA

Local document Q&A powered by retrieval-augmented generation. Upload PDFs, DOCX, or text files and ask questions — answers are grounded in your documents with source references.

## Key Features

- **Document Summary**: On upload, the app automatically generates a compact overview of your document using the LLM (falling back to an extractive snippet if offline).
- **Conversational Memory**: Supports follow-up questions naturally during chat sessions.
- **Robust Offline Fallback**: If the local LLM is unreachable, the app remains fully functional, falling back to presenting raw vector-retrieved matching text blocks directly.
- **Source Citations**: Answers include a context preview of document sources and page locations.

## Architecture

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│  Upload  │────▶│ Chunker  │────▶│  Embeddings  │────▶│ ChromaDB │
└──────────┘     └──────────┘     └──────────────┘     └──────────┘
                                                             │
┌──────────┐     ┌───────────┐    ┌──────────────┐          │
│ Question │────▶│ Retriever │◀───│ Vector Search│◀─────────┘
└──────────┘     └───────────┘    └──────────────┘
                       │
                       ▼
                 ┌───────────┐
                 │ Generator │──▶ Grounded Answer + Context Preview
                 │ (Ollama)  │
                 └───────────┘
```

**Upload pipeline:** File → parse (PDF/DOCX/TXT) → chunk (recursive text splitter) → embed (sentence-transformers) → store (ChromaDB) & generate document summary.

**Query pipeline:** Question (with chat history) → check summary request → embed → vector search → top-k context → LLM prompt → grounded answer with source citations.

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) running locally with a model pulled

```bash
# Pull the default local LLM model
ollama pull llama3.2
```

### Setup

```bash
# Clone and enter the project
git clone <repo-url> && cd LLM_QA

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Copy env config
cp .env.example .env
```

### Editor & Import Conventions

This repository has a `.vscode/settings.json` workspace file to automatically configure Python's interpreter path and include the `backend/` directory in Pyright extra paths, resolving linting diagnostics.

**Package Import Mappings:**
- **PyMuPDF**: Installed via `PyMuPDF` in `requirements.txt` but imported in Python as `import fitz`.
- **python-docx**: Installed via `python-docx` in `requirements.txt` but imported in Python as `import docx`.

### Run

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000)

### Troubleshooting

- **ChromaDB Telemetry warnings**: Silenced by default in `embeddings.py` by configuring `os.environ["ANONYMIZED_TELEMETRY"] = "False"` and setting log levels to `ERROR`.
- **Ollama is unreachable**: Ensure the Ollama app is launched on your desktop (`ollama serve`) and the default port `11434` is bound.
- **VS Code import warnings**: Ensure the workspace python interpreter is set to the project `.venv` virtualenv by pressing `Cmd + Shift + P` -> `Python: Select Interpreter` -> choose the interpreter pointing to `.venv`.

### Docker

```bash
# Make sure Ollama is running on the host
docker compose up --build
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload a document (multipart form) |
| `POST` | `/api/ask` | Ask a question (`{ "question": "...", "doc_id": null }`) |
| `GET` | `/api/documents` | List uploaded documents |
| `DELETE` | `/api/documents/{id}` | Remove a document |

### Example

```bash
# Upload
curl -X POST http://localhost:8000/api/upload \
  -F "file=@report.pdf"

# Ask
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key findings?"}'
```

## Configuration

All settings are in `.env`. See [.env.example](.env.example) for available options.

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `ollama` or `openai` |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model |
| `CHUNK_SIZE` | `512` | Characters per chunk |
| `TOP_K` | `5` | Number of chunks to retrieve |

## Tests

```bash
cd backend
python -m pytest tests/ -v
```

## Tech Stack

- **Backend:** FastAPI, Python 3.11
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **Vector store:** ChromaDB (persistent, local)
- **LLM:** Ollama (local) or OpenAI API
- **File parsing:** PyMuPDF, python-docx
- **Frontend:** Vanilla HTML/CSS/JS

## Project Structure

```
backend/
  app/
    main.py          # Routes and app setup
    config.py        # Settings from .env
    models.py        # Request/response schemas
    upload.py        # File parsing (PDF, DOCX, TXT)
    chunker.py       # Text splitting
    embeddings.py    # Embedding + ChromaDB storage
    retriever.py     # Vector search
    generator.py     # LLM answer generation
  tests/
frontend/
  index.html         # Single-page UI
  style.css          # Dark minimal theme
  app.js             # Client-side logic
```

## License

MIT
