import json
import litellm
import instructor
from pydantic import BaseModel, Field
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich import box

from . import vectordb

class Theme(BaseModel):
    name: str = Field(description="Short name of the recurring theme or mistake (e.g., 'Weakness on Long Diagonal', 'Time Trouble Blunders')")
    description: str = Field(description="A concise, 1-2 sentence explanation of how this theme appears in the games and why it's happening.")
    frequency: str = Field(description="How often this appears in the games provided (e.g., 'Often', 'Rarely')")

class QuerySynthesis(BaseModel):
    summary: str = Field(description="A concise 2-3 sentence overall summary of your answer to the query.")
    key_themes: List[Theme] = Field(description="A list of 2-4 primary recurring patterns, themes, or mistakes mapping to the query.")
    actionable_advice: str = Field(description="One very short, actionable sentence of advice on how to improve this specific issue in the future.")

console = Console()

def query_playstyle(question: str, n_results: int = 5, model: str = "gemini/gemini-2.5-flash", embedding_model: str = "gemini/text-embedding-004"):
    """
    Given a natural language query, search the vector DB for relevant game analyses, 
    and ask the model to synthesize an answer.
    """
    try:
        results = vectordb.query_analyses(query_text=question, n_results=n_results, embedding_model=embedding_model)
    except Exception as e:
        console.print(f"[red]Error querying ChromaDB: {e}[/red]")
        return
    
    if not results or not results['documents'] or not results['documents'][0]:
        console.print("[yellow]No relevant historical analyses found in Vector DB. Have you analyzed games yet?[/yellow]")
        return
        
    documents = results['documents'][0]
    metadatas = results['metadatas'][0]
    
    # Combine the context for the prompt
    context_blocks = []
    for i, (doc, meta) in enumerate(zip(documents, metadatas)):
        game_id = meta.get("game_id", "Unknown")
        opening = meta.get("opening", "Unknown")
        phase = meta.get("phase", "Unknown")
        
        block = f"[Game: {game_id} | Opening: {opening} | Phase: {phase}]\n{doc}"
        context_blocks.append(block)
        
    combined_context = "\n\n---\n\n".join(context_blocks)
    
    prompt = f"""
You are an expert chess analyst and reasoning engine helping me understand patterns in my playstyle over time.
I am asking the following question about my chess games: "{question}"

Here are the most relevant tactical insights and mistakes from my past games related to this question:

{combined_context}

Please synthesize an answer mapping out the recurring themes, habits, and mistakes across these specific games. Focus on specific strategic themes and constructive advice.
"""
    mode = instructor.Mode.GEMINI_JSON if "gemini" in model else instructor.Mode.TOOLS
    client = instructor.from_litellm(litellm.completion, mode=mode)
    try:
        with console.status(f"[bold green]Synthesizing structured tactical data with {model}...[/bold green]", spinner="dots"):
            synthesis = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_model=QuerySynthesis,
                temperature=0.3
            )
            
        console.print("\n")
        console.print(Panel(
            Markdown(synthesis.summary),
            title="[bold cyan]🧠 AI Playstyle Analysis[/bold cyan]",
            border_style="cyan",
            expand=False
        ))
        console.print("\n")
        
        table = Table(title="🔍 Key Themes & Mistakes", box=box.ROUNDED)
        table.add_column("Theme", style="bold magenta", justify="left")
        table.add_column("Frequency", style="bold yellow", justify="left")
        table.add_column("Description", style="white", justify="left")
        
        for theme in synthesis.key_themes:
            table.add_row(theme.name, theme.frequency, theme.description)
            
        console.print(table)
        console.print(f"\n[bold green]💡 Actionable Advice:[/bold green] {synthesis.actionable_advice}\n")
        
        console.print("[bold green]Sources used for this analysis:[/bold green]")
        for meta in metadatas:
            console.print(f"- Game ID: {meta.get('game_id')} ({meta.get('opening')})")
            
    except Exception as e:
        console.print(f"[red]Error synthesizing final answer with {model}: {e}[/red]")
