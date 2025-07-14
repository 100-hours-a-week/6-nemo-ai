"""
Unified test file for the vector search system
Replaces test_detailed_scenarios.py, test_chatbot_recommendations.py, test_enhanced_system.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.vector_db.vector_searcher import (
    search_similar_documents,
    keyword_search_documents, 
    get_user_joined_group_ids,
    get_system_stats,
    category_discovery,
    semantic_booster
)
from pprint import pprint
import time

def test_user_exclusion():
    """Test user group exclusion functionality"""
    print("=== Testing User Exclusion ===")
    
    test_users = ["20", "15", "u2", "u5"]
    
    for user_id in test_users:
        joined_groups = get_user_joined_group_ids(user_id)
        print(f"User {user_id}: {len(joined_groups)} joined groups")
        if joined_groups:
            print(f"  Groups: {list(joined_groups)[:5]}...")  # Show first 5
        print()

def test_category_discovery():
    """Test vector-based category discovery"""
    print("=== Testing Vector-Based Category Discovery ===")
    
    # These should discover categories from actual data, not hardcoded
    test_queries = [
        "축구 모임 찾아요",
        "개발 스터디 하고 싶어요", 
        "독서 모임 참여하고 싶습니다",
        "요리 배우고 싶어요",
        "봉사활동 같이 해요"
    ]
    
    for query in test_queries:
        category_matches = category_discovery.infer_query_categories(query)
        print(f"'{query}'")
        print(f"  Discovered categories: {[(cat, f'{score:.3f}') for cat, score in category_matches[:3]]}")
        print()

def test_semantic_enhancement():
    """Test semantic term relationships"""
    print("=== Testing Semantic Enhancement ===")
    
    # Test semantic relationships
    test_terms = ["축구", "풋살", "개발", "프로그래밍", "요리", "음식"]
    
    for term in test_terms:
        related = semantic_booster.get_related_terms(term, threshold=0.7)
        if related:
            print(f"'{term}' related terms:")
            for rel_term, score in sorted(related.items(), key=lambda x: x[1], reverse=True)[:3]:
                print(f"  {rel_term}: {score:.3f}")
        else:
            print(f"'{term}': No related terms found")
        print()

def test_search_scenarios():
    """Test various search scenarios"""
    print("=== Testing Search Scenarios ===")
    
    scenarios = [
        {
            "name": "Sports Query", 
            "query": "풋살 같이 하실분",
            "user_id": "20",
            "expected": "Should find soccer/football related groups"
        },
        {
            "name": "Tech Query",
            "query": "백엔드 개발 공부하고 싶어요", 
            "user_id": "15",
            "expected": "Should find programming/development groups"
        },
        {
            "name": "Cultural Query",
            "query": "영화 보고 토론해요",
            "user_id": None,
            "expected": "Should find movie/culture groups"
        },
        {
            "name": "Food Query", 
            "query": "맛집 탐방 모임",
            "user_id": "u2",
            "expected": "Should find food/restaurant groups"
        },
        {
            "name": "Volunteer Query",
            "query": "봉사활동 참여하고 싶습니다",
            "user_id": None,
            "expected": "Should find volunteer/social service groups"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n--- {scenario['name']} ---")
        print(f"Query: '{scenario['query']}'")
        print(f"Expected: {scenario['expected']}")
        print(f"User ID: {scenario['user_id']}")
        
        # Test vector search
        start_time = time.time()
        vector_results = search_similar_documents(
            scenario['query'], 
            top_k=3, 
            user_id=scenario['user_id']
        )
        vector_time = time.time() - start_time
        
        print(f"\nVector Search Results ({vector_time:.3f}s):")
        for i, result in enumerate(vector_results, 1):
            print(f"  {i}. Group {result['metadata'].get('groupId')}")
            print(f"     Category: {result['metadata'].get('category', 'N/A')}")
            print(f"     Score: {result['score']:.3f} (base: {result['base_score']:.3f}, boost: {result['semantic_boost']:.3f})")
            print(f"     Text: {result['text'][:60]}...")
        
        # Test keyword search for comparison
        start_time = time.time()
        keyword_results = keyword_search_documents(
            scenario['query'],
            top_k=3,
            user_id=scenario['user_id']
        )
        keyword_time = time.time() - start_time
        
        print(f"\nKeyword Search Results ({keyword_time:.3f}s):")
        for i, result in enumerate(keyword_results, 1):
            print(f"  {i}. Group {result['metadata'].get('groupId')}")
            print(f"     Category: {result['metadata'].get('category', 'N/A')}")
            print(f"     Score: {result['score']:.3f}")
            print(f"     Text: {result['text'][:60]}...")
        
        print("-" * 60)

def test_edge_cases():
    """Test edge cases and error handling"""
    print("=== Testing Edge Cases ===")
    
    edge_cases = [
        {
            "name": "Empty Query",
            "query": "",
            "user_id": None
        },
        {
            "name": "Very Short Query", 
            "query": "축구",
            "user_id": "20"
        },
        {
            "name": "English Query",
            "query": "soccer team",
            "user_id": None
        },
        {
            "name": "Mixed Language",
            "query": "programming 스터디",
            "user_id": "15"
        },
        {
            "name": "Special Characters",
            "query": "모임!@#$%^&*()",
            "user_id": None
        },
        {
            "name": "Very Long Query",
            "query": "안녕하세요 저는 축구를 정말 좋아하는 사람입니다 특히 풋살을 좋아하고 주말마다 친구들과 함께 운동을 하고 싶어요",
            "user_id": "20"
        }
    ]
    
    for case in edge_cases:
        print(f"\n--- {case['name']} ---")
        print(f"Query: '{case['query']}'")
        
        try:
            results = search_similar_documents(
                case['query'],
                top_k=2,
                user_id=case['user_id']
            )
            print(f"Results: {len(results)} groups found")
            
            for i, result in enumerate(results, 1):
                print(f"  {i}. Group {result['metadata'].get('groupId')} - Score: {result['score']:.3f}")
                
        except Exception as e:
            print(f"Error: {str(e)}")

def test_performance():
    """Test system performance"""
    print("=== Testing Performance ===")
    
    queries = [
        "축구 모임",
        "개발 스터디", 
        "맛집 탐방",
        "영화 감상",
        "봉사활동"
    ]
    
    print("Performance comparison (5 queries):")
    
    # Vector search timing
    start_time = time.time()
    for query in queries:
        search_similar_documents(query, top_k=5)
    vector_total = time.time() - start_time
    
    # Keyword search timing  
    start_time = time.time()
    for query in queries:
        keyword_search_documents(query, top_k=5)
    keyword_total = time.time() - start_time
    
    print(f"Vector Search Total: {vector_total:.3f}s ({vector_total/len(queries):.3f}s avg)")
    print(f"Keyword Search Total: {keyword_total:.3f}s ({keyword_total/len(queries):.3f}s avg)")

def test_system_health():
    """Test overall system health"""
    print("=== System Health Check ===")
    
    stats = get_system_stats()
    print("System Statistics:")
    pprint(stats)
    
    # Check if system is properly initialized
    if stats.get("system_ready"):
        print("✅ System is ready")
    else:
        print("❌ System not properly initialized")
    
    # Check semantic learning
    if stats.get("semantic_terms", 0) > 0:
        print(f"✅ Semantic learning active ({stats['semantic_terms']} terms)")
    else:
        print("❌ Semantic learning not active")
    
    # Check category discovery
    if stats.get("categories_discovered", 0) > 0:
        print(f"✅ Category discovery active ({stats['categories_discovered']} categories)")
    else:
        print("❌ Category discovery not active")

def run_comprehensive_test():
    """Run all tests"""
    print("🚀 Starting Comprehensive Vector Search System Test")
    print("=" * 60)
    
    try:
        test_system_health()
        print()
        
        test_user_exclusion()
        print()
        
        test_category_discovery()
        print()
        
        test_semantic_enhancement()
        print()
        
        test_search_scenarios()
        print()
        
        test_edge_cases()
        print()
        
        test_performance()
        print()
        
        print("✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_comprehensive_test()
