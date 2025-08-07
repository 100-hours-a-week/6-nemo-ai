from typing import List
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re


def is_similar_to_any(new_text: str, past_texts: List[str], threshold: float = 0.9) -> bool:
    if not past_texts:
        return False

    try:
        # Import here to avoid circular imports
        from app.models.embedding_model import embed

        all_texts = past_texts + [new_text]
        vectors = embed(all_texts)
        if len(vectors) != len(all_texts):
            return False

        similarities = cosine_similarity([vectors[-1]], vectors[:-1])[0]
        return any(score > threshold for score in similarities)
    except Exception:
        return False


def clean_text(text: str) -> str:
    if not text:
        return ""

    # Remove excessive whitespace
    text = " ".join(text.split())

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def validate_non_empty(value: str, field_name: str = "field") -> str:
    if not value or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    return value.strip()


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    if not text:
        return []

    text = re.sub(r'[^\w\s가-힣]', ' ', text.lower())
    words = text.split()

    korean_stopwords = {
        '이', '그', '저', '의', '를', '을', '가', '는', '에', '에서',
        '로', '으로', '와', '과', '도', '만', '까지', '부터', '하고', 
        '있는', '있다', '하는', '하다', '되는', '되다', '이다', '아니다',
        '그런', '그래서', '그리고', '또한', '하지만', '그러나', '따라서',
        '때문에', '위해', '통해', '대해', '관해', '처럼', '같이', '같은',
        '수', '것', '곳', '때', '중', '내', '외', '등', '및', '또', '더'
    }

    english_stopwords = {
        'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'as', 'are', 
        'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 
        'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might',
        'in', 'to', 'of', 'for', 'with', 'by', 'from', 'up', 'about', 
        'into', 'through', 'during', 'before', 'after', 'above', 'below'
    }

    all_stopwords = korean_stopwords | english_stopwords

    keywords = []
    for word in words:
        # Filter out stopwords, numbers, and very short words
        if (word not in all_stopwords and 
            not word.isdigit() and 
            len(word) > 1):
            keywords.append(word)

    # Remove duplicates while preserving order
    unique_keywords = []
    seen = set()
    for keyword in keywords:
        if keyword not in seen:
            unique_keywords.append(keyword)
            seen.add(keyword)

    return unique_keywords[:max_keywords]


def extract_meaningful_terms(text: str) -> List[str]:
    if not text:
        return []
        
    # Clean text - keep Korean, English, and numbers
    text = re.sub(r'[^\w\s가-힣]', ' ', text.lower())
    terms = text.split()

    # Korean stopwords
    stopwords = {
        '이', '그', '저', '의', '를', '을', '가', '는', '에', '에서',
        '로', '으로', '와', '과', '도', '만', '까지', '부터', '하고', 
        '있는', '있다', '하는', '하다', '되는', '되다', '이다'
    }

    meaningful = []
    for term in terms:
        if (len(term) > 1 and
            term not in stopwords and
            not term.isdigit()):
            meaningful.append(term)

    return meaningful


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:

    if not text or len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def normalize_korean_text(text: str) -> str:
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Normalize common Korean patterns
    # Handle repeated punctuation
    text = re.sub(r'[!]{2,}', '!', text)
    text = re.sub(r'[?]{2,}', '?', text)
    text = re.sub(r'[.]{2,}', '...', text)
    
    return text


def contains_korean(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r'[가-힣]', text))


def split_korean_english(text: str) -> tuple[List[str], List[str]]:
    if not text:
        return [], []
    
    words = text.split()
    korean_words = []
    english_words = []
    
    for word in words:
        if contains_korean(word):
            korean_words.append(word)
        elif re.match(r'^[a-zA-Z]+$', word):
            english_words.append(word.lower())
    
    return korean_words, english_words
