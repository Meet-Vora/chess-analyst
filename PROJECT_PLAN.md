# Project Plan

## 1. Executive Summary & End Goal

**Core Objective:** A chess game analysis pipeline that ingests PGN files (from chess.com or Lichess), runs each game through Claude for narrative tactical reviews, and stores the analysis in a vector DB so I can query my playstyle patterns over time. Unlike standard engine evals that say "blunder on move 23," this tells me "you consistently collapse in Caro-Kann middlegames when your opponent controls the e5 square — here are 4 games where this happened."

**Definition of Done (v1 MVP):**

- Can ingest a PGN file containing multiple games
- Each game is parsed, analyzed by Claude, and stored with embeddings
- Can ask a natural language question ("what are my recurring mistakes in the Sicilian?") and get a synthesized answer drawing from multiple games
- All of this works via CLI

## 2. User Experience & Interaction Flow

**Core User Journey:** This is a CLI tool. Two main flows:

1. **Ingest flow:** User exports PGN from chess.com/Lichess → runs `chess-analyst ingest games.pgn` → pipeline parses each game, sends to Claude for analysis, stores results + embeddings. Progress bar shows games processed.
    
2. **Query flow:** User runs `chess-analyst query "why do I keep losing in the Caro-Kann?"` → semantic search across stored game analyses → Claude synthesizes a pattern-level answer referencing specific games.
    

Secondary commands: `chess-analyst stats` (show summary of games ingested, openings played, win/loss), `chess-analyst game <id>` (show the full analysis for a specific game).

## 3. System Architecture & Tech Stack

**The Stack:**

- **Language:** Python 3.11+
- **PGN parsing:** `python-chess` — mature library, handles PGN parsing and board state/move validation
- **LLM:** Claude API (Anthropic SDK) — for game analysis and query synthesis
- **Embeddings:** OpenAI `text-embedding-3-small` (or Voyage AI, since Anthropic partners with them)
- **Vector DB:** ChromaDB — lightweight, file-based, no server needed
- **Metadata store:** SQLite — game metadata (date, opponent, opening, result, time control)
- **CLI framework:** `click` or `argparse`
- **Engine eval (optional stretch):** `python-chess` + Stockfish binary for adding centipawn loss data to enrich Claude's analysis

**Boundaries:**

- No web UI — CLI only for v1
- No real-time chess.com/Lichess API integration for v1 — just file-based PGN import
- Don't build a custom embedding model — use an off-the-shelf embeddings API
- Don't try to make Claude "play chess" — it's analyzing games, not evaluating positions

## 4. Data Models & State Management

**Core Entities:**

- **Game** (SQLite): `game_id`, `pgn_raw`, `white`, `black`, `result`, `date`, `time_control`, `opening_name`, `opening_eco`, `num_moves`, `source` (chess.com/lichess)
- **GameAnalysis** (SQLite + ChromaDB): `game_id`, `phase` (opening/middlegame/endgame), `narrative_summary`, `mistakes` (JSON array), `patterns_identified`, `opening_assessment`
- **Embedding** (ChromaDB): One embedding per game analysis chunk, with game_id and phase as metadata for filtered retrieval

**State Strategy:**

- SQLite file (`~/.chess-analyst/games.db`) for structured game data
- ChromaDB persistent directory (`~/.chess-analyst/chroma/`) for embeddings + analysis text
- No remote storage — everything local for v1

## 5. Implementation Plan (Milestones)

**Milestone 1: PGN Ingestion + Parsing (2-3 hours)**

- Set up project structure, dependencies, CLI skeleton
- Build PGN parser using `python-chess` — extract games, metadata, move list
- Store parsed games in SQLite
- Test with a real PGN export from chess.com/Lichess
- Deliverable: `chess-analyst ingest games.pgn` works and populates the DB

**Milestone 2: Claude Analysis Pipeline (3-4 hours)**

- Design the analysis prompt — feed Claude the PGN + metadata, get back structured analysis (opening assessment, phase-by-phase review, mistake identification, pattern tags)
- Use structured outputs (JSON mode) so analysis is parseable
- Process each game, store analysis in SQLite
- Handle rate limiting and cost (batch processing, maybe a `--limit N` flag)
- Deliverable: Each ingested game has a Claude-generated narrative analysis stored

**Milestone 3: Embedding + Vector Search (2-3 hours)**

- Generate embeddings for each game analysis chunk
- Store in ChromaDB with game_id/phase/opening metadata
- Build the query flow: user question → embed → semantic search → retrieve top-K relevant game analyses
- Pass retrieved analyses to Claude for synthesis ("across these 5 games, here's the pattern...")
- Deliverable: `chess-analyst query "question"` returns a synthesized answer

**Milestone 4: Polish + README (1-2 hours)**

- Add `stats` and `game <id>` commands
- Error handling, edge cases (empty PGN, duplicate games)
- Write a clean README with usage examples, architecture diagram, and sample output
- Push to GitHub
- Deliverable: Portfolio-ready repo

**Stretch goals (post-v1):**

- Stockfish integration for centipawn loss data enriching Claude's analysis
- Chess.com/Lichess API integration for direct game import (no file export needed)
- Trend tracking over time ("your Sicilian win rate improved from 35% to 52% over the last month")
- Opening repertoire recommendations based on playstyle analysis

## 6. Agent Directives

- Keep the codebase modular — separate ingestion, analysis, embedding, and query into distinct modules. This is literally what Anthropic's CodeSignal tests evaluate (clean code as requirements grow)
- Use type hints everywhere — Python best practice and signals code quality
- Don't over-engineer v1. Resist the urge to add a web UI, authentication, or cloud storage. Ship the CLI first
- Structured outputs from Claude should be validated — don't trust the LLM to always return perfect JSON. Use Pydantic models for parsing
- Cost-conscious: Log token usage per game analysis so I know what this costs at scale. Add a `--dry-run` flag that shows what would be processed without calling the API
- Test with real data from my actual chess.com account, not synthetic games

---
