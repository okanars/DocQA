import httpx
from app.config import get_settings

SYSTEM_PROMPT = """You are a helpful and concise document assistant.

Answer the user's question naturally, clearly, and directly based ONLY on the provided context.

Rules:
- Base your response strictly on the provided context. Do not make up facts or assume anything not mentioned.
- If the context does not mention the answer, state that briefly and naturally (e.g., "The document does not specify who the authors are" or "This information is not available in the document").
- Keep your tone conversational, professional, and concise. Avoid robotic formulas.
- Mention specific pages or section names when relevant to guide the user."""

NO_CONTEXT_ANSWER = "This information is not mentioned in the uploaded documents."


def _evaluate_has_answer(answer: str) -> bool:
    low = answer.lower()
    negatives = [
        "not mention", "not specify", "not contain", "not find", 
        "no information", "does not state", "not available", 
        "could not find", "does not say", "unavailable", 
        "unreachable", "offline", "connection issue"
    ]
    return not any(neg in low for neg in negatives)


class LLMConnectionError(Exception):
    """Custom exception raised when the LLM backend (Ollama or OpenAI) is unreachable or fails."""
    pass


async def generate_answer(question: str, context: str, history: list[dict] | None = None) -> dict:
    if not context.strip():
        return {"answer": NO_CONTEXT_ANSWER, "has_answer": False}

    settings = get_settings()

    try:
        if settings.llm_provider == "openai":
            return await _call_openai(question, context, history, settings)
        else:
            return await _call_ollama(question, context, history, settings)
    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        if settings.llm_provider == "openai":
            raise LLMConnectionError(
                "OpenAI API is unreachable. Please check your internet connection."
            ) from e
        else:
            raise LLMConnectionError(
                f"Ollama is unreachable at {settings.ollama_base_url}. "
                f"Please ensure Ollama is running (`ollama serve`) and that the '{settings.OLLAMA_MODEL}' model is pulled."
            ) from e
    except httpx.HTTPStatusError as e:
        raise LLMConnectionError(
            f"LLM backend returned an error status code: {e.response.status_code}. Detail: {e.response.text}"
        ) from e
    except Exception as e:
        raise LLMConnectionError(f"An unexpected error occurred while calling the LLM: {str(e)}") from e


async def generate_summary(text: str) -> str:
    settings = get_settings()
    prompt = (
        "Summarize the following document content naturally and concisely. "
        "Your output must consist of exactly: "
        "1. A single short summary paragraph (1-2 sentences).\n"
        "2. A bulleted list of 2 to 3 key points.\n"
        "Do not repeat the filename or use formulaic introductions."
    )
    sample_text = text[:4000]

    try:
        if settings.llm_provider == "openai":
            return await _generate_summary_openai(prompt, sample_text, settings)
        else:
            return await _generate_summary_ollama(prompt, sample_text, settings)
    except Exception as e:
        raise LLMConnectionError(f"Failed to generate summary: {str(e)}") from e


async def _call_ollama(question: str, context: str, history: list[dict] | None, settings) -> dict:
    url = f"{settings.ollama_base_url}/api/chat"
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for turn in history[-6:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"})

    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    answer = data["message"]["content"]
    has_answer = _evaluate_has_answer(answer)

    return {"answer": answer, "has_answer": has_answer}


async def _call_openai(question: str, context: str, history: list[dict] | None, settings) -> dict:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for turn in history[-6:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"})

    payload = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": 0.1,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    answer = data["choices"][0]["message"]["content"]
    has_answer = _evaluate_has_answer(answer)

    return {"answer": answer, "has_answer": has_answer}


async def _generate_summary_ollama(prompt: str, text: str, settings) -> str:
    url = f"{settings.ollama_base_url}/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "options": {
            "temperature": 0.3
        }
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    return data["message"]["content"].strip()


async def _generate_summary_openai(prompt: str, text: str, settings) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"].strip()
