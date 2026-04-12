import json
import litellm
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from . import vectordb

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

Please synthesize an answer mapping out the recurring themes, habits, and mistakes across these specific games. Focus on narrative, strategic concepts, and specific positional concepts rather than just win/loss counts. Be constructive and specific.
"""
    try:
        with console.status(f"[bold green]Synthesizing tactical data with {model}...[/bold green]", spinner="dots"):
            response = litellm.completion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            response_text = response.choices[0].message.content
            
        console.print("\n")
        console.print(Panel(
            Markdown(response_text),
            title="[bold cyan]🧠 AI Playstyle Analysis[/bold cyan]",
            border_style="cyan",
            expand=False
        ))
        console.print("\n")
        
        console.print("[bold green]Sources used for this analysis:[/bold green]")
        for meta in metadatas:
            console.print(f"- Game ID: {meta.get('game_id')} ({meta.get('opening')})")
            
    except Exception as e:
        console.print(f"[red]Error synthesizing final answer with {model}: {e}[/red]")
