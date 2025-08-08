"""
Unit tests for PrefixParser functionality.
Migrated from src/tests/utils/test_prefix_parser.py
"""

import pytest

# Import from app instead of src
try:
    from app.services.v3.ws_chatbot import PrefixParser
except ImportError:
    pytest.skip("PrefixParser not available", allow_module_level=True)


@pytest.mark.unit
class TestPrefixParser:
    """Unit tests for PrefixParser class."""

    @pytest.fixture
    def parser(self):
        """Create a PrefixParser instance for testing."""
        return PrefixParser(["**질문:**", "질문:", "**Question:**", "Question:"])

    def test_complete_prefix_in_first_chunk(self, parser):
        """Test handling of complete prefix in first chunk."""
        chunks = ["**질문:** 새로운 사람들과 편하게 이야기 나누는 걸 좋아하시나요?"]
        
        for chunk in chunks:
            result = parser.process_chunk(chunk)
            # Should remove the prefix but preserve the space after the prefix
            assert result == " 새로운 사람들과 편하게 이야기 나누는 걸 좋아하시나요?"

    def test_prefix_split_across_chunks(self, parser):
        """Test handling of prefix split across multiple chunks."""
        chunks = ["**질", "문:** 새로운 사람들과", " 편하게 이야기 나누는 걸 좋아하시나요?"]
        
        results = []
        for chunk in chunks:
            result = parser.process_chunk(chunk)
            results.append(result)
        
        # First chunk should be None (part of prefix, still waiting)
        assert results[0] is None
        # Second chunk should return content after prefix removal (space preserved)
        assert results[1] == " 새로운 사람들과"
        # Third chunk should return as-is
        assert results[2] == " 편하게 이야기 나누는 걸 좋아하시나요?"

    def test_no_prefix(self, parser):
        """Test handling when no prefix is present."""
        chunks = ["새로운 사람들과", " 편하게 이야기", " 나누는 걸 좋아하시나요?"]
        
        for i, chunk in enumerate(chunks):
            result = parser.process_chunk(chunk)
            # Should return chunks as-is when no prefix detected
            assert result == chunk

    def test_simple_korean_prefix(self, parser):
        """Test handling of simple Korean prefix."""
        chunks = ["질문: 새로운 사람들과", " 편하게 이야기 나누는 걸 좋아하시나요?"]
        
        results = []
        for chunk in chunks:
            result = parser.process_chunk(chunk)
            results.append(result)
        
        # First chunk should have prefix removed but space preserved
        assert results[0] == " 새로운 사람들과"
        # Second chunk should return as-is
        assert results[1] == " 편하게 이야기 나누는 걸 좋아하시나요?"

    def test_newlines_and_carriage_returns_removal(self, parser):
        """Test removal of newlines and carriage returns."""
        chunks = ["\n\r질문:\r\n 새로운 사람들과\n", " 편하게 이야기\r\n 나누는 걸 좋아하시나요?\n\r"]
        
        results = []
        for chunk in chunks:
            result = parser.process_chunk(chunk)
            results.append(result)
        
        # Should remove newlines/carriage returns and prefix
        assert "\n" not in results[0] and "\r" not in results[0]
        assert "\n" not in results[1] and "\r" not in results[1]
        
        # First chunk should have prefix removed but space preserved
        assert results[0] == " 새로운 사람들과"

    def test_prefix_in_middle_of_response(self, parser):
        """Test handling when prefix appears in middle of response."""
        chunks = ["새로운 사람들과 편하게", " 질문: 이야기 나누는 걸", " 좋아하시나요?"]
        
        results = []
        for chunk in chunks:
            result = parser.process_chunk(chunk)
            results.append(result)
        
        # Since prefix appears in middle, it should be treated as content
        # not as a prefix to remove
        assert results[0] == "새로운 사람들과 편하게"
        assert results[1] == " 질문: 이야기 나누는 걸"
        assert results[2] == " 좋아하시나요?"

    def test_empty_chunks(self, parser):
        """Test handling of empty chunks."""
        empty_chunk = ""
        result = parser.process_chunk(empty_chunk)
        assert result is None  # Should return None for empty chunks when waiting for prefix

    def test_whitespace_only_chunks(self, parser):
        """Test handling of whitespace-only chunks."""
        whitespace_chunk = "   \n\r\t   "
        result = parser.process_chunk(whitespace_chunk)
        # Should clean whitespace - first removes \n\r, then processes
        assert result == "   \t   "  # Only removed \n and \r

    @pytest.mark.parametrize("prefix", ["**질문:**", "질문:", "**Question:**", "Question:"])
    def test_different_prefixes(self, prefix):
        """Test handling of different prefix types."""
        parser = PrefixParser([prefix])
        test_chunk = f"{prefix} 테스트 내용입니다."
        
        result = parser.process_chunk(test_chunk)
        assert result == " 테스트 내용입니다."  # Space preserved after prefix removal

    def test_multiple_prefixes_in_list(self):
        """Test parser with multiple possible prefixes."""
        prefixes = ["**A:**", "**B:**", "**C:**"]
        parser = PrefixParser(prefixes)
        
        # Test each prefix
        for prefix in prefixes:
            test_chunk = f"{prefix} 테스트 내용"
            result = parser.process_chunk(test_chunk)
            assert result == " 테스트 내용"  # Space preserved after prefix removal

    def test_case_sensitivity(self):
        """Test case sensitivity of prefix matching."""
        parser = PrefixParser(["Question:", "QUESTION:"])
        
        # Should match exact case and preserve space
        result1 = parser.process_chunk("Question: 테스트")
        assert result1 == " 테스트"  # Space preserved after prefix removal
        
        # Create new parser for second test (since prefix_processed is now True)
        parser2 = PrefixParser(["Question:", "QUESTION:"])
        result2 = parser2.process_chunk("QUESTION: 테스트")
        assert result2 == " 테스트"  # Space preserved after prefix removal
        
        # Create new parser for third test
        parser3 = PrefixParser(["Question:", "QUESTION:"])
        # Should not match different case
        result3 = parser3.process_chunk("question: 테스트")
        assert result3 == "question: 테스트"  # No prefix removal


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
