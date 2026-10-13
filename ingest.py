"""
Build the FAISS vector index from the documents in ./data

Supported formats: .pdf, .docx, .txt   (Tamil and English)
Usage:  python ingest.py
"""

import re

from langchain_community.document_loaders import Docx2txtLoader, PyMuPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag import DATA_DIR, EMBEDDING_MODEL, INDEX_DIR, detect_language, get_embeddings

LOADERS = {
    ".pdf": PyMuPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt": lambda path: TextLoader(path, encoding="utf-8"),
}


def clean(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_documents():
    files = sorted(p for p in DATA_DIR.glob("*") if p.suffix.lower() in LOADERS)
    if not files:
        raise SystemExit(f"No documents found in {DATA_DIR}. Add your PDF/DOCX/TXT files first.")

    documents = []
    for path in files:
        pages = LOADERS[path.suffix.lower()](str(path)).load()
        pages = [p for p in pages if p.page_content.strip()]
        for page in pages:
            page.page_content = clean(page.page_content)
            page.metadata["source"] = path.name
            page.metadata["language"] = detect_language(page.page_content)

        preview = " ".join(pages[0].page_content.split())[:90] if pages else "(no text found)"
        print(f"  ✔ {path.name}: {len(pages)} page(s)  |  {preview}")
        documents.extend(pages)
    return documents


def main():
    print(f"\n📂 Loading documents from {DATA_DIR}")
    documents = load_documents()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", "।", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print(f"\n✂  Split into {len(chunks)} chunks")

    print(f"🧠 Embedding with {EMBEDDING_MODEL} (first run downloads the model)...")
    vectorstore = FAISS.from_documents(chunks, get_embeddings())
    vectorstore.save_local(str(INDEX_DIR))
    print(f"✅ Index saved to {INDEX_DIR}\n   Now run:  streamlit run app.py\n")


if __name__ == "__main__":
    main()
