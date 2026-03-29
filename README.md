# ♟️ Chess Analyst

Welcome to **Chess Analyst**! 

If you play chess online (like on Chess.com or Lichess), you probably have thousands of past games that you've totally forgotten about. 

This project is a powerful, locally-hosted tool that lets you download those old games, and uses the **Google Gemini AI** as your personal chess coach to read them. It will automatically point out your common mistakes, track your tactical habits across the Opening or Endgames, and allow you to physically chat with your historical data to figure out why you keep losing.

*(For detailed information on how the architecture handles vector generation and database structuring under the hood, check out the `PROJECT_SPEC.md` file!)*

---

## 1. Quick Setup

> [!NOTE]
> If you are just cloning this repository from GitHub, you will need to manually generate your own free Gemini API key and store it locally so the AI has permission to run. We never commit `.env` secret files directly to Git.

Before you run the tool, you just need to get it set up on your machine:

1. **Get your Google AI Key**: Go to [Google AI Studio](https://aistudio.google.com/app/apikey) and generate a 100% free API key.
2. **Save your secret Key**: Right in the main `chess-analyst` folder, create a new file named exactly `.env` and paste your key inside like this:
    ```ini
    GEMINI_API_KEY="your-secret-key"
    ```
3. **Install the dependencies**: Open your terminal here and type:
    ```bash
    uv sync
    ```

---

## 2. Setting Up Your Data Pipeline

Using the tool happens in 3 super simple steps. 

Because we built the project cleanly, you just run `uv run chess-analyst` followed by whatever command you want!

### Step 1: Download your Chess History
First, we provide a quick utility script for you to instantly download all your history directly from Chess.com.
```bash
uv run python scripts/download_pgn.py YOUR_CHESSCOM_USERNAME
```
This will automatically save a `.pgn` text file containing all your games into the `data/raw/` folder!

### Step 2: "Ingesting" the File
We need to load that massive text file into your secure, local database. This step is 100% offline and takes a fraction of a second.
```bash
uv run chess-analyst ingest data/raw/your_new_games_file.pgn
```

### Step 3: Analyze & Grade Your Games
Now, you actually ask Gemini to read those games and grade your performance under the hood. Because the AI takes a few seconds to map out the vectors and generate the text for every single match, we recommend running small batches of 5-10 games at a time!
```bash
uv run chess-analyst analyze --limit 5
```

---

## 3. The Coach: Viewing Your Results!

Once you have analyzed a batch of games, you have two super cool ways to interact with the AI to get coaching feedback on the results.

**Look at a single game specifically:**
If you want the AI's play-by-play breakdown of exactly what you did right and wrong in a specific match, use the `game` command with the Game's ID:
```bash
uv run chess-analyst game YOUR-GAME-ID
```

**Chat with your entire history:**
This is the best feature in the app. The AI remembers all the mistakes across every analyzed game. You can literally ask it questions about your overall playstyle, and it will search all your past games to generate an answer!
```bash
uv run chess-analyst query "I keep losing when I play the Sicilian Defense as black. Based on my past games, what are the biggest endgame mistakes I make?"
```

### 5. Statistics
See the exact footprint of your databases.
```bash
uv run chess-analyst stats
```

---

## 🗄️ Architecture & Folder Structure

- `source/main.py`: The `click` routing hub and CLI UI definitions.
- `source/parser.py`: Houses the purely local `python-chess` integration mapping flat PGNs into SQLite metadata blocks.
- `source/analyzer.py`: The rigid Pydantic engine enforcing JSON contracts with Gemini 2.5 Flash to ensure reliable analysis shapes.
- `source/vectordb.py`: Defines the `gemini-embedding-001` integration to store multi-dimensional representations of the tactical outputs into Chroma.
- `source/retriever.py`: Synthesizes vector searches via RAG (Retrieval-Augmented Generation).
- `data/`: The local environment cache containing the raw PGNs, `games.db` SQLite file, and local ChromaDB arrays (`data/chroma/`). Never push this directory to GitHub.
