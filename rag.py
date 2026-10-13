"""
Core RAG pipeline for Uzhavar Nalan AI.

Flow:  question -> multilingual retriever (FAISS) -> prompt with context -> ChatOpenAI -> answer
Every call is traced in LangSmith (retrieval + generation grouped under one run).
"""

import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langsmith import Client, traceable
from langsmith.run_helpers import get_current_run_tree

load_dotenv()
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ settings
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = BASE_DIR / "vectorstore"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TOP_K = int(os.getenv("TOP_K", "5"))
HISTORY_TURNS = 6  # previous messages sent to the LLM for follow-up questions

TAMIL_CHARS = re.compile(r"[\u0B80-\u0BFF]")


def detect_language(text: str) -> str:
    """Return 'Tamil' if the text contains Tamil script, otherwise 'English'."""
    return "Tamil" if TAMIL_CHARS.search(text or "") else "English"


# ---------------------------------------------------------------- embeddings
class MultilingualEmbeddings(Embeddings):
    """HuggingFace embeddings with the 'query:' / 'passage:' prefixes E5 models expect."""

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model = HuggingFaceEmbeddings(
            model_name=model_name,
            encode_kwargs={"normalize_embeddings": True},
        )
        self.use_prefix = "e5" in model_name.lower()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.use_prefix:
            texts = [f"passage: {t}" for t in texts]
        return self.model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        if self.use_prefix:
            text = f"query: {text}"
        return self.model.embed_query(text)


def get_embeddings() -> Embeddings:
    return MultilingualEmbeddings(EMBEDDING_MODEL)


# -------------------------------------------------------------------- prompt
SYSTEM_PROMPT = """You are "Uzhavar Nalan AI" (உழவர் நலன் AI), a friendly and trustworthy assistant \
that helps farmers understand Tamil Nadu government agriculture schemes.

Rules:
1. Answer ONLY from the CONTEXT below. Never invent scheme names, amounts, dates or eligibility rules.
2. If the context does not contain the answer, say so politely and suggest contacting the nearest \
Agriculture Extension Centre / Assistant Director of Agriculture office, or the official TNAGRISNET portal.
3. Write the whole answer in {language}. Keep scheme names recognisable (add the other-language \
name in brackets when helpful). Use simple words a farmer can understand.
4. Format: one-line summary, then short bullet points under the headings that the context supports: \
Benefits, Eligibility, Documents required, How to apply.
5. Quote amounts, percentages and limits exactly as written in the context.
6. If the question is vague (no crop, district or land size), answer with what is available and \
end with ONE short follow-up question.

CONTEXT:
{context}"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)


def format_docs(docs) -> str:
    blocks = []
    for doc in docs:
        source = doc.metadata.get("source", "document")
        page = doc.metadata.get("page")
        label = f"{source}, page {page + 1}" if isinstance(page, int) else source
        blocks.append(f"[Source: {label}]\n{doc.page_content}")
    return "\n\n---\n\n".join(blocks)


def unique_sources(docs) -> list[str]:
    seen = []
    for doc in docs:
        source = doc.metadata.get("source", "document")
        page = doc.metadata.get("page")
        label = f"{source} (p. {page + 1})" if isinstance(page, int) else source
        if label not in seen:
            seen.append(label)
    return seen


def to_messages(history: list[dict]) -> list:
    """Convert UI chat history into LangChain messages (last few turns only)."""
    messages = []
    for msg in history[-HISTORY_TURNS:]:
        if msg.get("welcome"):
            continue
        cls = HumanMessage if msg["role"] == "user" else AIMessage
        messages.append(cls(content=msg["content"]))
    return messages


# ----------------------------------------------------------------- assistant
def load_vectorstore() -> FAISS:
    if not (INDEX_DIR / "index.faiss").exists():
        raise FileNotFoundError(
            "Vector index not found. Put your documents in ./data and run:  python ingest.py"
        )
    return FAISS.load_local(
        str(INDEX_DIR), get_embeddings(), allow_dangerous_deserialization=True
    )


class SchemeAssistant:
    """Retrieval-augmented assistant for Tamil Nadu agriculture schemes."""

    def __init__(self):
        if not os.getenv("OPENAI_API_KEY"):
            raise EnvironmentError("OPENAI_API_KEY is missing. Add it to your .env file.")
        self.retriever = load_vectorstore().as_retriever(
            search_type="mmr", search_kwargs={"k": TOP_K, "fetch_k": TOP_K * 4}
        )
        llm = ChatOpenAI(model=LLM_MODEL, temperature=0.2)
        self.chain = PROMPT | llm | StrOutputParser()

    @traceable(name="Uzhavar Nalan RAG", run_type="chain")
    def ask(self, question: str, history: list[dict] | None = None, language: str | None = None) -> dict:
        language = language or detect_language(question)
        docs = self.retriever.invoke(question)
        answer = self.chain.invoke(
            {
                "question": question,
                "context": format_docs(docs),
                "history": to_messages(history or []),
                "language": language,
            },
            config={"run_name": "Answer generation", "metadata": {"language": language}},
        )
        run = get_current_run_tree()
        return {
            "answer": answer,
            "sources": unique_sources(docs),
            "run_id": str(run.id) if run else None,
        }


def send_feedback(run_id: str | None, score: int) -> None:
    """Attach a thumbs up (1) / down (0) rating to the LangSmith trace."""
    if not run_id or not os.getenv("LANGSMITH_API_KEY"):
        return
    try:
        Client().create_feedback(run_id=run_id, key="user_rating", score=score)
    except Exception as exc:  # feedback must never break the chat
        logger.warning("Could not send LangSmith feedback: %s", exc)
