from __future__ import annotations

import re
import sys
from pathlib import Path

import pymysql

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402

"""
  - 检查本地文件是否疑似乱码
  - 检查 FAQ 表里的数据是否疑似乱码
  - 用“正常中文 / 乱码中文”双向验证
  - 辅助定位是文件编码问题、入库问题还是显示问题
"""



SUSPECT_GARBLED_PATTERNS = [
    "浣", "鎴", "绯", "鍚", "妫", "璇", "鐨", "銆", "锛", "锟", "�"
]

CHECK_FILES = [
    ROOT / "docker" / "mysql" / "init" / "001_init_faq.sql",
    ROOT / "insert_sql.sql",
    ROOT / "logs" / "app.log",
]

TEST_QUESTIONS = [
    "你是谁",
    "系统健康吗",
    "联系方式",
    "浣犳槸璋?",
    "绯荤粺鍋ュ悍鍚?",
    "鑱旂郴鏂瑰紡",
]


def has_garbled_text(text: str) -> bool:
    if not text:
        return False
    return any(token in text for token in SUSPECT_GARBLED_PATTERNS)


def short_text(text: str, limit: int = 120) -> str:
    text = text.replace("\n", "\\n")
    return text if len(text) <= limit else text[:limit] + "..."


def check_file(path: Path) -> dict:
    result = {
        "path": str(path),
        "exists": path.exists(),
        "read_ok": False,
        "suspect_lines": [],
        "error": None,
    }
    if not path.exists():
        return result

    try:
        content = path.read_text(encoding="utf-8")
        result["read_ok"] = True
        for idx, line in enumerate(content.splitlines(), start=1):
            if has_garbled_text(line):
                result["suspect_lines"].append((idx, short_text(line)))
    except Exception as e:
        result["error"] = repr(e)
    return result


def get_mysql_connection():
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


def check_mysql_charset(cursor) -> dict:
    sql = """
    SHOW VARIABLES
    WHERE Variable_name IN (
        'character_set_server',
        'character_set_database',
        'character_set_connection',
        'character_set_client',
        'character_set_results',
        'collation_server',
        'collation_database',
        'collation_connection'
    )
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    return {row["Variable_name"]: row["Value"] for row in rows}


def check_mysql_rows(cursor, table_name: str) -> list[dict]:
    sql = f"""
    SELECT id, question, answer
    FROM {table_name}
    ORDER BY id
    LIMIT 20
    """
    cursor.execute(sql)
    return cursor.fetchall()


def query_exact(cursor, table_name: str, question: str) -> dict | None:
    sql = f"""
    SELECT id, question, answer
    FROM {table_name}
    WHERE question = %s
    LIMIT 1
    """
    cursor.execute(sql, (question,))
    return cursor.fetchone()


def main():
    print("=" * 80)
    print("P0-1 文本链路排查")
    print("=" * 80)

    print("\n[1] 本地文件检查")
    for file_path in CHECK_FILES:
        result = check_file(file_path)
        print(f"\n文件: {result['path']}")
        print(f"存在: {result['exists']}")
        print(f"可读取: {result['read_ok']}")
        if result["error"]:
            print(f"读取错误: {result['error']}")
        if result["suspect_lines"]:
            print("疑似乱码行:")
            for line_no, text in result["suspect_lines"][:10]:
                print(f"  L{line_no}: {text}")
        else:
            print("未发现明显乱码特征")

    print("\n[2] MySQL 字符集检查")
    try:
        conn = get_mysql_connection()
    except Exception as e:
        print(f"MySQL 连接失败: {e}")
        return

    try:
        with conn.cursor() as cursor:
            charset_info = check_mysql_charset(cursor)
            for k, v in charset_info.items():
                print(f"{k}: {v}")

            print("\n[3] FAQ 表样本检查")
            rows = check_mysql_rows(cursor, settings.mysql_faq_table)
            if not rows:
                print("FAQ 表为空")
            else:
                for row in rows:
                    q = row["question"] or ""
                    a = row["answer"] or ""
                    q_flag = "疑似乱码" if has_garbled_text(q) else "正常"
                    a_flag = "疑似乱码" if has_garbled_text(a) else "正常"
                    print(
                        f"ID={row['id']} | question[{q_flag}]={short_text(q)} | "
                        f"answer[{a_flag}]={short_text(a)}"
                    )

            print("\n[4] FAQ 精确匹配双向验证")
            for q in TEST_QUESTIONS:
                row = query_exact(cursor, settings.mysql_faq_table, q)
                if row:
                    print(
                        f"命中: {q} -> ID={row['id']} | "
                        f"question={short_text(row['question'])}"
                    )
                else:
                    print(f"未命中: {q}")

    finally:
        conn.close()

    print("\n[5] 结论判断建议")
    print("- 如果本地 SQL 文件本身就是乱码：说明源文件已损坏，后续要先修 SQL/脚本文件编码。")
    print("- 如果 SQL 文件正常、但表里是乱码：说明入库链路有问题。")
    print("- 如果表里正常、终端显示乱码：优先怀疑终端编码/日志查看方式。")
    print("- 如果正常中文查不到、乱码能查到：说明数据库里大概率已经存成乱码文本。")


if __name__ == "__main__":
    main()
      