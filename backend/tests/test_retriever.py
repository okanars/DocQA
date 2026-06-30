from app.retriever import build_context


def test_build_context_formatting():
    chunks = [
        {"text": "First chunk content.", "filename": "doc.pdf", "page": 1,
         "doc_id": "abc", "chunk_index": 0, "score": 0.9},
        {"text": "Second chunk content.", "filename": "doc.pdf", "page": 2,
         "doc_id": "abc", "chunk_index": 1, "score": 0.8},
    ]

    context = build_context(chunks)

    assert "[Source 1: doc.pdf, page 1]" in context
    assert "[Source 2: doc.pdf, page 2]" in context
    assert "First chunk content." in context
    assert "Second chunk content." in context
    assert "---" in context


def test_build_context_single_chunk():
    chunks = [
        {"text": "Only chunk.", "filename": "file.txt", "page": 1,
         "doc_id": "xyz", "chunk_index": 0, "score": 0.95},
    ]

    context = build_context(chunks)

    assert "[Source 1: file.txt, page 1]" in context
    assert "Only chunk." in context
    assert "---" not in context


def test_build_context_empty():
    context = build_context([])
    assert context == ""
