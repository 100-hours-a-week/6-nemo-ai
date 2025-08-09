import pymysql
from app.database.user_document_builder import build_user_document
from app.database.group_document_builder import build_group_document
from app.database.synthetic_document_builder import build_synthetic_documents
from app.database.vector_indexer import add_documents_to_vector_db
from app.config import HOST, PORT, DB_USER, PASSWORD, DATABASE
from app.core.ai_logger import get_ai_logger

ai_logger = get_ai_logger()

def fetch_data_from_mysql():
    conn = pymysql.connect(
        host=HOST,
        port=int(PORT),
        user=DB_USER,
        password=PASSWORD,
        db=DATABASE,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

    try:
        with conn.cursor() as cursor:
            # 1. 유저-그룹 참여 정보
            cursor.execute("SELECT group_id, user_id FROM group_participants")
            user_participation = cursor.fetchall()

            # 2. 그룹 정보 + 태그 이름
            cursor.execute("""
                SELECT 
                  g.id,
                  g.name,
                  g.summary,
                  g.description,
                  g.category,
                  g.location,
                  g.current_user_count,
                  g.max_user_count,
                  g.image_url,
                  g.plan,
                  GROUP_CONCAT(t.name) AS tags
                FROM groups_table g
                LEFT JOIN group_tags gt ON g.id = gt.group_id
                LEFT JOIN tags t ON gt.tag_id = t.id
                WHERE g.id IS NOT NULL
                AND g.status = 'ACTIVE'
                GROUP BY g.id;
    """)
            group_infos = cursor.fetchall()

            return user_participation, group_infos

    finally:
        conn.close()


def sync_user_documents(user_participation):
    user_docs = []
    for row in user_participation:
        try:
            user_docs.extend(build_user_document(str(row["user_id"]), str(row["group_id"])))
        except Exception as e:
            ai_logger.error(f"유저 문서 생성 실패: {row} - {e}")
    add_documents_to_vector_db(user_docs, collection="user-activity")


async def sync_group_documents(group_infos):
    group_docs = []
    synthetic_docs = []
    for group in group_infos:
        try:
            group["groupId"] = group.pop("id")
            tags = group["tags"].split(",") if group["tags"] else []
            group["tags"] = [tag.strip() for tag in tags]
            group_docs.append(build_group_document(group))

            try:
                syn = await build_synthetic_documents(group)
                synthetic_docs.extend(syn)
            except Exception as se:
                ai_logger.error(f"synthetic 문서 생성 실패: {group['groupId']} - {se}")
        except Exception as e:
            ai_logger.error(f"그룹 문서 생성 실패: {group.get('id')} - {e}")

    add_documents_to_vector_db(group_docs, collection="group-info")
    if synthetic_docs:
        add_documents_to_vector_db(synthetic_docs, collection="group-synthetic")


if __name__ == "__main__":
    ai_logger.info("MySQL에서 데이터 불러오는 중...")
    user_participation, group_infos = fetch_data_from_mysql()
    #
    # ai_logger.info(f"유저 참여 문서: {len(user_participation)}건")
    # sync_user_documents(user_participation)
    #
    # ai_logger.info(f"그룹 문서: {len(group_infos)}건")
    # sync_group_documents(group_infos)

    ai_logger.info("ChromaDB 동기화 완료")
