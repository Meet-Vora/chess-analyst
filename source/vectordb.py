import os
import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
import litellm

# Use local data folder
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma")

class LiteLLMEmbeddingFunction(EmbeddingFunction):
    def __init__(self, model_name: str = "gemini/text-embedding-004"):
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        """Embeds a list of strings using LiteLLM."""
        if not input:
            return []
            
        embeddings = []
        # Litellm supports batch embedding, but to be safe across providers, we can iterate or pass the list
        # We will try passing the list directly to litellm.embedding since most providers support it.
        try:
            response = litellm.embedding(
                model=self.model_name,
                input=input
            )
            for data in response.data:
                embeddings.append(data["embedding"])
        except Exception as e:
            # Fallback to individual embedding if batch fails
            for doc in input:
                res = litellm.embedding(model=self.model_name, input=[doc])
                embeddings.append(res.data[0]["embedding"])
                
        return embeddings

def get_chroma_client():
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)

def get_collection(embedding_model: str = "gemini/text-embedding-004"):
    client = get_chroma_client()
    return client.get_or_create_collection(
        name="game_analyses",
        embedding_function=LiteLLMEmbeddingFunction(model_name=embedding_model)
    )

def add_analysis_embedding(game_id: str, phase: str, analysis_text: str, metadata: dict, embedding_model: str = "gemini/text-embedding-004"):
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

def query_analyses(query_text: str, n_results: int = 5, embedding_model: str = "gemini/text-embedding-004"):
    """
    Finds the most similar past game analyses for a user query.
    """
    collection = get_collection(embedding_model=embedding_model)
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    return results
