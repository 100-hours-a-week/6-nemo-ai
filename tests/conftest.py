"""
Centralized pytest fixtures for 6-NEMO-AI testing.
Provides common fixtures for database, API clients, and test data.
"""

import pytest
from typing import Generator
import os
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "app"))

# Test configuration
TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def test_settings():
    """Test environment settings."""
    return {
        "database_url": TEST_DATABASE_URL,
        "kafka_enabled": False,
        "vector_db_enabled": True,  # Enable vector DB for tests
        "llm_enabled": False,
        "test_mode": True
    }


@pytest.fixture(scope="function")
def test_client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    try:
        from app.main import app
        client = TestClient(app)
        yield client
    except ImportError:
        pytest.skip("FastAPI app not available")


@pytest.fixture(scope="session")
def vector_test_data():
    """Sample data for vector database tests."""
    return {
        "groups": [
            {
                "id": "test-group-1",
                "title": "Python 스터디 그룹",
                "description": "초보자를 위한 파이썬 프로그래밍 스터디",
                "tags": ["python", "programming", "beginner"],
                "location": "서울 강남구"
            },
            {
                "id": "test-group-2", 
                "title": "React 개발자 모임",
                "description": "React.js 프론트엔드 개발 경험 공유",
                "tags": ["react", "frontend", "javascript"],
                "location": "서울 서초구"
            }
        ]
    }


@pytest.fixture(scope="function")
def kafka_test_config():
    """Kafka test configuration."""
    return {
        "bootstrap_servers": ["localhost:9092"],
        "test_topic": "test-nemo-chatbot",
        "group_id": "test-consumer-group"
    }


@pytest.fixture(scope="function") 
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "choices": [
            {
                "message": {
                    "content": "안녕하세요! 어떤 모임을 찾고 계신가요?"
                }
            }
        ]
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Automatically setup test environment for all tests."""
    # Set test environment variables
    os.environ["TESTING"] = "1"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    yield
    
    # Cleanup after test
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


@pytest.fixture(scope="function")
def websocket_test_client():
    """WebSocket test client."""
    from fastapi.testclient import TestClient
    try:
        from app.main import app
        client = TestClient(app)
        yield client
    except ImportError:
        pytest.skip("WebSocket client not available")


@pytest.fixture(scope="session")
def vector_db_client():
    """Vector database client for testing."""
    try:
        from app.database.vector.chroma_client import get_chroma_client
        client = get_chroma_client()
        yield client
    except ImportError:
        pytest.skip("Vector database not available")


@pytest.fixture(scope="session")
def embedding_function():
    """Embedding function for testing."""
    try:
        from app.models.e5_embeddings import embed
        yield embed
    except ImportError:
        pytest.skip("E5 embeddings not available")


# Vector database fixtures
@pytest.fixture(scope="function")
def vector_search_functions():
    """Vector search functions for testing."""
    try:
        from app.database.vector.vector_searcher import (
            search_similar_documents,
            keyword_search_documents,
            get_user_joined_group_ids,
            get_system_stats,
            category_discovery,
            semantic_booster
        )
        return {
            'search_similar_documents': search_similar_documents,
            'keyword_search_documents': keyword_search_documents,
            'get_user_joined_group_ids': get_user_joined_group_ids,
            'get_system_stats': get_system_stats,
            'category_discovery': category_discovery,
            'semantic_booster': semantic_booster
        }
    except ImportError as e:
        pytest.skip(f"Vector search functions not available: {e}")
