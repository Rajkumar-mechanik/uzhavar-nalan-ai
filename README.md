# 🌾 உழவர் நலன் AI | Uzhavar Nalan AI

A bilingual (Tamil + English) RAG chatbot that helps farmers understand **Tamil Nadu government agriculture schemes** — subsidies, crop insurance, loans, irrigation support, eligibility, documents and how to apply.

| Layer | Technology |
|---|---|
| UI | Streamlit |
| RAG orchestration | LangChain |
| Embeddings | HuggingFace `intfloat/multilingual-e5-base` (Tamil + English) |
| Vector DB | FAISS |
| LLM | OpenAI `gpt-4o-mini` via `ChatOpenAI` |
| Monitoring | LangSmith (traces + 👍/👎 user feedback) |

---

## 1. Project structure

```
uzhavar-nalan-ai/
├── app.py              # Streamlit UI
├── rag.py              # Retriever + prompt + LLM chain (traced in LangSmith)
├── ingest.py           # Builds the FAISS index from ./data
├── chat_store.py       # Saves / loads chat history (JSON files in ./chats)
├── styles.css          # Theme (green / cream / gold)
├── requirements.txt
├── .env.example        # Copy to .env and add your keys
├── data/               # ← put your 4 scheme PDFs here
├── assets/             # optional: logo.png, background.jpg
└── vectorstore/        # created by ingest.py
```

## 2. Prerequisites

- Python **3.10 – 3.14**
- An OpenAI API key and a LangSmith API key (free tier at https://smith.langchain.com)
- ~2 GB free disk space (the embedding model is downloaded once, ~1.1 GB)

## 3. Create a virtual environment

**Windows (PowerShell)**
```powershell
cd uzhavar-nalan-ai
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
cd uzhavar-nalan-ai
python3 -m venv .venv
source .venv/bin/activate
```

## 4. Install the packages

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Add your API keys

Copy the example file and edit it:

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=uzhavar-nalan-ai
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

## 6. Add documents and build the index

Put your Tamil and English documents (`.pdf`, `.docx`, `.txt`) into `data/`, then run:

```bash
python ingest.py
```

It prints a short text preview of each file — **check the Tamil preview is readable**. Re-run this command whenever you change the documents.

## 7. Launch the app

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## 8. Monitoring with LangSmith

Open https://smith.langchain.com → project **uzhavar-nalan-ai**. Every question shows one trace with:
- the retrieved chunks (retriever step),
- the exact prompt and answer (LLM step), token usage and latency,
- the answer language in metadata,
- user 👍/👎 ratings as `user_rating` feedback.

---

## Features

- Ask in **Tamil or English**; the answer comes back in the same language (or force தமிழ் / English from the top bar).
- **Source citations** (file + page) under every answer.
- One-click **Farmer Assistance** cards and **Quick Questions**.
- Follow-up questions keep the recent conversation context.
- **➕ New chat**, **🧹 Clear chat** and **🕘 History**: every conversation is auto-saved to `chats/` and can be searched and reopened, even after a page refresh. *(History is shared by everyone using the same running app — fine for a local demo; add login before a public deployment.)*
- **A- / A / A+** text size for accessibility.
- Grounded answers only — the bot says so when the documents don't cover a question.

## Customise the look

- `assets/logo.png` → replaces the 🌾 logo.
- `assets/background.jpg` → paddy-field background (e.g. a cropped version of the design image).

## Troubleshooting

| Problem | Fix |
|---|---|
| `Vector index not found` | Run `python ingest.py` first. |
| Tamil preview looks like garbled symbols | The PDF uses a legacy (non-Unicode) Tamil font. Re-export it as a Unicode PDF/DOCX, or OCR it, then re-ingest. |
| First run is slow | The embedding model is downloading once. For a lighter model set `EMBEDDING_MODEL=intfloat/multilingual-e5-small` and re-run `ingest.py`. |
| `faiss-cpu` install fails | Use Python 3.10–3.12 and upgrade pip. |
| No traces in LangSmith | Check `LANGSMITH_TRACING=true` and the API key in `.env`, then restart Streamlit. |
