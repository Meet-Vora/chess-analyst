import pytest
from unittest.mock import patch, MagicMock
from source import vectordb

@patch('source.vectordb.genai.Client')
def test_embedding_function_unrolls_lists(mock_client_class):
    """
    Verifies that the GeminiEmbeddingFunction strictly iterates individually over 
    arrays of string arrays, guaranteeing it bypasses the Google SDK multi-part object bug.
    """
    # Setup mock genai.Client
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    # Setup the mock shapes that google returns (response.embeddings.values is an array of floats)
    mock_response = MagicMock()
    mock_embed = MagicMock()
    # Let's say our embedding dimension is tiny for this test
    mock_embed.values = [0.1, 0.2, 0.3]
    mock_response.embeddings = mock_embed
    
    # Tell the SDK to return this object natively whenever called
    mock_client.models.embed_content.return_value = mock_response

    # Initialize our database hook
    embedder = vectordb.GeminiEmbeddingFunction()

    # Pass in three generic playstyle analyses
    input_docs = ["First sentence.", "Second sentence.", "Third sentence."]
    result = embedder(input_docs)

    # 1. Did it successfully map and return all 3 vectors to ChromaDB?
    assert len(result) == 3
    
    # 2. **CRITICAL TEST**: Ensure the client physically fired the network call EXACTLY 3 times.
    # If this is 1, the test fails, meaning we accidentally passed `input_docs` directly to Google
    # which we structurally know will trigger an immediate 404 NOT_FOUND crash!
    assert mock_client.models.embed_content.call_count == 3
