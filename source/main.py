import click
from rich.console import Console
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

@cli.command()
@click.argument('pgn_file', type=click.Path(exists=True))
def ingest(pgn_file: str):
    """Ingests a PGN file and stores games into SQLite."""
    console.print(f"[bold cyan]Ingesting games from:[/bold cyan] {pgn_file}")
    
    saved = parser.parse_and_store_pgn(pgn_file)
    
    if saved > 0:
        console.print(f"[bold green]Successfully saved {saved} new games to the database![/bold green]")
    else:
        console.print("[yellow]No new games were saved (all duplicates or parse errors).[/yellow]")

@cli.command()
@click.option('--limit', default=10, help="Maximum number of games to analyze in this run.")
@click.option('--dry-run', is_flag=True, help="Show which games would be analyzed without invoking the LLM.")
def analyze(limit: int, dry_run: bool):
    """Analyzes unreviewed games via Gemini and embeds insights into ChromaDB."""
    analyzer.analyze_games(limit=limit, dry_run=dry_run)

@cli.command()
@click.argument('question')
@click.option('--n-results', default=5, help="Number of related game phases to synthesize over.")
def query(question: str, n_results: int):
    """Queries playstyle history by searching past game analyses."""
    console.print(f"[bold cyan]Querying history for:[/bold cyan] {question}")
    retriever.query_playstyle(question=question, n_results=n_results)

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
        
        console.print(f"[green]Total Games Ingested:[/green] {total_games}")
        console.print(f"[green]Total Games Analyzed:[/green] {analyzed_games}")

if __name__ == '__main__':
    cli()
