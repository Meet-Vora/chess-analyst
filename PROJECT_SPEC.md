# 🧠 Chess Analyst - Technical Specification

This document outlines the internal system architecture, data flow, and specific technical choices powering the Chess Analyst CLI pipeline. 

## 1. Project Architecture

The application is an Extract-Transform-Load (ETL) pipeline coupled with a Retrieval-Augmented Generation (RAG) querying engine. It is intentionally modularized to decouple free local parsing from paid API inference processing.

### Tech Stack
- **Language**: Python 3.12+ (Managed via `uv` package manager)
- **CLI Framework**: `click` and `rich` for command routing and stylized terminal output.
- **Relational Data**: Local `sqlite3` for tracking ingested game IDs to prevent redundant parsing.
- **Vector Search Engine**: `ChromaDB` running completely locally (no cloud clusters).
- **Core ML Provider**: Google's `google-genai` Python SDK.
  - **Inference Model**: `gemini-2.5-flash` (used due to massive context window and fast structured JSON generation).
  - **Embedding Engine**: `gemini-embedding-001` (3072-dimensional vector projections).

---

## 2. Ingestion Pipeline (`parser.py` & `db.py`)
**Command**: `uv run chess-analyst ingest`

### The Mechanism
1. The user provides a path to a raw `.pgn` file containing one or more chess games (typically an archive exported from Chess.com or Lichess).
2. The `python-chess` library steps through the string, extracting critical header metadata: `[White]`, `[Black]`, `[Result]`, `[ECO]`, `[Opening]`, and raw PGN `moves`.
3. A unique cryptographic `game_id` is created (hash of the headers) to prevent duplicate ingestions if the user downloads overlapping archives.
4. The raw string data is securely committed to the local SQLite database (`data/games.db`) marking `is_analyzed = False`.

---

## 3. Analysis Engine (`analyzer.py`)
**Command**: `uv run chess-analyst analyze --limit 10`

### The Mechanism
This is the core ETL transformation phase. It bridges the local SQLite row with the LLM API.
1. The system queries `games.db` for up to `--limit` games where `is_analyzed=0`.
2. A stringent prompt is constructed containing the raw PGN move text.
3. The prompt is passed to `gemini-2.5-flash` using a strict **Pydantic Response Schema (`GameReview`)**. This absolutely guarantees the LLM responds in parseable JSON lacking hallucinated structures.
4. The system operates at `temperature=0.2`. Because chess analysis is a highly objective, logical task, low creativity drastically reduces hallucination on complex tactical strings.
5. The parsed JSON object is saved directly back into SQLite, and `is_analyzed` is flipped to `True`.

---

## 4. Vector Embedding Mapping (`vectordb.py`)

### The Mechanism
Immediately following the successful AI JSON generation in `analyzer.py`, the tactical findings must be mapped for semantic retrieval.
1. The tactical arrays (`mistakes`, `patterns_identified`, `critical_moments`, `tactical_motifs_missed`) are joined into a massive raw string blob representing that phase (e.g. Middlegame).
2. The string is dispatched to the `gemini-embedding-001` endpoint via the generic `EmbeddingFunction` callback hook. *(Note: Batched array uploads are looped iteratively to respect Google SDK payload requirements).*
3. The generated 3072-dimension float array is passed back to `ChromaDB`.
4. It is committed into the local cache (`data/chroma/`) alongside metadata tagging its specific `game_id` and Opening name, which allows for downstream filtering.

---

## 5. RAG Synthesis Engine (`retriever.py`)
**Command**: `uv run chess-analyst query "question"`

### The Mechanism
1. A user poses a plain English question about their playstyle.
2. The question is embedded natively against `gemini-embedding-001` to map it into the exact same 3072d vector space.
3. ChromaDB executes a cosine-similarity search (`vector cross product vs magnitudes`) to rip the 5 closest match embedding clusters out of the local database.
4. These closest 5 game phases are concatenated contextually and handed back fresh to `gemini-2.5-flash`.
5. Gemini reads the raw context, reasons over the specifically requested habits, and prints the synthesized advice array back out as a unified playbook strategy visually rendered via Python `rich` components. 
