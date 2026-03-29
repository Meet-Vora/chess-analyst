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

---

## 4. Statistics
See the exact footprint of your databases.
```bash
uv run chess-analyst stats
```

---

## 5. 🗄️ Architecture & Folder Structure

- `source/main.py`: The `click` routing hub and CLI UI definitions.
- `source/parser.py`: Houses the purely local `python-chess` integration mapping flat PGNs into SQLite metadata blocks.
- `source/analyzer.py`: The rigid Pydantic engine enforcing JSON contracts with Gemini 2.5 Flash to ensure reliable analysis shapes.
- `source/vectordb.py`: Defines the `gemini-embedding-001` integration to store multi-dimensional representations of the tactical outputs into Chroma.
- `source/retriever.py`: Synthesizes vector searches via RAG (Retrieval-Augmented Generation).
- `data/`: The local environment cache containing the raw PGNs, `games.db` SQLite file, and local ChromaDB arrays (`data/chroma/`). Never push this directory to GitHub.

---

Example!

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
│    counter-attack and a lost position. You missed the tactical sequence that followed, specifically the discovered   │
│    attack potential on the d-file.                                                                                   │
│  3 Game 8e62ba4b1488069e (Middlegame, Move 21. f4): Following the previous blunder, this was a desperate and         │
│    weakening move that further compromised your king's safety and resulted in immediate material loss (a rook for a  │
│    pawn). This indicates a failure to calculate the consequences under pressure, leading to another significant      │
│    tactical error.                                                                                                   │
│                                                                                                                      │
│ Recurring Theme: Tactical Blind Spots Under Pressure A clear pattern here is the occurrence of blunders that involve │
│ either directly hanging a piece (like the queen on g4) or miscalculating a tactical sequence, especially when your   │
│ king is already under pressure or your position is becoming difficult. This suggests a need to slow down and         │
│ double-check your moves, particularly when the position is complex or when you're attempting an aggressive maneuver. │
│                                                                                                                      │
│ Strategic Blunders (Compromising King Safety)                                                                        │
│                                                                                                                      │
│ While not always "blunders" in the sense of hanging a piece, several strategic decisions significantly weakened your │
│ king's position, making it highly susceptible to the tactical blunders that followed:                                │
│                                                                                                                      │
│  1 Game 9dace6c57af9c09a (Opening, Move 9. f4 and Middlegame, Move 10. g3):                                          │
│     • 9. f4 was a strategic error that significantly weakened your kingside dark squares and created a backward pawn │
│       on e5. This made your king's position vulnerable and hindered development.                                     │
│     • 10. g3 further exacerbated these kingside weaknesses, particularly the dark squares, and did not address the   │
│       central tension or your king's safety. These moves created the conditions for the later queen blunder on move  │
│       12.                                                                                                            │
│  2 Game 8e62ba4b1488069e (Opening, Move 15. g3): Similar to the previous game, this defensive move created a         │
│    permanent weakness on f3 and the light squares around your king. This move, while intended to defend, ultimately  │
│    created long-term vulnerabilities that Black skillfully exploited.                                                │
│                                                                                                                      │
│ Recurring Theme: Neglecting King Safety and Creating Permanent Weaknesses You have a tendency to make pawn moves     │
│ (like f4 and g3) around your king that, while sometimes intended for defense or expansion, often create permanent    │
│ weaknesses (e.g., weakened dark squares, exposed king) without adequate compensation. These strategic missteps don't │
│ immediately lose the game but create a fragile foundation that makes you prone to tactical blunders later on,        │
│ especially when your opponent starts an attack.                                                                      │
│                                                                                                                      │
│ Constructive Advice:                                                                                                 │
│                                                                                                                      │
│  • "Blunder Check" Routine: Before making any move, especially in complex or tense positions, ask yourself:          │
│     • "Is any of my pieces hanging?"                                                                                 │
│     • "Is my king safe after this move?"                                                                             │
│     • "What is my opponent's best response, and what are its consequences?"                                          │
│     • "Am I creating any new weaknesses?"                                                                            │
│  • Prioritize King Safety: Be very cautious about pushing pawns directly in front of your castled king (like f4 or   │
│    g3) unless you have a very clear and calculated reason, and you've assessed the long-term implications for your   │
│    king's safety. Often, these moves create more problems than they solve.                                           │
│  • Improve Tactical Vision: Practice tactical puzzles regularly. Focus on recognizing common tactical motifs like    │
│    forks, pins, skewers, discovered attacks, and hanging pieces. This will help you spot both your own blunders and  │
│    your opponent's threats.                                                                                          │
│  • Evaluate Consequences of Aggression: When you make an aggressive move (like 18. Nxe5), take extra time to         │
│    calculate the full sequence of moves, not just the immediate gain. Aggression without calculation often leads to  │
│    blunders.                                                                                                         │
│                                                                                                                      │
│ By addressing these patterns of tactical oversight and strategic king safety neglect, you can significantly reduce   │
│ the number of blunders in your games and build a more solid foundation for your play.                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯


Sources used for this analysis:
- Game ID: 9dace6c57af9c09a (Unknown)
- Game ID: 9dace6c57af9c09a (Unknown)
- Game ID: 8e62ba4b1488069e (Unknown)
- Game ID: 8e62ba4b1488069e (Unknown)
- Game ID: 9dace6c57af9c09a (Unknown)
```