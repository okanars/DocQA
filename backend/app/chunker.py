def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    if not text or not text.strip():
        return []

    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) + 1 <= chunk_size:
            current = f"{current}\n{para}".strip() if current else para
        else:
            if current:
                chunks.append(current)

            if len(para) <= chunk_size:
                current = para
            else:
                sub_chunks = _split_long_text(para, chunk_size, overlap)
                chunks.extend(sub_chunks[:-1])
                current = sub_chunks[-1] if sub_chunks else ""

    if current.strip():
        chunks.append(current)

    if overlap > 0 and len(chunks) > 1:
        chunks = _add_overlap(chunks, overlap)

    return chunks


def _split_long_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    separators = [". ", "! ", "? ", "; ", ", ", " "]
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            chunks.append(text[start:].strip())
            break

        split_at = end
        for sep in separators:
            pos = text.rfind(sep, start, end)
            if pos > start:
                split_at = pos + len(sep)
                break

        chunk = text[start:split_at].strip()
        if chunk:
            chunks.append(chunk)

        start = max(split_at - overlap, start + 1)

    return chunks


def _add_overlap(chunks: list[str], overlap: int) -> list[str]:
    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tail = chunks[i - 1][-overlap:]
        current = chunks[i]
        if not current.startswith(prev_tail):
            result.append(prev_tail + " " + current)
        else:
            result.append(current)
    return result


def chunk_pages(pages: list[dict], chunk_size: int = 512, overlap: int = 50) -> list[dict]:
    results = []
    chunk_index = 0

    for page_data in pages:
        text = page_data["text"]
        page = page_data.get("page", 1)
        chunks = chunk_text(text, chunk_size, overlap)

        for chunk in chunks:
            results.append({
                "text": chunk,
                "page": page,
                "chunk_index": chunk_index,
            })
            chunk_index += 1

    return results
