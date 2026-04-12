import pytest
import json
from unittest.mock import patch, MagicMock
from source import analyzer
from source.analyzer import GameReview, PhaseAnalysis

@patch('source.analyzer.db.save_analysis')
@patch('source.analyzer.vectordb.add_analysis_embedding')
@patch('source.analyzer.get_client')
def test_mocked_gemini_analysis_flow(mock_get_client, mock_add_embedding, mock_save_analysis):
    """
    Simulates a flawlessly formatted AI JSON payload returning from Instructor/LiteLLM,
    validating that Pydantic models structure it cleanly and pass it directly to the 
    sqlite database without actually spinning up physical APIs or Databases.
    """
    # Setup mock Client
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Spoof the exact Pydantic output that Instructor yields natively
    mock_review = GameReview(
        game_verdict="A hard fought tactical battle.",
        opening_assessment="Solid foundation in the Caro-Kann.",
        phases=[
            PhaseAnalysis(
                phase="opening",
                narrative_summary="Developed well.",
                mistakes=[],
                patterns_identified=["Solid central control"],
                critical_moments=[],
                tactical_motifs_missed=[]
            )
        ]
    )
    
    # Attach our simulated Pydantic object to the completion return
    mock_client.chat.completions.create.return_value = mock_review

    # Define a single imaginary game ripped from SQLite
    fake_games = [{
        "game_id": "test_123",
        "pgn_raw": "1. e4 c6 2. d4 d5",
        "opening_name": "Caro-Kann Defense",
        "opening_eco": "B10",
        "result": "1/2-1/2"
    }]

    # Override get_unanalyzed_games to inject our fake game into the pipeline cleanly
    with patch('source.analyzer.db.get_unanalyzed_games') as mock_get_games:
        mock_get_games.return_value = fake_games
        # Override the rich console print to suppress raw output tracking during tests
        with patch('source.analyzer.console.print'):
            analyzer.analyze_games(limit=1, dry_run=False, game_id=None)

    # 1. Did the prompt physically exit the Python loop toward the API?
    assert mock_client.chat.completions.create.call_count == 1
    
    # 2. Did the JSON payload get saved down to our relational SQLite system securely?
    assert mock_save_analysis.call_count == 1
    mock_save_analysis.assert_called_with(
        game_id="test_123",
        phase="opening",
        summary="Developed well.",
        mistakes=[],
        patterns=["Solid central control"],
        opening_assessment="Solid foundation in the Caro-Kann.",
        critical_moments=[],
        tactical_motifs_missed=[],
        game_verdict="A hard fought tactical battle."
    )
    
    # 3. Did it then extract a blob string of that phase and send it to our Vector module?
    assert mock_add_embedding.call_count == 1
