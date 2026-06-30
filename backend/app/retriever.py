from app.embeddings import embed_texts, _get_collection
from app.config import get_settings


def _is_metadata_query(query: str) -> bool:
    q = query.lower()
    keywords = [
        "author", "who wrote", "title", "publish", "written by", 
        "created by", "version", "date", "year", "creator"
    ]
    return any(kw in q for kw in keywords)


def normalize_query(query: str) -> str:
    q = query.strip().lower().rstrip("?").strip()
    mapping = {
        "author": "who wrote this document and who are the authors?",
        "authors": "who wrote this document and who are the authors?",
        "who wrote": "who wrote this document and who are the authors?",
        "who wrote this": "who wrote this document and who are the authors?",
        "title": "what is the title of the document?",
        "what is the title": "what is the title of the document?",
        "date": "when was this document published or written?",
        "published": "when was this document published or written?",
        "when was it published": "when was this document published or written?",
        "version": "what is the version or revision of this document?",
        "publisher": "who is the publisher of this document?",
        "summary": "can you summarize the document?",
        "about": "what is this document about?",
    }
    return mapping.get(q, query)


def retrieve_first_chunks(doc_id: str | None = None) -> list[dict]:
    collection = _get_collection()
    if collection.count() == 0:
        return []

    # Fallback-safe approach: get document chunks and filter manually to support
    # different versions of ChromaDB query schemas gracefully.
    if doc_id:
        results = collection.get(where={"doc_id": doc_id}, include=["documents", "metadatas"])
    else:
        results = collection.get(include=["documents", "metadatas"])

    chunks = []
    if results and "documents" in results and results["documents"]:
        for i in range(len(results["documents"])):
            meta = results["metadatas"][i]
            if meta.get("chunk_index") in (0, 1):
                chunks.append({
                    "text": results["documents"][i],
                    "doc_id": meta["doc_id"],
                    "filename": meta["filename"],
                    "chunk_index": meta["chunk_index"],
                    "page": meta.get("page", 1),
                    "score": 1.0,
                })
    chunks.sort(key=lambda c: c["chunk_index"])
    return chunks


def retrieve(query: str, doc_id: str | None = None, top_k: int | None = None) -> list[dict]:
    query = normalize_query(query)
    settings = get_settings()
    k = top_k or settings.top_k
    collection = _get_collection()

    if collection.count() == 0:
        return []

    query_embedding = embed_texts([query])[0]
    where_filter = {"doc_id": doc_id} if doc_id else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(k, collection.count()),
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    seen_keys = set()
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i]
        score = 1 - distance
        meta = results["metadatas"][0][i]
        key = (meta["doc_id"], meta["chunk_index"])
        seen_keys.add(key)

        chunks.append({
            "text": results["documents"][0][i],
            "doc_id": meta["doc_id"],
            "filename": meta["filename"],
            "chunk_index": meta["chunk_index"],
            "page": meta.get("page", 1),
            "score": round(score, 4),
        })

    if _is_metadata_query(query):
        first_chunks = retrieve_first_chunks(doc_id)
        prepend_chunks = []
        for fc in first_chunks:
            key = (fc["doc_id"], fc["chunk_index"])
            if key not in seen_keys:
                seen_keys.add(key)
                prepend_chunks.append(fc)
        chunks = prepend_chunks + chunks

    return chunks


def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = f"[Source {i}: {chunk['filename']}, page {chunk['page']}]"
        parts.append(f"{source}\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)
