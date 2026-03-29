import os
import tempfile
import pytest

from source import db

@pytest.fixture
def mock_db_path(monkeypatch):
    fd, temp_db_path = tempfile.mkstemp()
    os.close(fd)
    monkeypatch.setattr(db, 'DB_PATH', temp_db_path)
    yield temp_db_path
    os.remove(temp_db_path)

def test_insert_and_get_game(mock_db_path):
    """
    Verifies that a game dict can be seamlessly converted to an SQLite row and 
    inserted successfully, and that duplicate attempts fail gracefully while
    subsequent fetches correctly unpack the row into a python dict.
    """
    db.init_db()
    
    test_game = {
        "game_id": "test_id_123",
        "pgn_raw": "1. e4 e5",
        "white": "TestWhite",
        "black": "TestBlack",
        "result": "1/2-1/2",
        "date": "2024.01.01",
        "time_control": "300+0",
        "opening_name": "Ruy Lopez",
        "opening_eco": "C60",
        "num_moves": 2,
        "source": "lichess"
    }
    
    # Test Insert
    assert db.insert_game(test_game) == True
    
    # Test Duplicate Insert prevention
    assert db.insert_game(test_game) == False
    
    # Test Get Game
    retrieved = db.get_game("test_id_123")
    assert retrieved is not None
    assert retrieved["white"] == "TestWhite"

def test_unanalyzed_games_logic(mock_db_path):
    """
    Checks that the database perfectly intersects the games table and the 
    game_analysis table to filter out games that have already been run through 
    the Gemini pipeline.
    """
    db.init_db()
    
    db.insert_game({"game_id": "g1", "pgn_raw": "1. d4", "white": "w1", "black": "b1", "result": "1-0", "date": "2024", "time_control": "-", "opening_name": "QG", "opening_eco": "D00", "num_moves": 1, "source": "-"})
    db.insert_game({"game_id": "g2", "pgn_raw": "1. e4", "white": "w2", "black": "b2", "result": "0-1", "date": "2024", "time_control": "-", "opening_name": "e4", "opening_eco": "B00", "num_moves": 1, "source": "-"})
    
    # Both should be unanalyzed initially
    un_games = db.get_unanalyzed_games()
    assert len(un_games) == 2
    
    # Save an analysis for g1
    db.save_analysis(
        game_id="g1",
        phase="opening",
        summary="Test summary",
        mistakes=["m1"],
        patterns=["p1"],
        opening_assessment="Good",
        critical_moments=["c1"],
        tactical_motifs_missed=["t1"],
        game_verdict="Verdict test"
    )
    
    # Now only g2 should be unanalyzed
    un_games_after = db.get_unanalyzed_games()
    assert len(un_games_after) == 1
    assert un_games_after[0]["game_id"] == "g2"

def test_fetch_game_analysis(mock_db_path):
    """
    Tests that saving and fetching analysis properties (including the 
    new pydantic fields like tactical_motifs_missed) works transparently
    via database extraction.
    """
    db.init_db()
    db.insert_game({"game_id": "g3", "pgn_raw": "1. e4", "white": "w3", "black": "b3", "result": "1-0", "date": "2024", "time_control": "-", "opening_name": "e4", "opening_eco": "B00", "num_moves": 1, "source": "-"})
    
    # Shouldn't exist yet
    assert len(db.get_game_analysis("g3")) == 0
    
    db.save_analysis(
        game_id="g3",
        phase="opening",
        summary="Test summary",
        mistakes=[],
        patterns=[],
        opening_assessment="Okay",
        critical_moments=[],
        tactical_motifs_missed=[],
        game_verdict="Won"
    )
    
    analyses = db.get_game_analysis("g3")
    assert len(analyses) == 1
    assert analyses[0]["phase"] == "opening"
    assert analyses[0]["game_verdict"] == "Won"
