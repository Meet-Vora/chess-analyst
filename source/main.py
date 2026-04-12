import click
import sys
import os
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich import box
from dotenv import load_dotenv

from . import parser
from . import analyzer
from . import retriever
from . import db
from . import model_config

# Load environment logic right away, so SDK clients work correctly
load_dotenv()

console = Console()

@click.group()
def cli():
    """Chess Analyst CLI: A pipeline for reasoning over playstyles."""
    pass

@cli.command()
def setup():
    """Interactive wizard to rapidly configure Chess Analyst."""
    from rich.panel import Panel
    console.print(Panel("[bold cyan]Welcome to Chess Analyst Setup![/bold cyan]\nWe'll get you ready to analyze your games in under a minute.", expand=False))
    
    # 1. API Keys
    console.print("\n[bold]Step 1: AI Provider Keys[/bold]")
    console.print("You need at least one API key (Gemini, Anthropic, OpenAI). Press Enter to skip any you don't have.")
    
    env_content = ""
    gemini_key = click.prompt("Google Gemini API Key", default="", hide_input=True)
    if gemini_key: env_content += f'GEMINI_API_KEY="{gemini_key}"\n'
    
    anthropic_key = click.prompt("Anthropic API Key (Claude)", default="", hide_input=True)
    if anthropic_key: env_content += f'ANTHROPIC_API_KEY="{anthropic_key}"\n'
    
    openai_key = click.prompt("OpenAI API Key (GPT)", default="", hide_input=True)
    if openai_key: env_content += f'OPENAI_API_KEY="{openai_key}"\n'
    
    if env_content:
        with open(".env", "a") as f:
            f.write(env_content)
        console.print("[green]Saved API keys to .env file![/green]")
        load_dotenv(override=True)
    else:
        console.print("[yellow]No API keys provided! You will need to manually add them to .env later.[/yellow]")
        
    # 2. Download Games
    console.print("\n[bold]Step 2: Download Your Chess.com History[/bold]")
    username = click.prompt("What is your Chess.com username? (Leave blank to skip)", default="")
    
    if username:
        console.print(f"[cyan]Downloading games for {username} (this might take a moment)...[/cyan]")
        script_path = os.path.join(os.path.dirname(__file__), "..", "scripts", "download_pgn.py")
        result = subprocess.run([sys.executable, script_path, username])
        if result.returncode != 0:
             console.print("[red]Failed to download games. Let's skip to the next step.[/red]")
        else:
             console.print("[green]Downloaded games successfully![/green]")
             console.print("\n[bold]Step 3: Ingest Games[/bold]")
             with console.status("[bold green]Ingesting all downloaded games...[/bold green]", spinner="bouncingBall"):
                 raw_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
                 os.makedirs(raw_dir, exist_ok=True)
                 saved = parser.parse_and_store_all_pgns(raw_dir)
                 console.print(f"[bold green]Successfully saved {saved} new games to the database![/bold green]")
             
             console.print("\n[bold]Step 4: AI Analysis[/bold]")
             analyze_games = click.confirm("Would you like to analyze some of these games now to get immediate feedback?", default=True)
             if analyze_games:
                 num_games = click.prompt("How many games would you like to analyze?", default=5, type=int)
                 analyzer.analyze_games(limit=num_games, dry_run=False, game_id=None, model=model_config.DEFAULT_MODEL_FQN)
             
    console.print("\n[bold cyan]Setup Complete! You're ready to use Chess Analyst.[/bold cyan]")

@cli.command()
@click.argument('pgn_file', type=click.Path(exists=True))
def ingest(pgn_file: str):
    """Ingests a PGN file and stores games into SQLite."""
    console.print(f"[bold cyan]Ingesting games from:[/bold cyan] {pgn_file}")
    
    with console.status("[bold green]Crunching raw PGN data...[/bold green]", spinner="bouncingBall"):
        saved = parser.parse_and_store_pgn(pgn_file)
    
    if saved > 0:
        console.print(f"[bold green]Successfully saved {saved} new games to the database![/bold green]")
    else:
        console.print("[yellow]No new games were saved (all duplicates or parse errors).[/yellow]")

@cli.command()
@click.option('--limit', default=10, help="Maximum number of games to analyze in this run.")
@click.option('--dry-run', is_flag=True, help="Show which games would be analyzed without invoking the LLM.")
@click.option('--game-id', default=None, help="Process a specific game by ID.")
@click.option('--model', default=model_config.DEFAULT_MODEL_ALIAS, help="Model to use for analysis (alias or litellm string, e.g. 'claude', 'gpt-4o').")
def analyze(limit: int, dry_run: bool, game_id: str, model: str):
    """Analyzes unreviewed games and embeds insights into ChromaDB."""
    resolved_model = model_config.resolve_model(model)
    analyzer.analyze_games(
        limit=limit, 
        dry_run=dry_run, 
        game_id=game_id, 
        model=resolved_model
    )

@cli.command()
@click.argument('game_id')
def game(game_id: str):
    """Shows the stored analysis for a specific game ID."""
    analyses = db.get_game_analysis(game_id)
    if not analyses:
        console.print(f"[yellow]No analysis found for game '{game_id}'. Have you run 'analyze' on it?[/yellow]")
        return
        
    console.print(f"[bold cyan]Analysis for Game:[/bold cyan] {game_id}")
    
    # Verdict is stored redundantly across phases, so just grab it from the first one
    if analyses and analyses[0].get('game_verdict'):
        console.print(f"\n[bold green]Verdict:[/bold green] {analyses[0]['game_verdict']}\n")
        
    import json
    for a in analyses:
        # Parse JSON lists back into Python lists cleanly or default to empty lists
        mistakes = json.loads(a.get('mistakes') or "[]")
        patterns = json.loads(a.get('patterns_identified') or "[]")
        critical_moments = json.loads(a.get('critical_moments') or "[]")
        missed_tactics = json.loads(a.get('tactical_motifs_missed') or "[]")
        key_strengths = json.loads(a.get('key_strengths') or "[]")

        # Build the phase text natively as markdown
        content = f"**Summary:** {a['narrative_summary']}\n\n"
        content += f"**Strengths / Good Play:** {', '.join(key_strengths) if key_strengths else 'None'}\n\n"
        content += f"**Mistakes:** {', '.join(mistakes) if mistakes else 'None'}\n\n"
        content += f"**Patterns:** {', '.join(patterns) if patterns else 'None'}"
        
        if critical_moments:
            content += f"\n\n**Critical Moments:** {', '.join(critical_moments)}"
        if missed_tactics:
            content += f"\n\n**Missed Tactics:** {', '.join(missed_tactics)}"
            
        if a['phase'] == 'opening' and a.get('opening_assessment'):
             content += f"\n\n**Opening Assessment:** {a['opening_assessment']}"
             
        # Render the text beautifully inside a custom boxed panel
        panel = Panel(
            Markdown(content), 
            title=f"[bold magenta]{a['phase'].upper()}[/bold magenta]", 
            title_align="left", 
            border_style="cyan",
            expand=False
        )
        console.print(panel)

@cli.command()
@click.argument('question')
@click.option('--n-results', default=5, help="Number of related game phases to synthesize over.")
@click.option('--model', default=model_config.DEFAULT_MODEL_ALIAS, help="Model to use for synthesis (alias or litellm string, e.g. 'claude', 'gpt-4o').")
def query(question: str, n_results: int, model: str):
    """Queries playstyle history by searching past game analyses."""
    console.print(f"[bold cyan]Querying history for:[/bold cyan] {question}")
    resolved_model = model_config.resolve_model(model)
    retriever.query_playstyle(
        question=question, 
        n_results=n_results, 
        model=resolved_model
    )

@cli.command()
def stats():
    """Shows statistics across the ingestion and analysis pipeline."""
    db.init_db()
    import sqlite3
    with db.get_db() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Game stats
        cursor.execute("SELECT count(*) FROM games")
        total_games = cursor.fetchone()[0]
        
        # Analysis stats
        cursor.execute("SELECT count(DISTINCT game_id) FROM game_analysis")
        analyzed_games = cursor.fetchone()[0]
        
        table = Table(title="🗄️ Database Statistics", box=box.ROUNDED)
        table.add_column("Metric", justify="right", style="cyan", no_wrap=True)
        table.add_column("Count", style="magenta")
        
        table.add_row("Total Games Ingested", str(total_games))
        table.add_row("Games Completely Analyzed", str(analyzed_games))
        
        console.print(table)
        
        if total_games == 0:
            return
            
        # Discover the user's actual username by finding the most frequently played name
        cursor.execute("""
            SELECT player FROM (
                SELECT white as player, count(*) as count FROM games GROUP BY white
                UNION ALL
                SELECT black as player, count(*) as count FROM games GROUP BY black
            )
            GROUP BY player
            ORDER BY sum(count) DESC LIMIT 1
        """)
        row = cursor.fetchone()
        if not row:
            return
        username = row[0]
        
        # Win / Loss / Draw query (All Ingested)
        cursor.execute("""
            SELECT
                SUM(CASE WHEN white = ? AND result = '1-0' THEN 1 ELSE 0 END) as white_wins,
                SUM(CASE WHEN white = ? AND result = '0-1' THEN 1 ELSE 0 END) as white_losses,
                SUM(CASE WHEN white = ? AND result = '1/2-1/2' THEN 1 ELSE 0 END) as white_draws,
                SUM(CASE WHEN black = ? AND result = '0-1' THEN 1 ELSE 0 END) as black_wins,
                SUM(CASE WHEN black = ? AND result = '1-0' THEN 1 ELSE 0 END) as black_losses,
                SUM(CASE WHEN black = ? AND result = '1/2-1/2' THEN 1 ELSE 0 END) as black_draws
            FROM games
        """, (username, username, username, username, username, username))
        wld = cursor.fetchone()
        
        # Win / Loss / Draw query (Analyzed only)
        cursor.execute("""
            SELECT
                SUM(CASE WHEN white = ? AND result = '1-0' THEN 1 ELSE 0 END) as white_wins,
                SUM(CASE WHEN white = ? AND result = '0-1' THEN 1 ELSE 0 END) as white_losses,
                SUM(CASE WHEN white = ? AND result = '1/2-1/2' THEN 1 ELSE 0 END) as white_draws,
                SUM(CASE WHEN black = ? AND result = '0-1' THEN 1 ELSE 0 END) as black_wins,
                SUM(CASE WHEN black = ? AND result = '1-0' THEN 1 ELSE 0 END) as black_losses,
                SUM(CASE WHEN black = ? AND result = '1/2-1/2' THEN 1 ELSE 0 END) as black_draws
            FROM games
            WHERE game_id IN (SELECT DISTINCT game_id FROM game_analysis)
        """, (username, username, username, username, username, username))
        wld_analyzed = cursor.fetchone()

        wld_table = Table(title=f"🏆 Win/Loss Record for '{username}'", box=box.ROUNDED)
        wld_table.add_column("Scope", justify="left", style="cyan", no_wrap=True)
        wld_table.add_column("Color", justify="left", style="white", no_wrap=True)
        wld_table.add_column("Wins", justify="right", style="bold green")
        wld_table.add_column("Losses", justify="right", style="bold red")
        wld_table.add_column("Draws", justify="right", style="bold yellow")
        
        wld_table.add_row("Ingested", "⚪ White", str(wld["white_wins"] or 0) if wld else "0", str(wld["white_losses"] or 0) if wld else "0", str(wld["white_draws"] or 0) if wld else "0")
        wld_table.add_row("Ingested", "⚫ Black", str(wld["black_wins"] or 0) if wld else "0", str(wld["black_losses"] or 0) if wld else "0", str(wld["black_draws"] or 0) if wld else "0")
        wld_table.add_row("Analyzed", "⚪ White", str(wld_analyzed["white_wins"] or 0) if wld_analyzed else "0", str(wld_analyzed["white_losses"] or 0) if wld_analyzed else "0", str(wld_analyzed["white_draws"] or 0) if wld_analyzed else "0")
        wld_table.add_row("Analyzed", "⚫ Black", str(wld_analyzed["black_wins"] or 0) if wld_analyzed else "0", str(wld_analyzed["black_losses"] or 0) if wld_analyzed else "0", str(wld_analyzed["black_draws"] or 0) if wld_analyzed else "0")
        console.print(wld_table)
        
        # Termination conditions string search for wins
        cursor.execute("""
            SELECT termination FROM games 
            WHERE (white = ? AND result = '1-0') OR (black = ? AND result = '0-1')
        """, (username, username))
        terminations = cursor.fetchall()
        
        if terminations:
            checkmate_wins = sum(1 for t in terminations if t and t["termination"] and "checkmate" in t["termination"].lower())
            time_wins = sum(1 for t in terminations if t and t["termination"] and "time" in t["termination"].lower())
            resignation_wins = sum(1 for t in terminations if t and t["termination"] and ("resignation" in t["termination"].lower() or "resigned" in t["termination"].lower()))
            other_wins = len(terminations) - checkmate_wins - time_wins - resignation_wins
            
            term_table = Table(title="🗡️ How You Win (All Ingested Games)", box=box.ROUNDED)
            term_table.add_column("Condition", justify="left", style="cyan")
            term_table.add_column("Count", justify="right", style="magenta")
            term_table.add_row("Checkmate", str(checkmate_wins))
            term_table.add_row("Time Out", str(time_wins))
            term_table.add_row("Resignation", str(resignation_wins))
            term_table.add_row("Other / Unknown", str(other_wins))
            
            console.print(term_table)

if __name__ == '__main__':
    cli()
