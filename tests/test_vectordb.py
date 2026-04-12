import pytest
from unittest.mock import patch, MagicMock
from source import vectordb

@patch('source.vectordb.litellm.embedding')
def test_embedding_function_unrolls_lists(mock_embedding):
    """
    Verifies that the LiteLLMEmbeddingFunction returns embeddings properly.
    """
    
    # Setup the mock shapes that google returns (response.embeddings.values is an array of floats)
    mock_response = MagicMock()
    # Emulate Litellm's EmbeddingResponse. Litellm returns response.data as list of dicts.
    mock_response.data = [
        {"embedding": [0.1, 0.2, 0.3]},
        {"embedding": [0.1, 0.2, 0.3]},
        {"embedding": [0.1, 0.2, 0.3]}
    ]
    mock_embedding.return_value = mock_response

    # Initialize our database hook
    embedder = vectordb.LiteLLMEmbeddingFunction()

    # Pass in three generic playstyle analyses
    input_docs = ["First sentence.", "Second sentence.", "Third sentence."]
    result = embedder(input_docs)

    # 1. Did it successfully map and return all 3 vectors to ChromaDB?
    assert len(result) == 3
    
    # 2. **CRITICAL TEST**: Ensure litellm.embedding was called
    assert mock_embedding.call_count == 1
