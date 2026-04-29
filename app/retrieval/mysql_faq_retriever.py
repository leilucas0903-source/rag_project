from dataclasses import dataclass
import pymysql
from app.core.config import settings
from app.core.logger import get_logger
"""
CREATE TABLE faq (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    question VARCHAR(255) NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

logger = get_logger(__name__)

@dataclass
class FAQHit:
    faq_id: str
    question: str
    answer: str
    score: float


class MysqlFAQRetriever:
    def __init__(self) -> None:
        self.host = settings.mysql_host
        self.port = settings.mysql_port
        self.user = settings.mysql_user
        self.password = settings.mysql_password
        self.database = settings.mysql_database
        self.table = settings.mysql_faq_table

    def retrieve(self, query: str) -> FAQHit | None:
        q = query.strip()
        if not q:
            return None
        
        row = self._query_mysql(q)
        if not row:
            return None
        
        return FAQHit(
            faq_id=str(row["id"]),
            question=row["question"],
            answer=row["answer"],
            score=float(row.get("score", 1.0)),
        )


    def _query_mysql(self, query: str) -> dict | None:
        sql = f"""
        SELECT id, question, answer
        FROM {self.table}
        WHERE question = %s
        LIMIT 1
        """
        logger.info(f"Attempting to connect to MySQL: {self.host}:{self.port}, database: {self.database}, table: {self.table}")
        conn = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        logger.info("MySQL connection established successfully.") # 埋点 2：连接成功
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, (query,))
                row = cursor.fetchone()
                if not row:
                    logger.info(f"No match found in DB for query: '{query}'") # 埋点 4：查询无结果
                    return None

                
                row["score"] = 1.0
                logger.info(f"Match found in DB: ID={row['id']}") # 埋点 5：查询成功
                return row
                
        finally:
            conn.close()