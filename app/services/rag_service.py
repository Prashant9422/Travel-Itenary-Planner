"""Lightweight RAG pipeline over local travel CSVs and Markdown guides."""
from functools import lru_cache
from langchain_core.documents import Document
from app.config import DATA_DIR, CHROMA_DIR, EMBEDDING_MODEL
from app.services.data_service import display_source_name, is_synthetic_record, load_csv

@lru_cache(maxsize=1)
def get_vector_store():
    # Imports are delayed so users can still explore the app if embeddings are not installed yet.
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    docs: list[Document] = []
    for dataset in ("attractions", "hotels", "flights", "guides"):
        frame = load_csv(dataset)
        if not frame.empty and {"source", "notes"}.intersection(frame.columns):
            frame = frame[~frame.apply(is_synthetic_record, axis=1)]
        for _, row in frame.iterrows():
            content = " | ".join(f"{k}: {v}" for k, v in row.to_dict().items() if str(v).strip())
            docs.append(Document(page_content=content, metadata={"source": f"{dataset}.csv", "dataset": dataset}))
    for path in DATA_DIR.glob("*.md"):
        docs.append(Document(page_content=path.read_text(encoding="utf-8"), metadata={"source": path.name, "dataset": "guide"}))
    if not docs:
        raise RuntimeError("No RAG documents found in data/.")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return Chroma.from_documents(docs, embedding=embeddings, persist_directory=str(CHROMA_DIR),
                                 collection_name="travel_knowledge")

def retrieve_context(query: str, k: int = 5) -> tuple[str, list[dict]]:
    store = get_vector_store()
    docs = store.similarity_search(query, k=k)
    context = "\n\n".join(
        f"[Source: {display_source_name(d.metadata.get('source', 'unknown'))}] {d.page_content}"
        for d in docs
    )
    sources = [
        {
            "source": display_source_name(d.metadata.get("source", "unknown")),
            "content": d.page_content,
        }
        for d in docs
    ]
    return context, sources
