import os
import tempfile
import pytest

from source import parser
from source import db

# Example single game PGN
SAMPLE_PGN = """[Event "Live Chess"]
[Site "Chess.com"]
[Date "2024.01.01"]
[Round "-"]
[White "PlayerA"]
[Black "PlayerB"]
[Result "1-0"]
[Opening "Caro-Kann Defense"]
[ECO "B10"]

1. e4 c6 2. d4 d5 3. exd5 cxd5 4. Bd3 Nf6 5. h3 g6 6. Nf3 Bg7 7. O-O O-O
8. Re1 Nc6 9. c3 Bf5 10. Bxf5 gxf5 11. Bg5 Ne4 12. Bf4 e6 13. Nbd2 Kh8
14. Ne5 Nxe5 15. dxe5 Qc7 16. Nf3 Qb6 17. Qe2 Rac8 18. Rac1 Rc4 19. Be3 Qa5
20. a3 Rfc8 21. Bd4 b5 22. Qe3 R8c7 23. Ng5 Qa4 24. Nxe4 fxe4 25. Re2 a5
26. Rcc2 b4 27. axb4 axb4 28. Rd2 bxc3 29. bxc3 Qa1+ 30. Kh2 Rxc3 31. Bxc3 Rxc3
32. Qg5 h6 33. Qf4 Rc1 34. g5 Rh1+ 35. Kg3 Qg1# 1-0"""

@pytest.fixture
def mock_db_path(monkeypatch):
    # Setup an in-memory or temp DB for tests so we don't pollute local
    fd, temp_db_path = tempfile.mkstemp()
    os.close(fd)
    monkeypatch.setattr(db, 'DB_PATH', temp_db_path)
    yield temp_db_path
    os.remove(temp_db_path)

def test_parse_and_store_single_game(mock_db_path):
    # Setup test file
    fd, temp_pgn_path = tempfile.mkstemp(suffix=".pgn")
    with os.fdopen(fd, 'w') as f:
        f.write(SAMPLE_PGN)
        
    try:
        # Run function
        saved_count = parser.parse_and_store_pgn(temp_pgn_path)
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
        saved_count_two = parser.parse_and_store_pgn(temp_pgn_path)
        assert saved_count_two == 0
        
    finally:
        os.remove(temp_pgn_path)
