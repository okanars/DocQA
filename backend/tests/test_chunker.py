from app.chunker import chunk_text, chunk_pages


def test_basic_chunking():
    text = "Hello world. " * 50
    chunks = chunk_text(text, chunk_size=100, overlap=0)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 150  # allow some flexibility at boundaries


def test_empty_text():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_single_chunk():
    text = "Short text that fits in one chunk."
    chunks = chunk_text(text, chunk_size=512, overlap=0)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_paragraph_boundaries():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_text(text, chunk_size=100, overlap=0)
    assert len(chunks) >= 1
    combined = " ".join(chunks)
    assert "First paragraph" in combined
    assert "Third paragraph" in combined


def test_overlap_adds_context():
    text = "A" * 200 + "\n\n" + "B" * 200
    chunks = chunk_text(text, chunk_size=250, overlap=30)
    assert len(chunks) >= 2


def test_chunk_pages():
    pages = [
        {"text": "Page one content. " * 30, "page": 1},
        {"text": "Page two content. " * 30, "page": 2},
    ]
    results = chunk_pages(pages, chunk_size=100, overlap=0)
    assert len(results) > 2
    assert all("chunk_index" in r for r in results)
    assert any(r["page"] == 1 for r in results)
    assert any(r["page"] == 2 for r in results)

    indices = [r["chunk_index"] for r in results]
    assert indices == sorted(indices)


def test_very_long_paragraph():
    text = "word " * 500
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.strip()
