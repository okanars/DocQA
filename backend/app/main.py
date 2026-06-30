import uuid
import json
import os
from datetime import datetime, timezone

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.models import UploadResponse, AskRequest, AskResponse, DocumentInfo, SourceChunk
from app.upload import parse_file, save_upload
from app.chunker import chunk_pages
from app.embeddings import store_chunks, delete_document
from app.retriever import retrieve, build_context
from app.generator import generate_answer, generate_summary, LLMConnectionError

app = FastAPI(title="DocQA", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
DOC_REGISTRY_PATH = "./data/documents.json"


def _load_registry() -> dict:
    if os.path.exists(DOC_REGISTRY_PATH):
        with open(DOC_REGISTRY_PATH, "r") as f:
            return json.load(f)
    return {}


def _save_registry(registry: dict):
    os.makedirs(os.path.dirname(DOC_REGISTRY_PATH), exist_ok=True)
    with open(DOC_REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)


def _is_summary_request(question: str) -> bool:
    q = question.lower()
    keywords = [
        "summary", "summarize", "overview", 
        "what is this document about", "what's this document about", 
        "about this document", "tell me about this"
    ]
    return any(kw in q for kw in keywords)


@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile):
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}. Use PDF, DOCX, or TXT.")

    settings = get_settings()
    content = await file.read()

    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(413, f"File too large. Max size: {settings.max_file_size_mb}MB")

    filepath = save_upload(content, file.filename, settings.upload_dir)

    try:
        pages = parse_file(filepath)
    except Exception as e:
        os.remove(filepath)
        raise HTTPException(422, f"Failed to parse file: {str(e)}")

    if not pages:
        os.remove(filepath)
        raise HTTPException(422, "No text content found in file")

    chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)

    doc_id = uuid.uuid4().hex[:12]
    count = store_chunks(doc_id, file.filename, chunks)

    # Generate document summary
    full_text = "\n".join(p["text"] for p in pages)
    try:
        summary = await generate_summary(full_text)
    except Exception:
        # Fallback to extractive text snippet
        clean_text = " ".join(full_text.split())
        summary = clean_text[:300]
        if len(clean_text) > 300:
            summary += "..."
        summary = f"[Extractive Fallback] {summary}"

    registry = _load_registry()
    registry[doc_id] = {
        "filename": file.filename,
        "chunks": count,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "filepath": filepath,
        "summary": summary,
    }
    _save_registry(registry)

    return UploadResponse(
        doc_id=doc_id,
        filename=file.filename,
        chunks=count,
        summary=summary,
        message=f"Uploaded and indexed {count} chunks",
    )


@app.post("/api/ask", response_model=AskResponse)
async def ask_question(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    registry = _load_registry()
    
    # Try routing summary requests directly to document summaries if applicable
    doc_id = req.doc_id
    if not doc_id and len(registry) == 1:
        doc_id = list(registry.keys())[0]

    if doc_id and _is_summary_request(req.question):
        doc_info = registry.get(doc_id)
        if doc_info and doc_info.get("summary"):
            return AskResponse(
                answer=f"**Document Summary for {doc_info['filename']}:**\n\n{doc_info['summary']}",
                sources=[],
                has_answer=True,
                raw_answer=doc_info["summary"],
            )

    chunks = retrieve(req.question, doc_id=req.doc_id)

    if not chunks:
        return AskResponse(
            answer="No documents have been uploaded yet, or no relevant content was found.",
            sources=[],
            has_answer=False,
            raw_answer="No documents have been uploaded yet, or no relevant content was found.",
            excerpts=[],
        )

    # Create the sources response
    sources = [
        SourceChunk(
            text=c["text"][:300],
            doc_id=c["doc_id"],
            filename=c["filename"],
            chunk_index=c["chunk_index"],
            score=c["score"],
            page=c.get("page", 1),
        )
        for c in chunks
    ]

    context = build_context(chunks)

    try:
        result = await generate_answer(req.question, context, req.history)
        raw_answer = result["answer"]
        has_answer = result["has_answer"]
        answer = raw_answer
    except Exception as e:
        # Graceful fallback when the LLM service is offline/unreachable
        error_msg = str(e)
        raw_answer = f"The LLM backend is offline/unreachable ({error_msg})."
        answer = (
            f"⚠️ **LLM Connection Issue**\n\n"
            f"The LLM backend is offline or unreachable ({error_msg}). "
            f"Please check the supporting excerpts below for document matching details."
        )
        has_answer = False

    excerpts = [
        {
            "filename": c["filename"],
            "page": c["page"],
            "text": c["text"],
            "chunk_index": c["chunk_index"],
        }
        for c in chunks
    ]

    return AskResponse(
        answer=answer,
        sources=sources,
        has_answer=has_answer,
        raw_answer=raw_answer,
        excerpts=excerpts,
    )


@app.get("/api/documents", response_model=list[DocumentInfo])
async def list_documents():
    registry = _load_registry()
    return [
        DocumentInfo(
            doc_id=doc_id,
            filename=info["filename"],
            chunks=info["chunks"],
            uploaded_at=info["uploaded_at"],
        )
        for doc_id, info in registry.items()
    ]


@app.delete("/api/documents/{doc_id}")
async def remove_document(doc_id: str):
    registry = _load_registry()
    if doc_id not in registry:
        raise HTTPException(404, "Document not found")

    filepath = registry[doc_id].get("filepath")
    if filepath and os.path.exists(filepath):
        os.remove(filepath)

    delete_document(doc_id)

    del registry[doc_id]
    _save_registry(registry)

    return {"message": "Document removed"}


frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.isdir(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))
