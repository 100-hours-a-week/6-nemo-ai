#!/usr/bin/env python3
"""
Test script for PrefixParser functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.v2.ws_chatbot import PrefixParser

def test_prefix_parser():
    print("=== Testing PrefixParser ===")
    
    # Test case 1: Complete prefix in first chunk
    print("\n1. Testing complete prefix in first chunk:")
    parser = PrefixParser(["**질문:**", "질문:", "**Question:**", "Question:"])
    
    chunks = ["**질문:** 새로운 사람들과 편하게 이야기 나누는 걸 좋아하시나요?"]
    for i, chunk in enumerate(chunks):
        result = parser.process_chunk(chunk)
        print(f"  Chunk {i+1}: '{chunk}' -> '{result}'")
    
    # Test case 2: Prefix split across chunks
    print("\n2. Testing prefix split across chunks:")
    parser = PrefixParser(["**질문:**", "질문:", "**Question:**", "Question:"])
    
    chunks = ["**질", "문:** 새로운 사람들과", " 편하게 이야기 나누는 걸 좋아하시나요?"]
    for i, chunk in enumerate(chunks):
        result = parser.process_chunk(chunk)
        print(f"  Chunk {i+1}: '{chunk}' -> '{result}'")
    
    # Test case 3: No prefix
    print("\n3. Testing no prefix:")
    parser = PrefixParser(["**질문:**", "질문:", "**Question:**", "Question:"])
    
    chunks = ["새로운 사람들과", " 편하게 이야기", " 나누는 걸 좋아하시나요?"]
    for i, chunk in enumerate(chunks):
        result = parser.process_chunk(chunk)
        print(f"  Chunk {i+1}: '{chunk}' -> '{result}'")
    
    # Test case 4: Korean prefix
    print("\n4. Testing simple Korean prefix:")
    parser = PrefixParser(["**질문:**", "질문:", "**Question:**", "Question:"])
    
    chunks = ["질문: 새로운 사람들과", " 편하게 이야기 나누는 걸 좋아하시나요?"]
    for i, chunk in enumerate(chunks):
        result = parser.process_chunk(chunk)
        print(f"  Chunk {i+1}: '{chunk}' -> '{result}'")

if __name__ == "__main__":
    test_prefix_parser()
