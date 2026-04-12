import sqlite3
import os
import json
from contextlib import contextmanager

# Local path logic
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "games.db")

def init_db():
    """Initializes the SQLite database with necessary tables."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Games Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                pgn_raw TEXT NOT NULL,
                white TEXT,
                black TEXT,
                result TEXT,
                date TEXT,
                time_control TEXT,
                opening_name TEXT,
                opening_eco TEXT,
                num_moves INTEGER,
                source TEXT,
                termination TEXT
            )
        """)
        
        # Analysis Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_analysis (
                game_id TEXT,
                phase TEXT,
                narrative_summary TEXT,
                mistakes TEXT, -- JSON Array
                patterns_identified TEXT, -- JSON Array
                opening_assessment TEXT,
                critical_moments TEXT, -- JSON Array
                tactical_motifs_missed TEXT, -- JSON Array
                game_verdict TEXT,
                key_strengths TEXT, -- JSON Array
                PRIMARY KEY (game_id, phase),
                FOREIGN KEY (game_id) REFERENCES games(game_id)
            )
        """)
        
        # Idempotent migrations for existing MVP databases
        for col in ["critical_moments TEXT", "tactical_motifs_missed TEXT", "game_verdict TEXT", "key_strengths TEXT"]:
            try:
                cursor.execute(f"ALTER TABLE game_analysis ADD COLUMN {col}")
            except sqlite3.OperationalError:
                pass
                
        try:
            cursor.execute("ALTER TABLE games ADD COLUMN termination TEXT")
        except sqlite3.OperationalError:
            pass
        
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

def insert_game(game_data: dict) -> bool:
    """Inserts a game into the DB. Returns True if inserted, False if it already existed."""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO games (game_id, pgn_raw, white, black, result, date, time_control, opening_name, opening_eco, num_moves, source, termination)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game_data.get('game_id'),
                game_data.get('pgn_raw'),
                game_data.get('white'),
                game_data.get('black'),
                game_data.get('result'),
                game_data.get('date'),
                game_data.get('time_control'),
                game_data.get('opening_name'),
                game_data.get('opening_eco'),
                game_data.get('num_moves'),
                game_data.get('source'),
                game_data.get('termination')
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def get_unanalyzed_games(limit=None):
    """Fetches games that don't have an analysis yet, up to a given limit."""
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = """
            SELECT * FROM games
            WHERE game_id NOT IN (SELECT DISTINCT game_id FROM game_analysis)
            ORDER BY date DESC
        """
        if limit:
            query += f" LIMIT {int(limit)}"
            
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

def save_analysis(game_id: str, phase: str, summary: str, mistakes: list, patterns: list, opening_assessment: str,
                  critical_moments: list, tactical_motifs_missed: list, game_verdict: str, key_strengths: list = None):
    if key_strengths is None:
        key_strengths = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO game_analysis (
                game_id, phase, narrative_summary, mistakes, patterns_identified, 
                opening_assessment, critical_moments, tactical_motifs_missed, game_verdict, key_strengths
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_id,
            phase,
            summary,
            json.dumps(mistakes),
            json.dumps(patterns),
            opening_assessment,
            json.dumps(critical_moments),
            json.dumps(tactical_motifs_missed),
            game_verdict,
            json.dumps(key_strengths)
        ))
        conn.commit()

def get_game(game_id: str):
    """Fetches a specific game by its ID."""
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM games WHERE game_id = ?", (game_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_game_analysis(game_id: str):
    """Fetches the stored analysis phases for a specific game."""
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM game_analysis WHERE game_id = ?", (game_id,))
        return [dict(row) for row in cursor.fetchall()]
