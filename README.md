# CareerForge RAG — Strict Assistant (knowledge base only)

A command-line assistant that answers career questions **only** from a small
knowledge base of PDF documents, with page-level citations. If a question is
outside the documents, it says so instead of guessing.

This project is a faithful migration of the Jupyter/Colab notebook
`CareerForge_RAG_Strict.ipynb`. The RAG logic, prompts, models, and settings are
unchanged; the only intentional infrastructure change is that PDFs now come from
a local folder instead of Google Drive.

## What it does (pipeline)

```
PDFs (data/pdfs/) -> pdfplumber extraction -> cleaning -> structure-aware chunking
  -> embeddings (BAAI/bge-small-en-v1.5) -> ChromaDB (data/chroma_db/)
  -> vector retrieval (top_k = 3) -> query rewriting for follow-ups
  -> prompt -> LLM (openai/gpt-4o-mini via OpenRouter, temperature 0) -> answer + citation check
```

## Project structure

```
careerforge_rag/
├── data/
│   ├── pdfs/              <- PUT YOUR PDF FILES HERE
│   └── chroma_db/         <- created automatically (vector database)
├── src/
│   ├── config.py          <- paths, .env loading, model name, top_k
│   ├── ingestion/         <- schema.py, block_parser.py, pdf_extractor.py
│   ├── processing/        <- cleaner.py, chunker.py
│   ├── embeddings/        <- embedder.py
│   ├── vectorstore/       <- chroma_store.py
│   ├── retrieval/         <- vector_retriever.py
│   ├── citations/         <- citation_checker.py
│   └── generation/        <- prompts.py, generator.py, query_rewriter.py, conversation.py
├── main.py                <- entry point
├── requirements.txt
├── .env.example           <- template for your API key
├── .env                   <- your real API key (not committed)
└── README.md
```

## Requirements

* Windows + Visual Studio Code
* **Python 3.10, 3.11 or 3.12** (the notebook pins `Pillow==10.4.0`, which has no
  wheels for Python 3.13+)
* An OpenRouter API key (https://openrouter.ai)
* Internet on the first run (downloads the embedding model, about 130 MB, once)

## Setup (PowerShell, from the project folder)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

If PowerShell refuses to activate the environment, run this once and try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

In VS Code: press `Ctrl+Shift+P` -> **Python: Select Interpreter** -> choose the
`.venv` one.

## API key

Open the `.env` file and replace the placeholder:

```
OPENROUTER_API_KEY=your_real_key_here
```

(This is the same secret name the notebook read from Colab Secrets.)

## Add your PDFs

Copy your 7 PDF files into `data/pdfs/`. Any file ending in `.pdf` in that folder
is used; filenames don't matter.

## Run

```powershell
python main.py
```

What happens, in order (this mirrors the notebook cell by cell):

1. Every PDF is extracted; a table of documents/pages/blocks is printed.
2. Text is cleaned and chunked; the chunk count is printed.
3. Chunks are embedded and the ChromaDB collection is **rebuilt from scratch**
   (the notebook does this on every run too).
4. A retrieval check prints the top 3 chunks for "what is the STAR method?".
5. An automated demo asks one in-scope and one out-of-scope question.
6. An interactive prompt (`You:`) opens. Type a question; type `exit`, `quit`,
   or press Enter on an empty line to stop. Follow-up questions work.
7. A short transcript of the session is printed.

## Expected behavior

* In-scope questions get a conversational answer with citations like
  `[Source: <document title>, Page 3]`, followed by a line such as
  `(1 citation(s) -- all citations valid)`.
* Out-of-scope questions get a plain "I don't see anything in the knowledge base
  about that"-style reply.

## Troubleshooting

| Message / symptom | Fix |
|---|---|
| `ERROR: OPENROUTER_API_KEY is not set` | Put your key in `.env` (see above). |
| `ERROR: No PDF files found in ...data\pdfs` | Copy the PDFs into `data/pdfs/`. |
| `ModuleNotFoundError` | Activate the venv (`.venv\Scripts\activate`) and re-run `pip install -r requirements.txt`. |
| `pip` fails building Pillow | You are probably on Python 3.13+. Install Python 3.11 or 3.12. |
| Warning about symlinks / `HF_HUB_DISABLE_SYMLINKS_WARNING` | Harmless on Windows; the model still downloads and works. |
| First run is slow | The embedding model is being downloaded (once). |
| Log lines like "Failed to extract page N" | Same behavior as the notebook: a bad page is skipped, the rest continues. |
| 401 / authentication error from the LLM call | The API key is wrong or has no credit. |

## How the notebook maps to this project

| Notebook cell(s) | Responsibility | Python location |
|---|---|---|
| 2 (Drive mount, `PROJECT_ROOT`) | Colab-only setup | Removed; `src/config.py` + `main.py` resolve paths from the file location |
| 3 (folders, `__init__.py`) | Folder structure | The `src/<package>/` folders and `data/` |
| 4 (`!pip install`) | Dependencies | `requirements.txt` |
| 6 `schema.py` | Data model | `src/ingestion/schema.py` (unchanged) |
| 7 `block_parser.py` | Heading/bullet/prose parsing | `src/ingestion/block_parser.py` (unchanged) |
| 8 `pdf_extractor.py` | pdfplumber extraction | `src/ingestion/pdf_extractor.py` (unchanged) |
| 10 | Extraction sanity check | `main.py` -> `build_index()` (reads `data/pdfs/`) |
| 12 `cleaner.py` | Cleaning | `src/processing/cleaner.py` (unchanged) |
| 13 `chunker.py` | Chunking | `src/processing/chunker.py` (unchanged) |
| 14 | Clean + chunk | `main.py` -> `build_index()` |
| 16 `embedder.py` | Embeddings | `src/embeddings/embedder.py` (unchanged) |
| 17 `chroma_store.py` | Vector store | `src/vectorstore/chroma_store.py` (unchanged) |
| 18 | Embed + store (reset, add) | `main.py` -> `build_index()` |
| 20 `vector_retriever.py` | Retrieval | `src/retrieval/vector_retriever.py` (unchanged) |
| 21 `citation_checker.py` | Citation verification | `src/citations/citation_checker.py` (unchanged) |
| 22 | Retrieval smoke test | `main.py` -> `main()` |
| 24 `prompts.py` | System/user prompts | `src/generation/prompts.py` (unchanged) |
| 25 `generator.py` | LLM call (OpenRouter) | `src/generation/generator.py` (unchanged) |
| 26 `query_rewriter.py` | Follow-up rewriting | `src/generation/query_rewriter.py` (unchanged) |
| 27 (Colab Secrets key) | API key | `.env` -> `src/config.py::load_api_key()` |
| 29 `conversation.py` | Orchestration + history | `src/generation/conversation.py` (unchanged) |
| 30 | Create `Conversation(top_k=3)` | `main.py` -> `main()` |
| 32 | Demo questions + `print_turn` | `main.py` -> `run_demo()`, `print_turn()` |
| 34 | Interactive loop | `main.py` -> `run_interactive()` |
| 36 | Transcript | `main.py` -> `print_transcript()` |

The notebook's `del sys.modules[...]` reload cells were Jupyter-only and are not needed.
