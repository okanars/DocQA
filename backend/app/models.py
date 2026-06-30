from pydantic import BaseModel


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunks: int
    message: str
    summary: str | None = None


class AskRequest(BaseModel):
    question: str
    doc_id: str | None = None
    history: list[dict] | None = None


class SourceChunk(BaseModel):
    text: str
    doc_id: str
    filename: str
    chunk_index: int
    score: float
    page: int | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    has_answer: bool
    raw_answer: str | None = None
    excerpts: list[dict] | None = None


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    chunks: int
    uploaded_at: str
    summary: str | None = None
