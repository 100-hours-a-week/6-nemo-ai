from typing import List, Dict, Any, Literal, Optional
from src.vector_db.chroma_client import get_chroma_client
from src.models.e5_embeddings import embed
from src.core.ai_logger import get_ai_logger
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from collections import defaultdict, Counter

GROUP_COLLECTION = "group-info"
SYN_COLLECTION = "group-synthetic"
USER_COLLECTION = "user-activity"
RECOMMENDATION_THRESHOLD = 0.0
logger = get_ai_logger()

class SemanticBooster:
    def __init__(self):
        self.term_embeddings = {}
        self.semantic_clusters = {}
        self.similarity_cache = {}
        
    def build_semantic_relationships(self, documents: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """Build semantic relationships using embedding similarity"""
        # Extract all meaningful terms from documents
        all_terms = set()
        term_contexts = defaultdict(list)
        
        for doc, meta in zip(documents, metadatas):
            terms = self._extract_meaningful_terms(doc)
            tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
            category = meta.get("category", "")
            
            for term in terms + tags + ([category] if category else []):
                if len(term) > 1:
                    all_terms.add(term)
                    term_contexts[term].append(doc)
        
        # Generate embeddings for all terms
        if all_terms:
            terms_list = list(all_terms)
            try:
                # Get embeddings for all terms at once
                embeddings = embed([f"term: {term}" for term in terms_list])
                for term, embedding in zip(terms_list, embeddings):
                    self.term_embeddings[term] = np.array(embedding)
                
                # Build similarity matrix and find clusters
                self._build_similarity_clusters(terms_list)
                
            except Exception as e:
                logger.warning(f"[AI] Failed to generate term embeddings: {str(e)}")
    
    def _build_similarity_clusters(self, terms: List[str]) -> None:
        """Build semantic clusters based on embedding similarity"""
        if len(terms) < 2:
            return
            
        # Calculate pairwise similarities
        embeddings_matrix = np.array([self.term_embeddings[term] for term in terms])
        similarity_matrix = cosine_similarity(embeddings_matrix)
        
        # Find related terms for each term
        for i, term in enumerate(terms):
            related_terms = {}
            similarities = similarity_matrix[i]
            
            for j, other_term in enumerate(terms):
                if i != j:
                    sim_score = similarities[j]
                    if sim_score > 0.7:  # High similarity threshold
                        related_terms[other_term] = float(sim_score)
            
            if related_terms:
                self.semantic_clusters[term] = related_terms
        
        logger.info(f"[AI] Built semantic clusters for {len(self.semantic_clusters)} terms")
    
    def _extract_meaningful_terms(self, text: str) -> List[str]:
        """Extract meaningful Korean terms"""
        import re
        text = re.sub(r'[^\w\s가-힣]', ' ', text.lower())
        terms = text.split()
        
        # Filter meaningful terms
        stopwords = {'이', '그', '저', '의', '를', '을', '가', '는', '에', '에서', '로', '으로', '와', '과', '도', '만', '까지', '부터'}
        meaningful_terms = []
        
        for term in terms:
            if (len(term) > 1 and 
                term not in stopwords and
                not term.isdigit() and
                not re.match(r'^[a-zA-Z]+$', term)):  # Skip pure English unless important
                meaningful_terms.append(term)
        
        return meaningful_terms
    
    def get_related_terms(self, query_terms: List[str], threshold: float = 0.7) -> Dict[str, float]:
        """Get semantically related terms using embedding similarity"""
        if not self.term_embeddings:
            return {}
            
        related = {}
        
        for term in query_terms:
            # Direct lookup in clusters
            if term in self.semantic_clusters:
                for related_term, score in self.semantic_clusters[term].items():
                    if score > threshold:
                        related[related_term] = score
            
            # Dynamic similarity check for new terms
            elif term in self.term_embeddings:
                term_embedding = self.term_embeddings[term]
                for other_term, other_embedding in self.term_embeddings.items():
                    if other_term != term and other_term not in query_terms:
                        sim = float(cosine_similarity([term_embedding], [other_embedding])[0][0])
                        if sim > threshold:
                            related[other_term] = sim
        
        return related
    
    def find_similar_terms_for_query(self, query: str, threshold: float = 0.75) -> Dict[str, float]:
        """Find semantically similar terms for entire query"""
        if not self.term_embeddings:
            return {}
        
        try:
            # Get query embedding
            query_embedding = embed([f"query: {query}"])[0]
            query_embedding = np.array(query_embedding)
            
            similar_terms = {}
            for term, term_embedding in self.term_embeddings.items():
                sim = float(cosine_similarity([query_embedding], [term_embedding])[0][0])
                if sim > threshold:
                    similar_terms[term] = sim
            
            return similar_terms
            
        except Exception as e:
            logger.warning(f"[AI] Failed to find similar terms: {str(e)}")
            return {}

semantic_booster = SemanticBooster()

def search_similar_documents(
    query: str,
    top_k: int = 5,
    collection: Literal["group-info", "user-activity", "group-synthetic"] = "group-info",
    where: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(name=collection, embedding_function=embed)

        # Bootstrap semantic relationships if needed
        if not semantic_booster.term_embeddings:
            _bootstrap_semantic_learning(col)

        # Get semantically similar terms using embeddings
        query_terms = semantic_booster._extract_meaningful_terms(query)
        
        # Get related terms through embedding similarity
        term_relations = semantic_booster.get_related_terms(query_terms, threshold=0.75)
        query_relations = semantic_booster.find_similar_terms_for_query(query, threshold=0.75)
        
        # Combine both approaches
        all_related_terms = {}
        for term, score in term_relations.items():
            all_related_terms[term] = score
        for term, score in query_relations.items():
            all_related_terms[term] = max(all_related_terms.get(term, 0), score)
        
        # Enhance query with semantically similar terms
        enhanced_query = query
        if all_related_terms:
            # Pick top 2-3 most similar terms
            top_related = sorted(all_related_terms.items(), key=lambda x: x[1], reverse=True)[:2]
            enhancement = " ".join([term for term, score in top_related if score > 0.75])
            if enhancement:
                enhanced_query = f"{query} {enhancement}"

        # E5 models benefit from query prefix for search
        query_with_prefix = f"query: {enhanced_query}"
        vector = embed(query_with_prefix)[0]
        results = col.query(
            query_embeddings=[vector],
            n_results=top_k * 3,  # Get more for re-ranking
            include=["documents", "metadatas", "distances"],
            where=where,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        joined_ids: set[str] = set()
        if user_id:
            joined_ids = get_user_joined_group_ids(user_id)

        filtered = []
        origin = "real" if collection == GROUP_COLLECTION else "synthetic"
        for doc, meta, dist in zip(documents, metadatas, distances):
            base_score = 1 - dist
            group_id = meta.get("groupId")
            if base_score < RECOMMENDATION_THRESHOLD:
                continue
            if user_id and group_id in joined_ids:
                continue
            
            # Apply semantic boosting based on embedding similarities
            semantic_boost = _calculate_semantic_boost(doc, meta, query, all_related_terms)
            final_score = min(1.0, base_score + semantic_boost)
            
            filtered.append({
                "id": meta.get("id"),
                "text": doc,
                "metadata": meta,
                "score": final_score,
                "base_score": base_score,
                "semantic_boost": semantic_boost,
                "origin": origin,
                "related_terms": list(all_related_terms.keys())[:3],  # For debugging
            })
        
        # Sort by enhanced score and return top_k
        filtered.sort(key=lambda x: x["score"], reverse=True)
        return filtered[:top_k]
        
    except Exception as e:
        logger.exception(f"[AI] search_similar_documents 실패: {str(e)}")
        return []

def _bootstrap_semantic_learning(col) -> None:
    """Bootstrap semantic learning from existing documents"""
    try:
        result = col.get(include=["documents", "metadatas"])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        
        if documents:
            semantic_booster.build_semantic_relationships(documents, metadatas)
            logger.info(f"[AI] Built semantic relationships from {len(documents)} documents")
    except Exception as e:
        logger.warning(f"[AI] Failed to bootstrap semantic learning: {str(e)}")

def _calculate_semantic_boost(doc: str, meta: Dict[str, Any], query: str, related_terms: Dict[str, float]) -> float:
    """Calculate semantic boost based on embedding similarities"""
    if not related_terms:
        return 0.0
    
    doc_lower = doc.lower()
    tags = meta.get("tags", "").lower()
    category = meta.get("category", "").lower()
    combined_text = f"{doc_lower} {tags} {category}"
    
    boost = 0.0
    matches = 0
    
    for related_term, confidence in related_terms.items():
        if related_term in combined_text:
            # Higher boost for higher similarity
            term_boost = confidence * 0.25  # Scale the similarity score
            boost += term_boost
            matches += 1
    
    # Apply diminishing returns for multiple matches
    if matches > 0:
        boost = boost * (1.0 / (1.0 + 0.1 * (matches - 1)))
    
    return min(boost, 0.4)  # Cap total semantic boost


def keyword_search_documents(
    query: str,
    top_k: int = 5,
    collection: Literal["group-info", "group-synthetic"] = "group-info",
    where: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Enhanced keyword search with semantic term expansion."""
    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(name=collection, embedding_function=embed)

        result = col.get(where=where, include=["documents", "metadatas"])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        ids = result.get("ids", [])

        if not documents:
            return []

        # Bootstrap semantic learning if needed
        if not semantic_booster.term_embeddings:
            semantic_booster.build_semantic_relationships(documents, metadatas)

        # Get semantically related terms for query expansion
        query_terms = semantic_booster._extract_meaningful_terms(query)
        related_terms = semantic_booster.get_related_terms(query_terms, threshold=0.75)
        query_related = semantic_booster.find_similar_terms_for_query(query, threshold=0.75)
        
        # Combine related terms
        all_related = {}
        for term, score in related_terms.items():
            all_related[term] = score
        for term, score in query_related.items():
            all_related[term] = max(all_related.get(term, 0), score)
        
        # Expand query with most similar terms
        expanded_query = query
        if all_related:
            top_related = sorted(all_related.items(), key=lambda x: x[1], reverse=True)[:2]
            expansion = " ".join([term for term, score in top_related if score > 0.75])
            if expansion:
                expanded_query = f"{query} {expansion}"

        # Use expanded query for TF-IDF
        vectorizer = TfidfVectorizer(ngram_range=(1, 2))  # Include bigrams
        doc_vectors = vectorizer.fit_transform(documents)
        query_vec = vectorizer.transform([expanded_query])
        scores = (doc_vectors @ query_vec.T).toarray().ravel()

        joined_ids: set[str] = set()
        if user_id:
            joined_ids = get_user_joined_group_ids(user_id)

        order = list(np.argsort(scores)[::-1])
        results: List[Dict[str, Any]] = []
        origin = "real" if collection == GROUP_COLLECTION else "synthetic"
        for idx in order:
            meta = metadatas[idx]
            group_id = meta.get("groupId")
            if user_id and group_id in joined_ids:
                continue
            
            # Add semantic boost to keyword scores
            base_score = float(scores[idx])
            semantic_boost = _calculate_semantic_boost(documents[idx], meta, query, all_related)
            final_score = base_score + semantic_boost
            
            results.append({
                "id": ids[idx],
                "text": documents[idx],
                "metadata": meta,
                "score": final_score,
                "base_score": base_score,
                "semantic_boost": semantic_boost,
                "origin": origin,
            })
            if len(results) >= top_k:
                break
        return results
    except Exception as e:
        logger.exception(f"[AI] keyword_search_documents 실패: {str(e)}")
        return []

def get_user_joined_group_ids(user_id: str) -> set[str]:
    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(name=USER_COLLECTION, embedding_function=embed)

        result = col.get(where={"userId": user_id}, include=["metadatas"])
        return {
            meta.get("groupId")
            for meta in result.get("metadatas", [])
            if meta.get("groupId")
        }
    except Exception as e:
        logger.warning(f"[AI] 유저 참여 그룹 조회 실패: {str(e)}")
        return set()

def get_semantic_learning_stats() -> Dict[str, Any]:
    """Get statistics about semantic learning progress"""
    try:
        return {
            "semantic_enhancement_enabled": True,
            "total_term_embeddings": len(semantic_booster.term_embeddings),
            "semantic_clusters": len(semantic_booster.semantic_clusters),
            "total_relationships": sum(len(clusters) for clusters in semantic_booster.semantic_clusters.values())
        }
    except Exception as e:
        logger.warning(f"[AI] Failed to get semantic stats: {str(e)}")
        return {"semantic_enhancement_enabled": False, "error": str(e)}

if __name__ == "__main__":
    from pprint import pprint

    # Test semantic enhancement
    print("=== Semantic Enhancement Test ===")
    stats = get_semantic_learning_stats()
    print("Enhancement stats:", stats)
    
    user_id = "u2"
    joined_ids = get_user_joined_group_ids(user_id)
    print(f"\n유저 {user_id}가 참여 중인 group_id 리스트:")
    pprint(joined_ids)

    # Test queries that should find semantic relationships
    test_queries = [
        "풋살 하고싶어요",        # Should find 축구 groups  
        "축구 모임 찾아요",       # Should find 풋살 groups
        "조용한 독서모임",        # Should find 책, 도서 related
        "맛집탐방 같이해요",      # Should find 음식, 카페 related
        "농구 하실분"            # Should find basketball, 스포츠 related
    ]
    
    for query in test_queries:
        print(f"\n=== Query: '{query}' ===")
        results = search_similar_documents(query, top_k=3)
        for i, r in enumerate(results, 1):
            print(f"{i}. ID: {r['id']}")
            print(f"   GroupID: {r['metadata'].get('groupId')}")
            print(f"   Score: {r['score']:.3f} (base: {r.get('base_score', 0):.3f}, boost: {r.get('semantic_boost', 0):.3f})")
            if 'related_terms' in r:
                print(f"   Related terms: {r['related_terms']}")
            print(f"   Text: {r['text'][:100]}...")
            print("-" * 50)