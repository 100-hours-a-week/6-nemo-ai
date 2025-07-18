from typing import List, Dict, Any, Literal, Optional, Set, Tuple
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.vector_db.chroma_client import get_chroma_client
from src.models.e5_embeddings import embed
from src.core.ai_logger import get_ai_logger
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from collections import defaultdict, Counter
import re

# Collections
GROUP_COLLECTION = "group-info"
SYN_COLLECTION = "group-synthetic"
USER_COLLECTION = "user-activity"
RECOMMENDATION_THRESHOLD = 0.25
logger = get_ai_logger()

class VectorBasedCategoryDiscovery:
    """Discovers categories dynamically using vector similarity instead of hardcoded keywords"""

    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        self.category_cache = {}
        self.category_embeddings = {}

    def discover_categories_from_data(self, metadatas: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract actual categories from database and cluster them by similarity"""
        # Collect all unique categories from the data
        categories = set()
        for meta in metadatas:
            category = meta.get("category", "").strip()
            if category and len(category) > 1:
                categories.add(category)

        if not categories:
            return {}

        # Generate embeddings for all categories
        try:
            categories_list = list(categories)
            embeddings = embed([f"category: {cat}" for cat in categories_list])

            # Store embeddings
            for cat, emb in zip(categories_list, embeddings):
                self.category_embeddings[cat] = np.array(emb)

            # Cluster similar categories
            category_clusters = self._cluster_similar_categories(categories_list)

            logger.info(f"[AI] Discovered {len(category_clusters)} category clusters from {len(categories)} categories")
            return category_clusters

        except Exception as e:
            logger.warning(f"[AI] Failed to discover categories: {str(e)}")
            return {}

    def _cluster_similar_categories(self, categories: List[str]) -> Dict[str, List[str]]:
        """Cluster categories by semantic similarity"""
        if len(categories) < 2:
            return {cat: [cat] for cat in categories}

        # Calculate similarity matrix
        embeddings_matrix = np.array([self.category_embeddings[cat] for cat in categories])
        similarity_matrix = cosine_similarity(embeddings_matrix)

        # Find clusters
        clusters = {}
        processed = set()

        for i, cat in enumerate(categories):
            if cat in processed:
                continue

            # Find similar categories
            similar_cats = [cat]
            for j, other_cat in enumerate(categories):
                if i != j and other_cat not in processed:
                    sim_score = similarity_matrix[i][j]
                    if sim_score > self.similarity_threshold:
                        similar_cats.append(other_cat)
                        processed.add(other_cat)

            # Use the most common/representative category as cluster name
            cluster_name = max(similar_cats, key=len) if similar_cats else cat
            clusters[cluster_name] = similar_cats
            processed.add(cat)

        return clusters

    def infer_query_categories(self, query: str) -> List[Tuple[str, float]]:
        """Infer categories for query using vector similarity"""
        if not self.category_embeddings:
            return []

        try:
            query_embedding = embed([f"query: {query}"])[0]
            query_embedding = np.array(query_embedding)

            category_scores = []
            for category, cat_embedding in self.category_embeddings.items():
                similarity = float(cosine_similarity([query_embedding], [cat_embedding])[0][0])
                if similarity > 0.3:  # Minimum threshold
                    category_scores.append((category, similarity))

            # Sort by similarity score
            category_scores.sort(key=lambda x: x[1], reverse=True)
            return category_scores[:3]  # Return top 3 matches

        except Exception as e:
            logger.warning(f"[AI] Failed to infer categories for query '{query}': {str(e)}")
            return []

class SemanticBooster:
    """Enhanced semantic relationships using embeddings"""

    def __init__(self):
        self.term_embeddings = {}
        self.semantic_clusters = {}

    def build_semantic_relationships(self, documents: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """Build semantic relationships from actual document content"""
        all_terms = set()

        for doc, meta in zip(documents, metadatas):
            # Extract terms from content
            terms = self._extract_meaningful_terms(doc)
            tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
            category = meta.get("category", "")

            # Add all terms
            for term in terms + tags + ([category] if category else []):
                if len(term) > 1:
                    all_terms.add(term)

        if all_terms:
            self._generate_term_embeddings(list(all_terms))

    def _extract_meaningful_terms(self, text: str) -> List[str]:
        """Extract meaningful Korean/English terms"""
        text = re.sub(r'[^\w\s가-힣]', ' ', text.lower())
        terms = text.split()

        # Korean stopwords
        stopwords = {'이', '그', '저', '의', '를', '을', '가', '는', '에', '에서',
                    '로', '으로', '와', '과', '도', '만', '까지', '부터', '하고', '있는'}

        meaningful = []
        for term in terms:
            if (len(term) > 1 and
                term not in stopwords and
                not term.isdigit()):
                meaningful.append(term)

        return meaningful

    def _generate_term_embeddings(self, terms: List[str]) -> None:
        """Generate embeddings for terms efficiently"""
        try:
            embeddings = embed([f"term: {term}" for term in terms])
            for term, embedding in zip(terms, embeddings):
                self.term_embeddings[term] = np.array(embedding)

            self._build_similarity_clusters(terms)
            logger.info(f"[AI] Built semantic relationships for {len(terms)} terms")

        except Exception as e:
            logger.warning(f"[AI] Failed to generate term embeddings: {str(e)}")

    def _build_similarity_clusters(self, terms: List[str]) -> None:
        """Build clusters of semantically similar terms"""
        if len(terms) < 2:
            return

        embeddings_matrix = np.array([self.term_embeddings[term] for term in terms])
        similarity_matrix = cosine_similarity(embeddings_matrix)

        for i, term in enumerate(terms):
            related = {}
            for j, other_term in enumerate(terms):
                if i != j:
                    sim_score = similarity_matrix[i][j]
                    if sim_score > 0.75:  # High similarity threshold
                        related[other_term] = float(sim_score)

            if related:
                self.semantic_clusters[term] = related

    def get_related_terms(self, query: str, threshold: float = 0.75) -> Dict[str, float]:
        """Get semantically related terms for query"""
        if not self.term_embeddings:
            return {}

        try:
            query_embedding = embed([f"query: {query}"])[0]
            query_embedding = np.array(query_embedding)

            related_terms = {}
            for term, term_embedding in self.term_embeddings.items():
                similarity = float(cosine_similarity([query_embedding], [term_embedding])[0][0])
                if similarity > threshold:
                    related_terms[term] = similarity

            return related_terms

        except Exception as e:
            logger.warning(f"[AI] Failed to get related terms: {str(e)}")
            return {}

# Global instances
category_discovery = VectorBasedCategoryDiscovery()
semantic_booster = SemanticBooster()

def get_user_joined_group_ids(user_id: str) -> Set[str]:
    """Get groups user has already joined"""
    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(name=USER_COLLECTION, embedding_function=embed)

        # Convert user_id to string first, then create variations
        user_id_str = str(user_id)
        user_variations = [user_id_str]
        
        # Only add integer variant if the string is actually a digit
        if user_id_str.isdigit():
            user_variations.append(int(user_id_str))

        joined_groups = set()

        for uid_variant in user_variations:
            try:
                result = col.get(where={"userId": uid_variant}, include=["metadatas"])
                groups = {
                    str(meta.get("groupId"))
                    for meta in result.get("metadatas", [])
                    if meta.get("groupId") is not None
                }
                joined_groups.update(groups)

            except Exception:
                continue

        # Clean up the set
        joined_groups.discard('None')
        joined_groups.discard('')
        joined_groups.discard(None)

        logger.info(f"[AI] User {user_id} joined groups: {len(joined_groups)}")
        return joined_groups

    except Exception as e:
        logger.warning(f"[AI] Failed to get user joined groups: {str(e)}")
        return set()

def search_similar_documents(
    query: str,
    top_k: int = 5,
    collection: Literal["group-info", "user-activity", "group-synthetic"] = "group-info",
    where: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Main search function with vector-based category discovery"""
    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(name=collection, embedding_function=embed)

        # Bootstrap learning from existing data
        if not category_discovery.category_embeddings or not semantic_booster.term_embeddings:
            _bootstrap_learning(col)

        # Get user's joined groups for exclusion
        joined_ids: Set[str] = set()
        if user_id:
            joined_ids = get_user_joined_group_ids(user_id)

        # Infer categories from query using vector similarity
        category_matches = category_discovery.infer_query_categories(query)
        logger.info(f"[AI] Query '{query}' matches categories: {[(cat, f'{score:.3f}') for cat, score in category_matches]}")

        # Try category-specific search first
        category_results = []
        if category_matches:
            # Use the best matching category
            best_category, score = category_matches[0]
            if score > 0.5:  # Decent similarity threshold
                logger.info(f"[AI] Searching in category: {best_category}")
                category_where = {"category": best_category}
                if where:
                    category_where.update(where)

                category_results = _perform_vector_search(
                    col, query, top_k * 2, category_where, joined_ids, user_id
                )

        # If no good category results, do general search with semantic enhancement
        if not category_results:
            logger.info(f"[AI] Performing enhanced general search")

            # Get semantically related terms
            related_terms = semantic_booster.get_related_terms(query, threshold=0.75)

            # Enhance query with related terms
            enhanced_query = query
            if related_terms:
                top_related = sorted(related_terms.items(), key=lambda x: x[1], reverse=True)[:2]
                enhancement = " ".join([term for term, score in top_related if score > 0.8])
                if enhancement:
                    enhanced_query = f"{query} {enhancement}"
                    logger.info(f"[AI] Enhanced query: '{enhanced_query}'")

            category_results = _perform_vector_search(
                col, enhanced_query, top_k * 3, where, joined_ids, user_id, related_terms
            )

        # Sort and return results
        category_results.sort(key=lambda x: x["score"], reverse=True)
        final_results = category_results[:top_k]

        logger.info(f"[AI] Returning {len(final_results)} recommendations")
        return final_results

    except Exception as e:
        logger.exception(f"[AI] Search failed: {str(e)}")
        return []

def _perform_vector_search(
    col,
    query: str,
    n_results: int,
    where: Optional[Dict[str, Any]],
    joined_ids: Set[str],
    user_id: Optional[str],
    related_terms: Optional[Dict[str, float]] = None
) -> List[Dict[str, Any]]:
    """Perform vector search with semantic scoring"""

    # Use E5 query prefix for better retrieval
    query_with_prefix = f"query: {query}"
    vector = embed(query_with_prefix)[0]

    results = col.query(
        query_embeddings=[vector],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
        where=where,
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    filtered = []
    origin = "real" if col.name == GROUP_COLLECTION else "synthetic"

    for doc, meta, dist in zip(documents, metadatas, distances):
        base_score = 1 - dist
        group_id = str(meta.get("groupId", ""))

        # Apply filters
        if base_score < RECOMMENDATION_THRESHOLD:
            continue
        if user_id and group_id in joined_ids:
            logger.debug(f"[AI] Excluding group {group_id} - user already joined")
            continue

        # Calculate semantic boost if we have related terms
        semantic_boost = 0.0
        if related_terms:
            semantic_boost = _calculate_semantic_boost(doc, meta, related_terms)

        final_score = min(1.0, base_score + semantic_boost)

        filtered.append({
            "id": meta.get("id"),
            "text": doc,
            "metadata": meta,
            "score": final_score,
            "base_score": base_score,
            "semantic_boost": semantic_boost,
            "origin": origin,
        })

    return filtered

def _calculate_semantic_boost(doc: str, meta: Dict[str, Any], related_terms: Dict[str, float]) -> float:
    """Calculate semantic boost based on related term matches"""
    if not related_terms:
        return 0.0

    # Combine all searchable text
    combined_text = f"{doc.lower()} {meta.get('tags', '').lower()} {meta.get('category', '').lower()}"

    boost = 0.0
    matches = 0

    for term, confidence in related_terms.items():
        if term in combined_text:
            # Boost based on term similarity confidence
            term_boost = confidence * 0.2  # Scale factor
            boost += term_boost
            matches += 1

    # Apply diminishing returns for multiple matches
    if matches > 0:
        boost = boost * (1.0 / (1.0 + 0.05 * (matches - 1)))

    return min(boost, 0.3)  # Cap total boost

def keyword_search_documents(
    query: str,
    top_k: int = 5,
    collection: Literal["group-info", "group-synthetic"] = "group-info",
    where: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """TF-IDF based keyword search with semantic enhancement"""
    try:
        client = get_chroma_client()
        col = client.get_or_create_collection(name=collection, embedding_function=embed)

        result = col.get(where=where, include=["documents", "metadatas"])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        ids = result.get("ids", [])

        if not documents:
            return []

        # Bootstrap if needed
        if not semantic_booster.term_embeddings:
            semantic_booster.build_semantic_relationships(documents, metadatas)

        # Get related terms for query expansion
        related_terms = semantic_booster.get_related_terms(query, threshold=0.75)

        # Expand query
        expanded_query = query
        if related_terms:
            top_related = sorted(related_terms.items(), key=lambda x: x[1], reverse=True)[:2]
            expansion = " ".join([term for term, score in top_related if score > 0.8])
            if expansion:
                expanded_query = f"{query} {expansion}"

        # TF-IDF search
        vectorizer = TfidfVectorizer(ngram_range=(1, 2))
        doc_vectors = vectorizer.fit_transform(documents)
        query_vec = vectorizer.transform([expanded_query])
        scores = (doc_vectors @ query_vec.T).toarray().ravel()

        # Filter and rank
        joined_ids = get_user_joined_group_ids(user_id) if user_id else set()

        results = []
        origin = "real" if collection == GROUP_COLLECTION else "synthetic"

        for idx in np.argsort(scores)[::-1]:
            meta = metadatas[idx]
            group_id = str(meta.get("groupId", ""))

            if user_id and group_id in joined_ids:
                continue

            base_score = float(scores[idx])
            semantic_boost = _calculate_semantic_boost(documents[idx], meta, related_terms)
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
        logger.exception(f"[AI] Keyword search failed: {str(e)}")
        return []

def _bootstrap_learning(col) -> None:
    """Bootstrap both category discovery and semantic learning"""
    try:
        result = col.get(include=["documents", "metadatas"])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])

        if documents:
            # Discover categories from actual data
            category_discovery.discover_categories_from_data(metadatas)

            # Build semantic relationships
            semantic_booster.build_semantic_relationships(documents, metadatas)

            logger.info(f"[AI] Bootstrapped learning from {len(documents)} documents")

    except Exception as e:
        logger.warning(f"[AI] Bootstrap learning failed: {str(e)}")

def get_system_stats() -> Dict[str, Any]:
    """Get system statistics"""
    try:
        return {
            "categories_discovered": len(category_discovery.category_embeddings),
            "semantic_terms": len(semantic_booster.term_embeddings),
            "semantic_clusters": len(semantic_booster.semantic_clusters),
            "total_relationships": sum(len(clusters) for clusters in semantic_booster.semantic_clusters.values()),
            "system_ready": bool(category_discovery.category_embeddings and semantic_booster.term_embeddings)
        }
    except Exception as e:
        logger.warning(f"[AI] Failed to get stats: {str(e)}")
        return {"error": str(e)}

# Convenience functions for backward compatibility
def search_similar_documents_with_category_filter(
    query: str,
    top_k: int = 5,
    collection: Literal["group-info", "user-activity", "group-synthetic"] = "group-info",
    where: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    preferred_categories: Optional[List[str]] = None,  # Ignored - using vector discovery now
) -> List[Dict[str, Any]]:
    """Backward compatibility wrapper"""
    return search_similar_documents(query, top_k, collection, where, user_id)

def get_user_joined_group_ids_enhanced(user_id: str) -> Set[str]:
    """Backward compatibility wrapper"""
    return get_user_joined_group_ids(user_id)

if __name__ == "__main__":
    from pprint import pprint
    print("=== Vector-Based Category Discovery Test ===")

    # Test system stats
    stats = get_system_stats()
    print("System stats:", stats)

    # Test user exclusion
    test_user_id = "20"
    joined_ids = get_user_joined_group_ids(test_user_id)
    print(f"\nUser {test_user_id} joined groups: {len(joined_ids)}")

    # Test queries
    test_queries = [
        "풋살 하고싶어요",
        "백엔드 개발 공부하고 싶어요",
        "영화 보면서 토론하고 싶어요",
        "맛집 탐방 모임 찾아요",
        "봉사활동 하고 싶어요"
    ]

    for query in test_queries:
        print(f"\n=== Query: '{query}' ===")
        results = search_similar_documents(query, top_k=3, user_id=test_user_id)

        for i, r in enumerate(results, 1):
            print(f"{i}. Group {r['metadata'].get('groupId')}")
            print(f"   Category: {r['metadata'].get('category')}")
            print(f"   Score: {r['score']:.3f} (base: {r['base_score']:.3f}, boost: {r['semantic_boost']:.3f})")
            print(f"   Text: {r['text'][:80]}...")
            print("-" * 50)
