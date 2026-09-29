"""
CareerForge RAG -- Strict Assistant (knowledge base only).

Command-line entry point. Runs the same sequence as the original
notebook, top to bottom:

  1. extract every PDF in data/pdfs/          (notebook cell 10)
  2. clean + chunk                            (cell 14)
  3. embed + rebuild the ChromaDB collection  (cell 18)
  4. retrieval smoke test                     (cell 22)
  5. create the generator + conversation      (cells 27, 30)
  6. automated in-scope / out-of-scope demo   (cells 32)
  7. interactive question loop                (cell 34)
  8. transcript of the session                (cell 36)

Run with:  python main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Notebook Section 0: PROJECT_ROOT/src was inserted into sys.path so modules
# import as `ingestion.*`, `processing.*`, etc. Same thing here, but based on
# this file's location rather than the current working directory.
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Windows consoles often default to a legacy code page; answers may contain
# characters such as bullets or dashes. Output-encoding only -- no effect on
# what is generated.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

from config import (  # noqa: E402
    CHROMA_DIR,
    LLM_MODEL,
    PDF_DIR,
    TOP_K,
    ConfigError,
    ensure_pdf_directory,
    load_api_key,
)
from ingestion.pdf_extractor import extract_pdf_directory  # noqa: E402
from processing.cleaner import clean_document  # noqa: E402
from processing.chunker import chunk_documents  # noqa: E402
from embeddings.embedder import Embedder  # noqa: E402
from vectorstore.chroma_store import ChromaStore  # noqa: E402
from retrieval.vector_retriever import VectorRetriever  # noqa: E402
from generation.generator import Generator  # noqa: E402
from generation.conversation import Conversation  # noqa: E402

# Notebook cell 32
DEMO_QUESTIONS = [
    "What is the STAR method?",                 # in-scope
    "What is the capital of France?",             # out-of-scope -- should be declined
]


def build_index():
    """Notebook cells 10, 14, 18: extract -> clean -> chunk -> embed -> store."""
    pdf_dir_files = ensure_pdf_directory()
    print(f"Found {len(pdf_dir_files)} PDF file(s) in data/pdfs/")

    # --- cell 10: extraction ---
    docs_raw = extract_pdf_directory(PDF_DIR)

    print(f"{'doc_id':45s} {'title':40s} {'pages':>6s} {'blocks':>7s}")
    print("-" * 100)
    for doc in docs_raw:
        print(f"{doc.metadata.doc_id:45s} {doc.metadata.title[:40]:40s} "
              f"{doc.metadata.num_pages:>6d} {len(doc.blocks):>7d}")
    print(f"\nTotal documents extracted: {len(docs_raw)}")
    if not docs_raw:
        raise ConfigError("No document could be extracted from data/pdfs/ (see log messages above).")

    # --- cell 14: cleaning + chunking ---
    docs = [clean_document(d) for d in docs_raw]
    chunks = chunk_documents(docs)
    print(f"Total chunks: {len(chunks)}")

    # --- cell 18: embeddings + vector store (rebuilt from scratch every run) ---
    embedder = Embedder()
    vectors = embedder.embed_texts([c.text for c in chunks])
    print("Embeddings shape:", vectors.shape)

    store = ChromaStore(persist_dir=str(CHROMA_DIR))
    store.reset()
    store.add_chunks(chunks, vectors)
    print("Chunks stored in ChromaDB:", store.count())

    return embedder, store


def print_turn(turn) -> None:
    """Notebook cell 32."""
    print("A:", turn.answer)
    if turn.citation_checks:
        invalid = [c for c in turn.citation_checks if not c.is_valid]
        status = "all citations valid" if not invalid else f"{len(invalid)} INVALID citation(s)!"
        print(f"   ({len(turn.citation_checks)} citation(s) -- {status})")


def run_demo(conv: Conversation) -> None:
    """Notebook cell 32: automated in-scope vs. out-of-scope demo."""
    for q in DEMO_QUESTIONS:
        print("=" * 90)
        print("Q:", q)
        print("-" * 90)
        turn = conv.ask(q)
        print_turn(turn)
        print()


def run_interactive(conv: Conversation) -> None:
    """Notebook cell 34: interactive question loop."""
    conv.reset()  # start a clean conversation for this demo session

    print("CareerForge Assistant (knowledge-base only) -- type a question, or 'exit' to stop.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question or question.lower() in ("exit", "quit"):
            print("\nEnded.")
            break

        turn = conv.ask(question)
        print()
        print_turn(turn)
        print()


def print_transcript(conv: Conversation) -> None:
    """Notebook cell 36."""
    print(f"Total turns this session: {len(conv.turns)}\n")
    for i, t in enumerate(conv.turns, start=1):
        print(f"{i}. Q: {t.original_question}")
        print(f"   A: {t.answer[:150]}{'...' if len(t.answer) > 150 else ''}")
        print()


def main() -> int:
    try:
        api_key = load_api_key()  # fail early, before the slow embedding step
        embedder, store = build_index()
    except ConfigError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # --- cell 22: retrieval smoke test ---
    retriever = VectorRetriever(embedder=embedder, store=store)
    for r in retriever.retrieve("what is the STAR method?", top_k=3):
        print(f"[dist={r.distance:.3f}] {r.doc_id} -- {r.section_heading}")

    # --- cells 27, 30: generator + conversation ---
    generator = Generator(api_key=api_key, model=LLM_MODEL)
    print("Generator ready.")
    conv = Conversation(retriever=retriever, generator=generator, top_k=TOP_K)
    print("Conversation ready.")

    # --- cell 32, 34, 36 ---
    run_demo(conv)
    run_interactive(conv)
    print_transcript(conv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
