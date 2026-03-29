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

# These Pydantic models act as "Instruction Contracts" between our code and the LLM.
# By passing these to the Gemini API via the `response_schema` parameter, the SDK 
# forces the AI to securely return perfectly formatted, predictable JSON output 
# (with the exact fields and lists we define below) instead of free-flowing text.
# The `description` fields act as mini-prompts instructing the AI how to generate a value.

class PhaseAnalysis(BaseModel):
    phase: str = Field(description="The phase of the game: 'opening', 'middlegame', or 'endgame'")
    narrative_summary: str = Field(description="A detailed tactical and strategic narrative of what happened in this phase")
    mistakes: List[str] = Field(description="List of critical mistakes, blunders, or conceptual errors")
    patterns_identified: List[str] = Field(description="Recurring patterns of play, either positive or negative (e.g. 'weakness on light squares', 'strong knight outpost')")
    critical_moments: List[str] = Field(description="List of turning points or move numbers where the game's evaluation drastically shifted")
    tactical_motifs_missed: List[str] = Field(description="Specific tactical motifs missed, such as 'knight fork', 'pin', or 'discovered attack'")

class GameReview(BaseModel):
    opening_assessment: str = Field(description="A short assessment of how the opening was played relative to book expectations")
    game_verdict: str = Field(description="A 1-sentence summary of why the game was ultimately won or lost")
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
    
    # Temperature controls the "creativity" of the LLM scale (0.0 to 1.0+). 
    # Because we are asking Gemini to act as an analytical chess coach and output strict, 
    # structured JSON, we use a low temperature to prioritize analytical precision 
    # and determinism over hallucination or creative writing.
    ANALYSIS_TEMPERATURE = 0.2
    
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
                    'temperature': ANALYSIS_TEMPERATURE
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
                    opening_assessment=review.opening_assessment,
                    critical_moments=phase_data.critical_moments,
                    tactical_motifs_missed=phase_data.tactical_motifs_missed,
                    game_verdict=review.game_verdict
                )
                
                # Embedding context is a combined text of the summary, mistakes and patterns
                embedding_text = (f"Phase: {phase_data.phase}\n"
                                  f"Summary: {phase_data.narrative_summary}\n"
                                  f"Mistakes: {', '.join(phase_data.mistakes)}\n"
                                  f"Patterns: {', '.join(phase_data.patterns_identified)}\n"
                                  f"Critical Moments: {', '.join(phase_data.critical_moments)}\n"
                                  f"Missed Tactics: {', '.join(phase_data.tactical_motifs_missed)}\n"
                                  f"Game Verdict: {review.game_verdict}")
                
                # Adding it to Chroma
                vectordb.add_analysis_embedding(
                    game_id=game['game_id'],
                    phase=phase_data.phase,
                    analysis_text=embedding_text,
                    metadata={"opening": game['opening_name']}
                )
                
        except Exception as e:
            console.print(f"[red]Error analyzing game {game['game_id']}: {e}[/red]")
            
    # Notify the user that the entire batch is complete
    console.print(f"\n[bold green]Analysis of {len(games)} games done![/bold green]")
