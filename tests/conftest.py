"""
Global test configuration and fixtures.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os

# Mock Google Cloud and external services at import time
sys.modules['google.cloud.aiplatform'] = MagicMock()
sys.modules['google.oauth2.service_account'] = MagicMock()
sys.modules['vertexai.preview.generative_models'] = MagicMock()
sys.modules['vertexai.language_models'] = MagicMock()
sys.modules['google.api_core.exceptions'] = MagicMock()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment with required mocks and environment variables."""
    # Mock environment variables that might be missing in tests
    os.environ.setdefault('PROJECT_ID', 'test-project')
    os.environ.setdefault('REGION', 'us-central1')
    os.environ.setdefault('CREDENTIAL_PATH', 'test-credentials.json')
    os.environ.setdefault('TXTGEN_MODEL_ID', 'test-model')
    os.environ.setdefault('EMBEDDING_MODEL_ID', 'test-embedding-model')
    
    # Mock ChromaDB at module level
    mock_collection = Mock()
    mock_collection.add.return_value = None
    mock_collection.query.return_value = {
        'ids': [['mock_id_1', 'mock_id_2']],
        'documents': [['Mock document 1', 'Mock document 2']],
        'distances': [[0.1, 0.2]]
    }
    mock_collection.count.return_value = 100
    mock_collection.peek.return_value = {'ids': ['sample'], 'documents': ['sample doc']}
    
    mock_client = Mock()
    mock_client.get_or_create_collection.return_value = mock_collection
    
    with patch('chromadb.PersistentClient', return_value=mock_client):
        yield


@pytest.fixture(scope="session")
def app():
    """Application fixture."""
    from app.main import app
    return app


@pytest.fixture(scope="function")
def client(app):
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture(scope="function")
def mock_vector_service():
    """Mock vector service for consistent test results."""
    with patch('app.services.shared.vector_service.VectorService') as mock:
        mock_instance = Mock()
        mock_instance.search.return_value = [
            {
                "text": "Test group description",
                "metadata": {"groupId": 1, "title": "Test Group"}
            }
        ]
        mock_instance.get_user_joined_groups.return_value = set()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture(scope="function")
def mock_llm_service():
    """Mock LLM service for fast tests."""
    with patch('app.models.text_generation_model.call_gemma_vllm_api') as mock:
        mock.return_value = '{"question": "Test question", "options": ["Option 1", "Option 2"]}'
        yield mock


@pytest.fixture(scope="function") 
def mock_chatbot_question_service():
    """Mock chatbot question service for integration tests."""
    with patch('app.services.v2.chatbot.handle_combined_question') as mock:
        mock.return_value = {
            "question": "Test question",
            "options": ["Option 1", "Option 2"]
        }
        yield mock


@pytest.fixture(scope="function")
def mock_chatbot_recommendation_service():
    """Mock chatbot recommendation service for integration tests."""
    with patch('app.services.v2.chatbot.handle_combined_recommendations') as mock:
        mock.return_value = {
            "groupId": 1,
            "reason": "Test recommendation reason"
        }
        yield mock


@pytest.fixture(scope="function")
def mock_vertex_client():
    """Mock vertex AI client."""
    with patch('app.core.vertex_client.generate_content') as mock_gen, \
         patch('app.core.vertex_client.limited_generate') as mock_limited, \
         patch('app.core.vertex_client.smart_generate') as mock_smart, \
         patch('app.core.vertex_client.embed_model') as mock_embed_model:
        
        mock_gen.return_value = "Mock AI response"
        mock_limited.return_value = "Mock limited response"
        mock_smart.return_value = "Mock smart response"
        
        # Mock the embedding model
        mock_embedding = Mock()
        mock_embedding.values = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_embed_model.get_embeddings.return_value = [mock_embedding]
        
        yield {
            'generate_content': mock_gen,
            'limited_generate': mock_limited,
            'smart_generate': mock_smart,
            'embed_model': mock_embed_model
        }


@pytest.fixture(scope="function")
def mock_embeddings():
    """Mock embedding service."""
    with patch('app.services.v1.embed.embed') as mock:
        # Return consistent mock embeddings
        mock.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5] for _ in range(10)]  # Mock 5-dim embeddings
        yield mock


@pytest.fixture(scope="function")
def vector_search_functions():
    """
    Fixture providing vector search functions for integration tests.
    
    This fixture provides implementations that work with mocked services
    but simulate the real behavior of the vector search system.
    """
    
    def mock_get_user_joined_group_ids(user_id: str):
        """Mock function to get user's joined group IDs."""
        # Return some mock group IDs based on user_id
        if user_id == "20":
            return {"group_1", "group_2", "group_3"}
        elif user_id == "15":
            return {"group_4", "group_5"}
        elif user_id in ["u2", "u5"]:
            return {"group_6"}
        else:
            return set()

    def mock_search_similar_documents(query: str, top_k: int = 3, user_id: str = None):
        """Mock function for vector similarity search using real service structure."""
        # Return mock search results with realistic structure
        results = []
        for i in range(min(top_k, 3)):
            results.append({
                "text": f"Mock group description {i+1} for query: {query[:20]}...",
                "metadata": {
                    "groupId": f"group_{i+1}",
                    "title": f"Mock Group {i+1}",
                    "category": "sports" if "축구" in query or "풋살" in query else "general"
                },
                "score": 0.9 - (i * 0.1)
            })
        return results

    def mock_keyword_search_documents(query: str, top_k: int = 3, user_id: str = None):
        """Mock function for keyword search."""
        # Return mock keyword search results
        results = []
        for i in range(min(top_k, 2)):
            results.append({
                "text": f"Keyword match {i+1} for: {query}",
                "metadata": {
                    "groupId": f"keyword_group_{i+1}",
                    "title": f"Keyword Group {i+1}"
                },
                "score": 0.8 - (i * 0.2)
            })
        return results

    def mock_get_system_stats():
        """Mock function to get system statistics."""
        return {
            "system_ready": True,
            "semantic_terms": 150,
            "categories_discovered": 25,
            "total_documents": 1000,
            "last_update": "2024-01-15T10:00:00Z"
        }

    # Mock category discovery class
    class MockCategoryDiscovery:
        def infer_query_categories(self, query: str):
            """Mock category inference based on query content."""
            categories = []
            
            # Simple keyword-based category mapping
            if any(word in query.lower() for word in ["축구", "풋살", "soccer", "football"]):
                categories = [("sports", 0.9), ("football", 0.8), ("soccer", 0.7)]
            elif any(word in query.lower() for word in ["개발", "프로그래밍", "programming", "development"]):
                categories = [("programming", 0.9), ("development", 0.8), ("tech", 0.7)]
            elif any(word in query.lower() for word in ["영화", "movie", "film"]):
                categories = [("culture", 0.9), ("movies", 0.8), ("discussion", 0.7)]
            elif any(word in query.lower() for word in ["요리", "음식", "cooking", "food"]):
                categories = [("cooking", 0.9), ("food", 0.8), ("lifestyle", 0.6)]
            else:
                categories = [("general", 0.5), ("social", 0.4), ("community", 0.3)]
            
            return categories

    # Mock semantic booster class
    class MockSemanticBooster:
        def get_related_terms(self, term: str, threshold: float = 0.7):
            """Mock semantic term relationships."""
            related_terms = {
                "축구": {"풋살": 0.9, "soccer": 0.8, "football": 0.8},
                "풋살": {"축구": 0.9, "soccer": 0.8},
                "개발": {"프로그래밍": 0.9, "programming": 0.8, "coding": 0.7},
                "프로그래밍": {"개발": 0.9, "programming": 0.9, "코딩": 0.8},
                "요리": {"음식": 0.8, "cooking": 0.9, "레시피": 0.7},
                "음식": {"요리": 0.8, "food": 0.9, "맛집": 0.7}
            }
            
            # Filter by threshold
            result = {}
            for related_term, score in related_terms.get(term, {}).items():
                if score >= threshold:
                    result[related_term] = score
            
            return result

    # Create mock instances
    category_discovery = MockCategoryDiscovery()
    semantic_booster = MockSemanticBooster()

    # Return dictionary of functions
    return {
        'get_user_joined_group_ids': mock_get_user_joined_group_ids,
        'search_similar_documents': mock_search_similar_documents,
        'keyword_search_documents': mock_keyword_search_documents,
        'get_system_stats': mock_get_system_stats,
        'category_discovery': category_discovery,
        'semantic_booster': semantic_booster
    }


@pytest.fixture(scope="function", autouse=True)
def disable_logging():
    """Disable verbose logging during tests."""
    import logging
    logging.getLogger().setLevel(logging.WARNING)


# Test session configuration
def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "real_services: tests that use real external services"
    )
    config.addinivalue_line(
        "markers", "mock_only: tests that should only use mocks"
    )
    config.addinivalue_line(
        "markers", "integration: integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: unit tests"
    )
    config.addinivalue_line(
        "markers", "vector: vector database tests"
    )
    config.addinivalue_line(
        "markers", "websocket: websocket tests"
    )
    config.addinivalue_line(
        "markers", "kafka: kafka integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: slow running tests"
    )
    config.addinivalue_line(
        "markers", "performance: performance tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Auto-mark performance tests as slow
        if "performance" in item.name.lower():
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.performance)
        
        # Auto-mark websocket tests
        if "websocket" in item.name.lower() or "ws" in item.name.lower():
            item.add_marker(pytest.mark.websocket)
        
        # Auto-mark integration tests in integration folder
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Auto-mark unit tests in unit folder
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)


# Skip configuration for missing dependencies
def pytest_runtest_setup(item):
    """Setup for individual tests."""
    # Skip websocket tests if dependencies not available
    if item.get_closest_marker("websocket"):
        try:
            import websockets
        except ImportError:
            pytest.skip("WebSocket dependencies not available")
    
    # Skip Kafka tests if not available
    if item.get_closest_marker("kafka"):
        try:
            # Check if Kafka is available
            pass  # Add actual Kafka check here if needed
        except Exception:
            pytest.skip("Kafka not available")
