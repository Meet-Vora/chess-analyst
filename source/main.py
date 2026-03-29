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
def analyze(limit: int, dry_run: bool, game_id: str):
    """Analyzes unreviewed games via Gemini and embeds insights into ChromaDB."""
    analyzer.analyze_games(limit=limit, dry_run=dry_run, game_id=game_id)

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
        
        table = Table(title="🗄️ Database Statistics", box=box.ROUNDED)
        table.add_column("Metric", justify="right", style="cyan", no_wrap=True)
        table.add_column("Count", style="magenta")
        
        table.add_row("Total Games Ingested", str(total_games))
        table.add_row("Games Completely Analyzed", str(analyzed_games))
        
        console.print(table)

if __name__ == '__main__':
    cli()
