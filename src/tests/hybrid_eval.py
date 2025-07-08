from src.vector_db.chroma_client import get_chroma_client
from src.vector_db.vector_indexer import add_documents_to_vector_db
from src.vector_db.group_document_builder import build_group_document
from src.vector_db.hybrid_search import hybrid_group_search
from src.vector_db.vector_searcher import search_similar_documents


GROUPS = [
    {
        "groupId": "1",
        "name": "조용한 독서모임",
        "summary": "소수로 모여 책을 읽습니다",
        "description": "도서관에서 진행되는 차분한 분위기의 모임",
        "category": "문화/예술",
        "location": "서울",
        "tags": ["독서", "조용한"],
        "plan": "매주 일요일",
    },
    {
        "groupId": "2",
        "name": "재즈 감상회",
        "summary": "함께 재즈를 듣습니다",
        "description": "활기찬 음악을 즐기는 모임",
        "category": "음악",
        "location": "서울",
        "tags": ["재즈", "공연"],
        "plan": "월 2회",
    },
]


def setup_data() -> None:
    docs = [build_group_document(g) for g in GROUPS]
    add_documents_to_vector_db(docs, collection="group-info")

    synthetic = [
        {
            "id": f"synthetic-{g['groupId']}-0",
            "text": f"{g['name']}에 대한 후기입니다. {g['description']}",
            "metadata": {
                "groupId": g["groupId"],
                "category": g["category"],
                "location": g["location"],
                "tags": ", ".join(g["tags"]),
            },
        }
        for g in GROUPS
    ]
    add_documents_to_vector_db(synthetic, collection="group-synthetic")


def evaluate(query: str = "조용한 분위기의 독서 모임") -> None:
    print("Query:", query)
    dense = search_similar_documents(query, top_k=1)
    hybrid = hybrid_group_search(query, top_k=1)
    print("Dense Top Result:", dense[0]["metadata"].get("groupId") if dense else None)
    print("Hybrid Top Result:", hybrid[0]["metadata"].get("groupId") if hybrid else None)


if __name__ == "__main__":
    setup_data()
    client = get_chroma_client()
    collections = [c.name for c in client.list_collections()]
    print("Collections:", collections)
    evaluate()
