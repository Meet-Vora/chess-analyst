import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
import requests
import os

from . import model_config

# Use local data folder
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma")

class GoogleEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        """Embeds strings purely using the native Google GenAI REST API."""
        if not input:
            return []
            
        embeddings = []
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in .env")
            
        model = model_config.EMBEDDING_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"
        
        for doc in input:
            data = {
                "model": f"models/{model}",
                "content": {"parts": [{"text": doc}]}
            }
            resp = requests.post(url, json=data)
            
            if resp.status_code != 200:
                raise Exception(f"Google API Error: {resp.text}")
                
            embeddings.append(resp.json()["embedding"]["values"])
            
        return embeddings

def get_chroma_client():
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)

def get_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="game_analyses",
        embedding_function=GoogleEmbeddingFunction()
    )

def add_analysis_embedding(game_id: str, phase: str, analysis_text: str, metadata: dict):
    """
    Chunks and embeds an analysis text for a given phase and game.
    """
    collection = get_collection(embedding_model=embedding_model)
    
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
