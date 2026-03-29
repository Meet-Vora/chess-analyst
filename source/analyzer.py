import os
import json
from pydantic import BaseModel, Field
from typing import List, Optional
from google import genai
from rich.progress import track
from rich.console import Console

from . import db
from . import vectordb

console = Console()

AVAILABLE_MODELS = {
    "gemini": {
        "id": "gemini-2.5-flash",
        "display_name": "Gemini 2.5 Flash"
    },
    "claude": {
        "id": "claude-3-5-sonnet-20241022",
        "display_name": "Claude 3.5 Sonnet"
    }
}

class PhaseAnalysis(BaseModel):
    phase: str = Field(description="The phase of the game: 'opening', 'middlegame', or 'endgame'")
    narrative_summary: str = Field(description="A detailed tactical and strategic narrative of what happened in this phase")
    mistakes: List[str] = Field(description="List of critical mistakes, blunders, or conceptual errors")
    patterns_identified: List[str] = Field(description="Recurring patterns of play, either positive or negative (e.g. 'weakness on light squares', 'strong knight outpost')")

class GameReview(BaseModel):
    opening_assessment: str = Field(description="A short assessment of how the opening was played relative to book expectations")
    phases: List[PhaseAnalysis] = Field(description="A breakdown of the game into its 3 phases")

def get_client():
    return genai.Client()

def analyze_games(limit: int = 10, dry_run: bool = False, game_id: str = None):
    """
    Fetches un-analyzed games from the DB and analyzes them using Gemini.
    """
    if game_id:
        game = db.get_game(game_id)
        if not game:
            console.print(f"[red]Game with ID {game_id} not found in database![/red]")
            return
        games = [game]
        console.print(f"Found [cyan]1[/cyan] requested game.")
    else:
        games = db.get_unanalyzed_games(limit=limit)
        if not games:
            console.print("[green]No new games to analyze![/green]")
            return
        console.print(f"Found [cyan]{len(games)}[/cyan] unanalyzed games.")
    
    if dry_run:
        console.print("[yellow]Dry run enabled. Would have analyzed the following games:[/yellow]")
        for g in games:
            console.print(f" - ID: {g['game_id']} | {g['white']} vs {g['black']} | {g['opening_name']}")
        return

    client = get_client()
    
    # Easily swap out the active model key here
    active_model = AVAILABLE_MODELS["gemini"]
    
    for game in track(games, description=f"Analyzing games with {active_model['display_name']}..."):
        prompt = f"""
You are an expert chess analyst and coach. I am providing you with the PGN of a chess game.
Please provide a deep, narrative tactical review of the game, breaking it down into opening, middlegame, and endgame phases.
Do not just provide engine evaluations; explain the *ideas* behind the moves, the strategic themes (e.g., pawn structures, outposts, weaknesses), and recurring playstyle patterns.

Game PGN:
{game['pgn_raw']}

Opening Played: {game['opening_name']} ({game['opening_eco']})
Result: {game['result']}
"""
        try:
            response = client.models.generate_content(
                model=active_model['id'],
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': GameReview,
                    'temperature': 0.2
                }
            )
            
            # The response text will be a JSON string conforming to the GameReview schema
            review_dict = json.loads(response.text)
            
            # Parse it using our Pydantic model just to ensure validity and format
            review = GameReview(**review_dict)
            
            for phase_data in review.phases:
                db.save_analysis(
                    game_id=game['game_id'],
                    phase=phase_data.phase,
                    summary=phase_data.narrative_summary,
                    mistakes=phase_data.mistakes,
                    patterns=phase_data.patterns_identified,
                    opening_assessment=review.opening_assessment
                )
                
                # Embedding context is a combined text of the summary, mistakes and patterns
                embedding_text = f"Phase: {phase_data.phase}\nSummary: {phase_data.narrative_summary}\nMistakes: {', '.join(phase_data.mistakes)}\nPatterns: {', '.join(phase_data.patterns_identified)}"
                
                # Adding it to Chroma
                vectordb.add_analysis_embedding(
                    game_id=game['game_id'],
                    phase=phase_data.phase,
                    analysis_text=embedding_text,
                    metadata={"opening": game['opening_name']}
                )
                
        except Exception as e:
            console.print(f"[red]Error analyzing game {game['game_id']}: {e}[/red]")
