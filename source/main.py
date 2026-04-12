import click
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

# Load environment logic right away, so SDK clients work correctly
load_dotenv()

console = Console()

@click.group()
def cli():
    """Chess Analyst CLI: A pipeline for reasoning over playstyles."""
    pass

MODEL_ALIASES = {
    "gemini": "gemini/gemini-2.5-flash",
    "gemini-flash": "gemini/gemini-2.5-flash",
    "gemini-pro": "gemini/gemini-2.5-pro",
    "claude": "anthropic/claude-3-5-sonnet-latest",
    "claude-sonnet": "anthropic/claude-3-5-sonnet-latest",
    "gpt": "openai/gpt-4o",
    "gpt-4o": "openai/gpt-4o",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "grok": "xai/grok-2-latest",
}

def resolve_model(model_str: str) -> str:
    """Returns the litellm fully qualified model string for an alias, or the string itself."""
    return MODEL_ALIASES.get(model_str.lower(), model_str)

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
@click.option('--model', default='gemini', help="Model to use for analysis (alias or litellm string, e.g. 'claude', 'gpt-4o').")
@click.option('--embedding-model', default='gemini/text-embedding-004', help="Model to use for embedding (e.g. 'text-embedding-3-small').")
def analyze(limit: int, dry_run: bool, game_id: str, model: str, embedding_model: str):
    """Analyzes unreviewed games and embeds insights into ChromaDB."""
    resolved_model = resolve_model(model)
    analyzer.analyze_games(
        limit=limit, 
        dry_run=dry_run, 
        game_id=game_id, 
        model=resolved_model,
        embedding_model=embedding_model
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
        
    for a in analyses:
        # Build the phase text natively as markdown
        content = f"**Summary:** {a['narrative_summary']}\n\n"
        content += f"**Mistakes:** {', '.join(a['mistakes']) if a.get('mistakes') else 'None'}\n\n"
        content += f"**Patterns:** {', '.join(a['patterns_identified']) if a.get('patterns_identified') else 'None'}"
        
        if a.get('critical_moments'):
            content += f"\n\n**Critical Moments:** {', '.join(a['critical_moments'])}"
        if a.get('tactical_motifs_missed'):
            content += f"\n\n**Missed Tactics:** {', '.join(a['tactical_motifs_missed'])}"
            
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
@click.option('--model', default='gemini', help="Model to use for synthesis (alias or litellm string, e.g. 'claude', 'gpt-4o').")
@click.option('--embedding-model', default='gemini/text-embedding-004', help="Model to use for embedding vector search.")
def query(question: str, n_results: int, model: str, embedding_model: str):
    """Queries playstyle history by searching past game analyses."""
    console.print(f"[bold cyan]Querying history for:[/bold cyan] {question}")
    resolved_model = resolve_model(model)
    retriever.query_playstyle(
        question=question, 
        n_results=n_results, 
        model=resolved_model,
        embedding_model=embedding_model
    )

@cli.command()
def stats():
    """Shows statistics across the ingestion and analysis pipeline."""
    db.init_db()
    with db.get_db() as conn:
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
        
        # Win / Loss / Draw query
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
        
        wld_table = Table(title=f"🏆 Win/Loss Record for '{username}'", box=box.ROUNDED)
        wld_table.add_column("Color", justify="left", style="white", no_wrap=True)
        wld_table.add_column("Wins", justify="right", style="bold green")
        wld_table.add_column("Losses", justify="right", style="bold red")
        wld_table.add_column("Draws", justify="right", style="bold yellow")
        
        wld_table.add_row("⚪ White", str(wld["white_wins"] or 0) if wld else "0", str(wld["white_losses"] or 0) if wld else "0", str(wld["white_draws"] or 0) if wld else "0")
        wld_table.add_row("⚫ Black", str(wld["black_wins"] or 0) if wld else "0", str(wld["black_losses"] or 0) if wld else "0", str(wld["black_draws"] or 0) if wld else "0")
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
            
            term_table = Table(title="🗡️ How You Win", box=box.ROUNDED)
            term_table.add_column("Condition", justify="left", style="cyan")
            term_table.add_column("Count", justify="right", style="magenta")
            term_table.add_row("Checkmate", str(checkmate_wins))
            term_table.add_row("Time Out", str(time_wins))
            term_table.add_row("Resignation", str(resignation_wins))
            term_table.add_row("Other / Unknown", str(other_wins))
            
            console.print(term_table)

if __name__ == '__main__':
    cli()
