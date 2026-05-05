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

    def _connect(self):
        # TODO: 当 FAQ 请求量上来后，这里可替换为连接池，减少重复建连开销。
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )

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
        # TODO: 当前先保留精确匹配；后续可升级为模糊匹配、全文检索或 FAQ 向量检索。
        logger.info(
            f"Attempting to connect to MySQL: {self.host}:{self.port}, database: {self.database}, table: {self.table}"
        )
        conn = self._connect()
        logger.info("MySQL connection established successfully.")

        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, (query,))
                row = cursor.fetchone()
                if not row:
                    logger.info(f"No match found in DB for query: '{query}'")
                    return None

                row["score"] = 1.0
                logger.info(f"Match found in DB: ID={row['id']}")
                return row
        finally:
            conn.close()

    def health_status(self) -> dict:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 AS ok")
                cursor.fetchone()

                cursor.execute("SHOW TABLES LIKE %s", (self.table,))
                table_exists = cursor.fetchone() is not None

                faq_count = 0
                if table_exists:
                    cursor.execute(f"SELECT COUNT(*) AS count FROM {self.table}")
                    row = cursor.fetchone() or {}
                    faq_count = int(row.get("count", 0))

                return {
                    "ok": True,
                    "host": self.host,
                    "port": self.port,
                    "database": self.database,
                    "table": self.table,
                    "table_exists": table_exists,
                    "faq_count": faq_count,
                }
        finally:
            conn.close()
