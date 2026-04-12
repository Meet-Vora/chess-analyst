# ♞ Chess Analyst

```text
      (\=,
     //  .\
    (( \_  \
     ))  `\_)
    (/     \
     | _.-'|
      )___(
     (=====)
    }======={
   /         \
  |___________|
```

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FF4F00?style=for-the-badge)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)
![Click](https://img.shields.io/badge/Click-000000?style=for-the-badge&logo=click&logoColor=white)
![Rich](https://img.shields.io/badge/Rich-000000?style=for-the-badge)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

Chess Analyst is a highly structured, locally-hosted 5-module ETL pipeline and RAG (Retrieval-Augmented Generation) query engine designed to extract deep analytical insights from historical chess data.

Rather than acting as a simple API wrapper, this project parses raw PGN files, enforces rigorous JSON schema validation on large language models (via `instructor` and `litellm`), generates high-dimensional vector embeddings, and synthesizes tactical patterns using a robust retrieval pipeline over ChromaDB with a cosine similarity search process. It effectively transforms thousands of forgotten, unstructured games into queryable, relational metadata stored in an idempotent SQLite framework, beautifully rendered locally in your terminal via a powerful `click` CLI.

---

## 🏗️ System Architecture

The pipeline securely handles data extraction, vector mapping, and semantic search locally, reaching out to your LLM of choice strictly for raw inference and embedding projections.

```mermaid
flowchart TD
    A[📄 PGN File] -->|Extract Moves & Metadata| B(⚙️ Parser<br/>python-chess)
    B -->|Idempotent Hashing| C[(🗄️ SQLite<br/>metadata storage)]
    C -->|Unanalyzed Games| D(🧠 Analyzer<br/>LiteLLM + Instructor schema enforcement)
    D -->|Structured Tactics| E(📏 Embeddings<br/>Dynamic Vector Embeddings)
    E -->|Store Vectors| F[(📊 ChromaDB<br/>vector store)]
    F -->|Cosine Similarity| G(🔍 RAG Query Engine<br/>semantic search + LLM synthesis)
```

### 🔑 Key Architectural Insights

- **Multi-Model Agnostic:** Powered by `litellm` and `instructor`, the system natively supports structured extraction across major providers (OpenAI, Anthropic, Google, xAI) decoupling your pipeline from vendor lock-in.
- **Pydantic Schema Enforcement:** The `analyzer` module forces the AI to respond strictly within a Pydantic-defined JSON schema. This ensures highly reliable downstream ETL parsing and eliminates hallucinated output structures.
- **Analytical Precision:** Inference operates at `temperature=0.2`. Because chess analysis is a highly objective, logical task, reducing the creativity parameter guarantees precision on complex tactical sequences.
- **Idempotent Data Ingestion:** The `parser` generates a unique cryptographic hash of each game's headers. This guarantees that duplicate or overlapping PGN histories can be ingested flawlessly without creating duplicate database records or wasting token inference limits.

---

## 🛠️ Tech Stack

This project is built intelligently atop powerful modern Python infrastructure:
- **Language**: Python 3.12+ (orchestrated via `uv`)
- **CLI Rendering**: `click` for command routing and `rich` for formatting engine.
- **Inference Stack**: `litellm` and `instructor` to bind Pydantic parsing natively across OpenAI, Anthropic, and Google architectures.
- **Data Layers**: Local `sqlite3` for fast relational hashes alongside a local `ChromaDB` deployment for dense vector search.
- **Verification**: Assured component logic via `pytest` operating heavily on mocked API interceptions.

---

## 💡 Example Output

Here's an example of the rich terminal rendering when querying the RAG engine against historically analyzed games:

```
Querying history for: can you tell me my blunders from all the games you analyzed so far


╭────────────────────────────────────────────── 🧠 AI Playstyle Analysis ──────────────────────────────────────────────╮
│ Based on the games analyzed so far, your blunders tend to fall into two main categories: direct tactical oversights  │
│ leading to immediate material loss and strategic missteps that severely compromise king safety, setting the stage    │
│ for later tactical collapses.                                                                                        │
│                                                                                                                      │
│ Here's a breakdown of your blunders:                                                                                 │
│                                                                                                                      │
│ Direct Tactical Blunders (Hanging Pieces & Miscalculations)                                                          │
│                                                                                                                      │
│  1 Game 9dace6c57af9c09a (Middlegame, Move 12. Qg4): This was a game-losing blunder where you moved your queen to    │
│    g4, leaving it completely undefended and allowing Black's bishop on e5 to capture it immediately. This is a       │
│    fundamental oversight of a hanging piece.                                                                         │
│  2 Game 8e62ba4b1488069e (Middlegame, Move 18. Nxe5): This was a critical blunder where you attempted to win a pawn  │
│    but completely miscalculated Black's response. This move opened the d-file for Black's rook, leading to a strong  │
│    counter-attack and a lost position.                                                                               │
│                                                                                                                      │
│ Recurring Theme: Tactical Blind Spots Under Pressure A clear pattern here is the occurrence of blunders that involve │
│ either directly hanging a piece (like the queen on g4) or miscalculating a tactical sequence, especially when your   │
│ king is already under pressure or your position is becoming difficult.                                               │
│                                                                                                                      │
│ Constructive Advice:                                                                                                 │
│                                                                                                                      │
│  • "Blunder Check" Routine: Before making any move, especially in complex or tense positions, ask yourself:          │
│     • "Is any of my pieces hanging?"                                                                                 │
│     • "Is my king safe after this move?"                                                                             │
│     • "What is my opponent's best response, and what are its consequences?"                                          │
│  • Prioritize King Safety: Be very cautious about pushing pawns directly in front of your castled king               │
│    unless you have a very clear and calculated reason.                                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Sources used for this analysis:
- Game ID: 9dace6c57af9c09a (Unknown)
- Game ID: 8e62ba4b1488069e (Unknown)
```

---

## 🚀 Quick Setup

> [!NOTE]
> The system defaults to Google's Gemini models, but strictly supports an agnostic `litellm` interface. You will need to generate API keys for the providers you wish to use. We never commit `.env` secret files directly to Git.

1. **Obtain API Keys**: Grab your key for Gemini from [Google AI Studio](https://aistudio.google.com/app/apikey), or equivalents from Anthropic or OpenAI.
2. **Save your secret Key**: Right in the main `chess-analyst` folder, create a new file named exactly `.env` and paste your keys inside like this:
    ```ini
    GEMINI_API_KEY="your-secret-key"
    ANTHROPIC_API_KEY="your-anthropic-key"
    OPENAI_API_KEY="your-openai-key"
    ```
3. **Install the dependencies**: Open your terminal here and install via `uv`:
    ```bash
    uv sync
    ```

---

## 🛠️ Usage

Using the pipeline operates in 3 simple phases:

### Step 1: Download & Ingest
First, download your history directly from Chess.com. Then load that large text file into your secure, local database. This step is 100% offline.
```bash
uv run python scripts/download_pgn.py YOUR_CHESSCOM_USERNAME
uv run chess-analyst ingest data/raw/your_new_games_file.pgn
```

### Step 2: Analyze & Grade Your Games
Have your model read ingested games and extract tactical arrays. You can optionally swap out the reasoning engine and the embedding engine via CLI flags.
```bash
# Using defaults (Gemini 2.5 Flash / Gemini Embedding)
uv run chess-analyst analyze --limit 5

# Or customizing models
uv run chess-analyst analyze --limit 5 --model claude --embedding-model text-embedding-3-small
```

### Step 3: View Results & Query
Get coaching feedback on the data!

**Look at a single game specifically:**
Display the play-by-play breakdown of exactly what you did right and wrong in a specific match.
```bash
uv run chess-analyst game YOUR-GAME-ID
```

**Chat with your entire history:**
Ask questions about your overall playstyle. The engine will utilize ChromaDB to return similar past mistakes.
```bash
uv run chess-analyst query "Based on my past games, what are the biggest endgame mistakes I make?" --model gpt-4o
```

*(You can also use `uv run chess-analyst stats` to check the footprint of your databases).*

---

## 🧪 Testing

We uphold strong engineering rigor through a robust test suite. Local operations are validated by mocking the API network layers.

```bash
uv run pytest
```

The testing suite relies on 4 core files:
- `test_parser.py`: Validates `python-chess` header extraction, raw string management, and idempotent ID logic.
- `test_analyzer.py`: Asserts correct enforcement of structured LLM outputs, boundaries, and mocked responses.
- `test_db.py`: Tracks SQLite storage flows and table schema logic.
- `test_vectordb.py`: Tests dimensionality matching and payload handling for embedding configurations prior to Chroma DB insertion.

---

## 🗄️ Detailed Architecture Overview

*(For detailed information on how the backend handles vector projections under the hood, check out the `PROJECT_SPEC.md` file.)*

- `source/main.py`: The `click` routing hub and CLI UI definitions.
- `source/parser.py`: Houses the purely local `python-chess` integration mapping flat PGNs into SQLite metadata blocks.
- `source/analyzer.py`: The rigid `instructor` engine enforcing Pydantic contracts across major foundation models.
- `source/vectordb.py`: Configurable `litellm` integration to store multi-dimensional representations into Chroma.
- `source/retriever.py`: Synthesizes vector searches via RAG (Retrieval-Augmented Generation).
- `data/`: The local environment cache containing the raw PGNs, `games.db` SQLite file, and local ChromaDB arrays (`data/chroma/`). Never push this directory to GitHub.