#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402

TEST_QUESTIONS = [
    "你是谁",
    "系统健康吗",
    "联系方式",
    "什么是RAG",
    "浣犳槸璋?",
    "绯荤粺鍋ュ悍鍚?",
    "鑱旂郴鏂瑰紡",
]


def get_conn():
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset="utf8mb4",
        use_unicode=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def print_faq_overview(cursor, table_name: str):
    sql = f"""
    SELECT
        id,
        question,
        HEX(question) AS question_hex,
        answer,
        HEX(answer) AS answer_hex
    FROM {table_name}
    ORDER BY id
    LIMIT 20
    """
    cursor.execute(sql)
    rows = cursor.fetchall()

    print("=" * 80)
    print("FAQ 表概览")
    print("=" * 80)
    if not rows:
        print("FAQ 表为空")
        return

    for row in rows:
        print(f"ID: {row['id']}")
        print(f"question: {row['question']}")
        print(f"question_hex: {row['question_hex']}")
        print(f"answer: {row['answer']}")
        print(f"answer_hex: {row['answer_hex'][:120]}...")
        print("-" * 80)


def query_exact(cursor, table_name: str, question: str):
    sql = f"""
    SELECT id, question, answer, HEX(question) AS question_hex
    FROM {table_name}
    WHERE question = %s
    LIMIT 1
    """
    cursor.execute(sql, (question,))
    return cursor.fetchone()


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            print_faq_overview(cursor, settings.mysql_faq_table)

            print("\n" + "=" * 80)
            print("FAQ 精确匹配测试")
            print("=" * 80)

            for q in TEST_QUESTIONS:
                row = query_exact(cursor, settings.mysql_faq_table, q)
                if row:
                    print(f"[命中] {q}")
                    print(f"  ID: {row['id']}")
                    print(f"  question: {row['question']}")
                    print(f"  question_hex: {row['question_hex']}")
                else:
                    print(f"[未命中] {q}")
                print("-" * 80)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
