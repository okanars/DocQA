import os
import logging

os.environ["ANONYMIZED_TELEMETRY"] = "False"
logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)

import chromadb
from sentence_transformers import SentenceTransformer
from app.config import get_settings

_model = None
_client = None
_collection = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        settings = get_settings()
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        settings = get_settings()
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=chromadb.Settings(anonymized_telemetry=False)
        )
        _collection = _client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()


def store_chunks(doc_id: str, filename: str, chunks: list[dict]) -> int:
    collection = _get_collection()
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    ids = [f"{doc_id}_chunk_{c['chunk_index']}" for c in chunks]
    metadatas = [
        {
            "doc_id": doc_id,
            "filename": filename,
            "chunk_index": c["chunk_index"],
            "page": c.get("page", 1),
        }
        for c in chunks
    ]

    batch_size = 100
    for i in range(0, len(ids), batch_size):
        end = i + batch_size
        collection.add(
            ids=ids[i:end],
            embeddings=embeddings[i:end],
            documents=texts[i:end],
            metadatas=metadatas[i:end],
        )

    return len(ids)


def delete_document(doc_id: str):
    collection = _get_collection()
    results = collection.get(where={"doc_id": doc_id})
    if results["ids"]:
        collection.delete(ids=results["ids"])


def get_collection_stats() -> dict:
    collection = _get_collection()
    return {"count": collection.count()}
