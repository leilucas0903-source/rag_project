#!/usr/bin/env python
"""测试 MySQL FAQ Retriever 连接。"""

import sys
from pathlib import Path

import pymysql

sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.retrieval.mysql_faq_retriever import MysqlFAQRetriever


def test_direct_pymysql() -> bool:
    print("\n" + "=" * 60)
    print("直接 PyMySQL 连接测试")
    print("=" * 60)
    print(
        f"[DEBUG] Host={settings.mysql_host} "
        f"Port={settings.mysql_port} "
        f"User={settings.mysql_user} "
        f"DB={settings.mysql_database}"
    )

    try:
        conn = pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset="utf8mb4",
            use_unicode=True,
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor,
        )
        print("[OK] 连接成功")

        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version, NOW() AS now")
            result = cursor.fetchone()
            print(f"MySQL 版本: {result['version']}")
            print(f"当前时间: {result['now']}")

            cursor.execute(f"SHOW TABLES LIKE '{settings.mysql_faq_table}'")
            row = cursor.fetchone()
            if row:
                print(f"[OK] 表 `{settings.mysql_faq_table}` 存在")
                cursor.execute(f"SELECT COUNT(*) AS count FROM {settings.mysql_faq_table}")
                count = cursor.fetchone()
                print(f"FAQ 记录数: {count['count']}")
            else:
                print(f"[ERROR] 表 `{settings.mysql_faq_table}` 不存在")
                return False

        conn.close()
        return True

    except Exception as e:
        print(f"[ERROR] 连接失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        return False


def test_retriever() -> bool:
    print("\n" + "=" * 60)
    print("MysqlFAQRetriever 测试")
    print("=" * 60)

    print("当前配置:")
    print(f"  Host: {settings.mysql_host}")
    print(f"  Port: {settings.mysql_port}")
    print(f"  User: {settings.mysql_user}")
    print(f"  Database: {settings.mysql_database}")
    print(f"  Table: {settings.mysql_faq_table}")

    try:
        retriever = MysqlFAQRetriever()
        print("[OK] Retriever 初始化成功")
    except Exception as e:
        print(f"[ERROR] Retriever 初始化失败: {e}")
        return False

    test_queries = [
        "你是谁",
        "什么是RAG",
        "如何使用",
        "测试查询",
    ]

    for query in test_queries:
        print(f"\n查询: {query}")
        try:
            result = retriever.retrieve(query)
            if result:
                print(f"[OK] 命中: {result.question}")
                print(f"答案: {result.answer}")
            else:
                print("[INFO] 未命中")
        except Exception as e:
            print(f"[ERROR] 查询失败: {e}")

    return True


if __name__ == "__main__":
    if test_direct_pymysql():
        test_retriever()
    else:
        print("\n排查建议:")
        print("1. 先运行 `docker compose ps` 确认 rag-mysql 是 Up 状态")
        print("2. 运行 `docker compose logs mysql` 查看初始化报错")
        print("3. 若改过初始化 SQL，请执行 `docker compose down -v` 后再重建")
