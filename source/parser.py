import chess.pgn
import hashlib
from typing import Iterator
from rich.progress import Progress

import os
import glob
from . import db

def generate_game_id(headers: chess.pgn.Headers, pgn_string: str) -> str:
    """Generates a stable unique ID based on game headers and moves."""
    # A combination of key headers and the move string should be unique.
    unique_string = f"{headers.get('White', '')}-{headers.get('Black', '')}-{headers.get('Date', '')}-{pgn_string}"
    return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()[:16]

def parse_and_store_pgn(file_path: str) -> int:
    """Reads a PGN file, extracts games, and stores them in SQLite DB."""
    db.init_db()
    
    saved_count = 0
    skipped_count = 0
    
    # We first count games if possible, but PGNs can be huge. We'll just read linearly.
    with open(file_path, "r", encoding="utf-8") as f, Progress(transient=True) as progress:
        task = progress.add_task("[cyan]Parsing PGN games...", total=None)
        
        while True:
            try:
                game = chess.pgn.read_game(f)
            except Exception as e:
                # Log the error and skip to next game
                print(f"[WARN] Failed to read a game: {e}")
                continue
            if game is None:
                break
            
            # Canonical string representation avoids manual file seeks
            raw_pgn = str(game)
            
            headers = game.headers
            game_id = generate_game_id(headers, raw_pgn)
            
            # Determine source
            site = headers.get("Site", "").lower()
            source = "unknown"
            if "chess.com" in site:
                source = "chess.com"
            elif "lichess" in site:
                source = "lichess"

            total_moves = len(list(game.mainline_moves()))
            if total_moves == 0:
                # If there are no moves, it's either an empty file or pure garbage text
                continue
            
            # Extract basic data
            game_data = {
                "game_id": game_id,
                "pgn_raw": raw_pgn,
                "white": headers.get("White", "Unknown"),
                "black": headers.get("Black", "Unknown"),
                "result": headers.get("Result", "*"),
                "date": headers.get("Date", "????.??.??"),
                "time_control": headers.get("TimeControl", "-"),
                "opening_name": headers.get("Opening", "Unknown"),
                "opening_eco": headers.get("ECO", "???"),
                "num_moves": total_moves,
                "source": source,
                "termination": headers.get("Termination", "Unknown")
            }
            
            # Attempt to insert
            is_saved = db.insert_game(game_data)
            saved_count += 1 if is_saved else 0
            skipped_count += 0 if is_saved else 1
                
            progress.update(task, advance=1, description=f"[cyan]Parsing PGN... (Saved: {saved_count}, Skipped: {skipped_count})")
            
    return saved_count


def parse_and_store_all_pgns(directory: str) -> int:
    """Parse and store all *.pgn files in the given directory.

    Returns the total number of newly saved games across all files.
    """
    total_saved = 0
    import os, glob
    pgn_paths = glob.glob(os.path.join(directory, "*.pgn"))
    if not pgn_paths:
        print(f"[INFO] No PGN files found in {directory}")
        return 0
    for pgn_file in pgn_paths:
        print(f"[INFO] Processing {pgn_file} ...")
        saved = parse_and_store_pgn(pgn_file)
        total_saved += saved
    print(f"[INFO] Finished processing directory. Total new games saved: {total_saved}")
    return total_saved
