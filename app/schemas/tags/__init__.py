"""
Tags 스키마 모듈
태그 추출 관련 데이터 모델들을 정의합니다.
"""

from .tag_extraction import (
    TagRequest,
    TagResponse
)

__all__ = [
    "TagRequest",
    "TagResponse",
]
