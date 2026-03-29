import os
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from google import genai

# Use local data folder
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma")

class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        # Initializes client with GEMINI_API_KEY from environment automatically
        self.client = genai.Client()

    def __call__(self, input: Documents) -> Embeddings:
        """Embeds a list of strings."""
        if not input:
            return []
        
        response = self.client.models.embed_content(
            model='text-embedding-004',
            contents=input
        )
        return [list(e.values) for e in response.embeddings]

def get_chroma_client():
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)

def get_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="game_analyses",
        embedding_function=GeminiEmbeddingFunction()
    )

def add_analysis_embedding(game_id: str, phase: str, analysis_text: str, metadata: dict):
    """
    Chunks and embeds an analysis text for a given phase and game.
    """
    collection = get_collection()
    
    # Store combining data points
    combined_meta = {
        "game_id": game_id,
        "phase": phase,
        **metadata
    }
    
    # Unique ID for Chroma
    doc_id = f"{game_id}_{phase}"
    
    collection.add(
        documents=[analysis_text], 
        metadatas=[combined_meta], 
        ids=[doc_id]
    )

def query_analyses(query_text: str, n_results: int = 5):
    """
    Finds the most similar past game analyses for a user query.
    """
    collection = get_collection()
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    return results
