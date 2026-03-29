import os
import tempfile
import pytest

from source import parser
from source import db

@pytest.fixture
def mock_db_path(monkeypatch):
    # Setup an in-memory or temp DB for tests so we don't pollute local
    fd, temp_db_path = tempfile.mkstemp()
    os.close(fd)
    monkeypatch.setattr(db, 'DB_PATH', temp_db_path)
    yield temp_db_path
    os.remove(temp_db_path)

def test_parse_and_store_single_game(mock_db_path):
    """
    Verifies that a well-formatted PGN file with exactly one game is correctly
    parsed by python-chess, extracts the right metadata, and inserts cleanly into SQLite.
    Also tests that redundant ingestion attempts are skipped.
    """
    saved_count = parser.parse_and_store_pgn("tests/data/good.pgn")
    assert saved_count == 1
    
    # Verify db contents
    games = db.get_unanalyzed_games()
    assert len(games) == 1
    g = games[0]
    assert g['white'] == "PlayerA"
    assert g['opening_eco'] == "B10"
    assert g['source'] == "chess.com"
    assert 10 < g['num_moves'] < 100
    
    # Test duplicate ingestion is avoided
    saved_count_two = parser.parse_and_store_pgn("tests/data/good.pgn")
    assert saved_count_two == 0

def test_parse_multiple_games(mock_db_path):
    """
    Verifies that a single PGN file containing multiple appended games 
    (which is the standard format for Lichess/Chess.com archives) 
    properly parses and inserts all games into the database.
    """
    saved_count = parser.parse_and_store_pgn("tests/data/multiple.pgn")
    assert saved_count == 2
    
    games = db.get_unanalyzed_games()
    assert len(games) == 2

def test_parse_malformed_pgn(mock_db_path):
    """
    Ensures the parser gracefully ignores or fails to parse files that contain 
    pure garbage text instead of valid PGN headers or move strings.
    """
    saved_count = parser.parse_and_store_pgn("tests/data/garbage.txt")
    assert saved_count == 0
    
    games = db.get_unanalyzed_games()
    assert len(games) == 0

def test_parse_illegal_move_pgn(mock_db_path):
    """
    Ensures that games with structurally valid PGN headers but invalid/impossible
    moves are still handled safely without crashing the module. It may save the
    partial game up to the error, or skip it, but python-chess must not bubble an unhandled error.
    """
    saved_count = parser.parse_and_store_pgn("tests/data/illegal_move.pgn")
    assert saved_count >= 0 

