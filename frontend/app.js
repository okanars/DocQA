const API = window.location.origin;

const elements = {
    dropZone: document.getElementById("drop-zone"),
    fileInput: document.getElementById("file-input"),
    uploadProgress: document.getElementById("upload-progress"),
    progressFill: document.getElementById("progress-fill"),
    progressText: document.getElementById("progress-text"),
    documentList: document.getElementById("document-list"),
    messages: document.getElementById("messages"),
    askForm: document.getElementById("ask-form"),
    questionInput: document.getElementById("question-input"),
    sendBtn: document.getElementById("send-btn"),
    sourcesPanel: document.getElementById("sources-panel"),
    sourcesList: document.getElementById("sources-list"),
    closeSources: document.getElementById("close-sources"),
};

let documents = [];
let conversationHistory = [];
let isProcessing = false;

// File upload

elements.dropZone.addEventListener("click", () => elements.fileInput.click());

elements.dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    elements.dropZone.classList.add("drag-over");
});

elements.dropZone.addEventListener("dragleave", () => {
    elements.dropZone.classList.remove("drag-over");
});

elements.dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    elements.dropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
});

elements.fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) uploadFile(file);
    e.target.value = "";
});

async function uploadFile(file) {
    const allowed = [".pdf", ".docx", ".txt"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!allowed.includes(ext)) {
        showError("Unsupported file type. Use PDF, DOCX, or TXT.");
        return;
    }

    elements.uploadProgress.hidden = false;
    elements.progressFill.style.width = "20%";
    elements.progressText.textContent = `Uploading ${file.name}...`;

    const form = new FormData();
    form.append("file", file);

    try {
        elements.progressFill.style.width = "50%";
        elements.progressText.textContent = "Processing...";

        const res = await fetch(`${API}/api/upload`, { method: "POST", body: form });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Upload failed");
        }

        elements.progressFill.style.width = "100%";
        elements.progressText.textContent = "Done";

        await loadDocuments();

        setTimeout(() => {
            elements.uploadProgress.hidden = true;
            elements.progressFill.style.width = "0%";
        }, 1500);
    } catch (err) {
        elements.uploadProgress.hidden = true;
        elements.progressFill.style.width = "0%";
        showError(err.message);
    }
}

// Documents

async function loadDocuments() {
    try {
        const res = await fetch(`${API}/api/documents`);
        documents = await res.json();
        renderDocuments();
    } catch {
        // Silently fail on initial load
    }
}

function renderDocuments() {
    if (documents.length === 0) {
        elements.documentList.innerHTML = '<p class="empty-state">No documents uploaded</p>';
        return;
    }

    elements.documentList.innerHTML = documents
        .map(
            (doc) => `
        <div class="doc-item" data-id="${doc.doc_id}">
            <div class="doc-info-block">
                <span class="doc-name" title="${doc.filename}">${doc.filename}</span>
                <span class="doc-meta">${doc.chunks} chunks</span>
                ${doc.summary ? `<p class="doc-summary-text" title="${escapeHtml(doc.summary)}">${escapeHtml(doc.summary)}</p>` : ''}
            </div>
            <button class="doc-delete" onclick="deleteDocument('${doc.doc_id}')" title="Remove">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
            </button>
        </div>
    `
        )
        .join("");
}

async function deleteDocument(docId) {
    try {
        await fetch(`${API}/api/documents/${docId}`, { method: "DELETE" });
        conversationHistory = [];
        await loadDocuments();
    } catch (err) {
        showError("Failed to delete document");
    }
}

// Chat

elements.askForm.addEventListener("submit", (e) => {
    e.preventDefault();
    sendQuestion();
});

elements.questionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendQuestion();
    }
});

elements.questionInput.addEventListener("input", () => {
    const el = elements.questionInput;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
});

async function sendQuestion() {
    const question = elements.questionInput.value.trim();
    if (!question || isProcessing) return;

    isProcessing = true;
    elements.sendBtn.disabled = true;

    clearWelcome();
    addMessage("user", question);
    elements.questionInput.value = "";
    elements.questionInput.style.height = "auto";

    const loadingId = addLoading();

    try {
        const res = await fetch(`${API}/api/ask`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, history: conversationHistory }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to get answer");
        }

        const data = await res.json();
        removeLoading(loadingId);
        addMessage("assistant", data.answer, data.sources, data.has_answer, data.excerpts);

        conversationHistory.push({ role: "user", content: question });
        conversationHistory.push({ role: "assistant", content: data.raw_answer || data.answer });
    } catch (err) {
        removeLoading(loadingId);
        addMessage("assistant", `Error: ${err.message}`, [], false);
    }

    isProcessing = false;
    elements.sendBtn.disabled = false;
    elements.questionInput.focus();
}

function clearWelcome() {
    const welcome = elements.messages.querySelector(".welcome-message");
    if (welcome) welcome.remove();
}

function addMessage(role, content, sources = [], hasAnswer = true, excerpts = []) {
    const div = document.createElement("div");
    div.className = `message message-${role}`;

    if (role === "user") {
        div.innerHTML = `<div class="message-content">${escapeHtml(content)}</div>`;
    } else {
        const answerClass = hasAnswer ? "" : "no-answer";
        let html = `<div class="message-content"><div class="${answerClass}">${formatAnswer(content)}</div>`;

        if (excerpts && excerpts.length > 0) {
            html += `
            <details class="supporting-excerpts-toggle">
                <summary>Show supporting excerpts</summary>
                <ul class="excerpts-list">
                    ${excerpts.slice(0, 3).map(e => `
                        <li>
                            <div class="excerpt-meta">
                                <strong>${escapeHtml(e.filename)}</strong> (Page ${e.page || 1}, Chunk #${e.chunk_index})
                            </div>
                            <blockquote class="excerpt-body">${escapeHtml(e.text)}</blockquote>
                        </li>
                    `).join("")}
                </ul>
            </details>
            `;
        }

        if (sources && sources.length > 0) {
            html += `<button class="sources-btn" onclick='showSources(${JSON.stringify(sources).replace(/'/g, "&#39;")})'>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                </svg>
                ${sources.length} source${sources.length > 1 ? "s" : ""}
            </button>`;
        }

        html += "</div>";
        div.innerHTML = html;
    }

    elements.messages.appendChild(div);
    elements.messages.scrollTop = elements.messages.scrollHeight;
}

let loadingCounter = 0;

function addLoading() {
    const id = `loading-${++loadingCounter}`;
    const div = document.createElement("div");
    div.className = "message message-assistant message-loading";
    div.id = id;
    div.innerHTML = `
        <div class="message-content">
            <div class="loading-dots">
                <span></span><span></span><span></span>
            </div>
            Thinking...
        </div>
    `;
    elements.messages.appendChild(div);
    elements.messages.scrollTop = elements.messages.scrollHeight;
    return id;
}

function removeLoading(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// Sources panel

function showSources(sources) {
    elements.sourcesPanel.hidden = false;
    elements.sourcesList.innerHTML = sources
        .map(
            (s) => `
        <div class="source-card">
            <div class="source-card-header">
                <span class="source-filename">${escapeHtml(s.filename)}</span>
                <span class="source-score">${(s.score * 100).toFixed(0)}% match</span>
            </div>
            <div class="source-card-meta" style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px;">
                <span>Page ${s.page || 1}</span> • <span>Chunk Reference: #${s.chunk_index}</span>
            </div>
            <div class="source-text" style="font-size: 12px; color: var(--text-secondary); line-height: 1.5; background: var(--bg-primary); padding: 8px; border-radius: 4px; white-space: pre-wrap;">${escapeHtml(s.text)}</div>
        </div>
    `
        )
        .join("");
}

elements.closeSources.addEventListener("click", () => {
    elements.sourcesPanel.hidden = true;
});

// Helpers

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function formatAnswer(text) {
    return escapeHtml(text)
        .replace(/\n\n/g, "</p><p>")
        .replace(/\n/g, "<br>")
        .replace(/^/, "<p>")
        .replace(/$/, "</p>");
}

function showError(message) {
    const toast = document.createElement("div");
    toast.className = "error-toast";
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// Make deleteDocument available globally
window.deleteDocument = deleteDocument;
window.showSources = showSources;

// Init
loadDocuments();
