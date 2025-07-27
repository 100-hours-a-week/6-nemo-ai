"""
Core utility functions for the 6-NEMO-AI application.
Includes text similarity checking, validation helpers, and other cross-cutting utilities.
"""

from typing import List
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def is_similar_to_any(new_text: str, past_texts: List[str], threshold: float = 0.9) -> bool:
    """
    Check if new text is similar to any text in a list of past texts.
    
    Args:
        new_text: The text to check for similarity
        past_texts: List of texts to compare against
        threshold: Similarity threshold (0.0-1.0), default 0.9
        
    Returns:
        True if new_text is similar to any past text above threshold
    """
    if not past_texts:
        return False

    try:
        # Import here to avoid circular imports
        from app.models.e5_embeddings import embed
        
        all_texts = past_texts + [new_text]
        vectors = embed(all_texts)
        if len(vectors) != len(all_texts):
            return False

        similarities = cosine_similarity([vectors[-1]], vectors[:-1])[0]
        return any(score > threshold for score in similarities)
    except Exception:
        return False


def clean_text(text: str) -> str:
    """
    Clean and normalize text input.
    
    Args:
        text: Raw text input
        
    Returns:
        Cleaned and normalized text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = " ".join(text.split())
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def validate_non_empty(value: str, field_name: str = "field") -> str:
    """
    Validate that a string value is not empty.
    
    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        
    Returns:
        The validated value
        
    Raises:
        ValueError: If value is empty or None
    """
    if not value or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract keywords from text (simple implementation).
    
    Args:
        text: Input text
        max_keywords: Maximum number of keywords to extract
        
    Returns:
        List of extracted keywords
    """
    if not text:
        return []
    
    # Simple keyword extraction - split by whitespace and filter
    words = text.lower().split()
    
    # Filter out common stop words (basic set)
    stop_words = {
        'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'are', 
        'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 
        'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might',
        'in', 'to', 'of', 'for', 'with', 'by', 'from', 'up', 'about', 
        'into', 'through', 'during', 'before', 'after', 'above', 'below'
    }
    
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Remove duplicates while preserving order
    unique_keywords = []
    seen = set()
    for keyword in keywords:
        if keyword not in seen:
            unique_keywords.append(keyword)
            seen.add(keyword)
    
    return unique_keywords[:max_keywords]


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with optional suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
