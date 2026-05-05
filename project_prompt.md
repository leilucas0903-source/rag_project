# Table of Contents
- .env.example
- .gitignore
- check_text_chain.py
- docker-compose.yml
- insert_sql.sql
- project_prompt.md
- README.md
- Record.md
- requirements.txt
- roadmap.md
- test_milvus.py
- test_sql.py
- verify_milvus_collection_p0.py
- verify_mysql_faq_p0.py
- 项目问题清单.md
- app\main.py
- app\__init__.py
- app\api\routes_admin.py
- app\api\routes_query.py
- app\api\schemas.py
- app\api\__init__.py
- app\core\config.py
- app\core\logger.py
- app\core\metrics.py
- app\generation\answer_postprocess.py
- app\generation\llm_client.py
- app\generation\prompt_builder.py
- app\handlers\error_handler.py
- app\indexing\embedding_worker.py
- app\indexing\loaders.py
- app\indexing\milvus_upsert.py
- app\indexing\splitter.py
- app\indexing\__init__.py
- app\middleware\metrics_middleware.py
- app\middleware\request_logger.py
- app\models\document.py
- app\models\query.py
- app\models\response.py
- app\retrieval\bm25_retriever.py
- app\retrieval\hybrid_retriever.py
- app\retrieval\milvus_retriever.py
- app\retrieval\mysql_faq_retriever.py
- app\router\intent_router.py
- data\seed\demo_knowledge.jsonl
- docker\mysql\init\001_init_faq.sql
- scripts\reindex.py
- scripts\trace_log.py

## File: .env.example

- Extension: .example
- Language: unknown
- Size: 575 bytes
- Created: 2026-04-28 22:21:35
- Modified: 2026-04-29 19:27:06

### Code

```unknown
﻿APP_NAME=rag-project
APP_ENV=dev
LOG_LEVEL=INFO
DEBUG=false

MYSQL_ROOT_PASSWORD=CHANGE_ME
MYSQL_DATABASE=rag
TZ=Asia/Shanghai

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=CHANGE_ME
MYSQL_FAQ_TABLE=faq

MILVUS_HOST=127.0.0.1
MILVUS_PORT=19530
MILVUS_COLLECTION=rag_docs
MILVUS_USER=
MILVUS_PASSWORD=

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION=384
EMBEDDING_BATCH_SIZE=32
CHUNK_SIZE=500
CHUNK_OVERLAP=80

OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_MAX_OUTPUT_TOKENS=800

```

## File: .gitignore

- Extension: 
- Language: unknown
- Size: 380 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```unknown
# Python 缓存与字节码
__pycache__/
*.pyc
*.pyo
*.pyd

# 日志文件
logs/
*.log

# 环境与配置
.env
.venv/
venv/
.pytest_cache/

# 你的项目特有配置
# 如果 config.dev.yaml 里有敏感密码，建议把它也加入忽略列表
# 或者只上传一个 config.dev.yaml.example
configs/config.dev.yaml

# 你的本地开发文件
log_test.py
```

## File: check_text_chain.py

- Extension: .py
- Language: python
- Size: 5979 bytes
- Created: 2026-04-29 15:29:05
- Modified: 2026-04-29 15:39:04

### Code

```python
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
      
```

## File: docker-compose.yml

- Extension: .yml
- Language: yaml
- Size: 2497 bytes
- Created: 2026-04-28 17:25:50
- Modified: 2026-04-29 17:58:19

### Code

```yaml
﻿services:
  mysql:
    image: mysql:8.0
    container_name: rag-mysql
    restart: unless-stopped
    ports:
      - "3307:3306"
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      TZ: ${TZ}
      LANG: C.UTF-8
      LC_ALL: C.UTF-8
    command:
      - --default-authentication-plugin=mysql_native_password
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --skip-character-set-client-handshake
    volumes:
      - mysql_data:/var/lib/mysql
      - ./docker/mysql/init:/docker-entrypoint-initdb.d

  adminer:
    image: adminer:latest
    container_name: rag-adminer
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      ADMINER_DEFAULT_SERVER: mysql
    depends_on:
      - mysql

  etcd:
    container_name: milvus-etcd
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - etcd_data:/etcd
    command:
      - etcd
      - -advertise-client-urls=http://127.0.0.1:2379
      - -listen-client-urls
      - http://0.0.0.0:2379
      - --data-dir
      - /etcd
    healthcheck:
      test: ["CMD", "etcdctl", "endpoint", "health"]
      interval: 30s
      timeout: 20s
      retries: 3

  minio:
    container_name: milvus-minio
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    ports:
      - "9001:9001"
      - "9000:9000"
    volumes:
      - minio_data:/minio_data
    command: minio server /minio_data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  milvus-standalone:
    container_name: milvus-standalone
    image: milvusdb/milvus:v2.3.4
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    volumes:
      - milvus_data:/var/lib/milvus
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      interval: 30s
      start_period: 90s
      timeout: 20s
      retries: 3
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - etcd
      - minio

volumes:
  mysql_data:
  etcd_data:
  minio_data:
  milvus_data:

```

## File: insert_sql.sql

- Extension: .sql
- Language: sql
- Size: 2048 bytes
- Created: 2026-04-29 09:56:48
- Modified: 2026-04-29 10:10:06

### Code

```sql
#!/usr/bin/env python
"""修复数据库编码问题 - 重新插入正确的 UTF-8 数据"""

import pymysql
import sys

# 数据库配置
config = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'rag',
    'charset': 'utf8mb4',
    'use_unicode': True
}

# 正确的数据
faq_data = [
    ("你是谁", "我是 RAG 智能助手，基于检索增强生成技术构建，可以回答你的问题。"),
    ("你能做什么", "我可以回答问题、提供信息、协助解决问题等。"),
    ("什么是RAG", "RAG（Retrieval-Augmented Generation）是一种结合检索和生成的 AI 技术。"),
    ("如何使用", "直接输入问题，我会从知识库中检索相关信息并给出答案。"),
    ("联系方式", "请通过项目仓库提交问题或建议。"),
    ("系统健康吗", "系统当前运行正常，所有服务可用。")
]

print("="*60)
print("修复数据库编码")
print("="*60)

try:
    # 连接数据库
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    # 检查当前数据
    cursor.execute("SELECT COUNT(*) FROM faq")
    count = cursor.fetchone()[0]
    print(f"当前记录数: {count}")
    
    # 清空表
    cursor.execute("TRUNCATE TABLE faq")
    print("✅ 清空表成功")
    
    # 插入正确数据
    for question, answer in faq_data:
        cursor.execute(
            "INSERT INTO faq (question, answer) VALUES (%s, %s)",
            (question, answer)
        )
        print(f"✅ 插入: {question}")
    
    conn.commit()
    print(f"✅ 共插入 {len(faq_data)} 条记录")
    
    # 验证
    cursor.execute("SELECT id, question FROM faq")
    rows = cursor.fetchall()
    print("\n验证结果:")
    for row in rows:
        print(f"  ID {row[0]}: {row[1]}")
    
    cursor.close()
    conn.close()
    
    print("\n✅ 数据修复完成！")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    sys.exit(1)
```

## File: project_prompt.md

- Extension: .md
- Language: markdown
- Size: 244759 bytes
- Created: 2026-04-29 10:29:35
- Modified: 2026-05-05 17:02:52

### Code

```markdown
# Table of Contents
- .env.example
- .gitignore
- check_text_chain.py
- docker-compose.yml
- insert_sql.sql
- project_prompt.md
- README.md
- Record.md
- requirements.txt
- roadmap.md
- test_milvus.py
- test_sql.py
- verify_milvus_collection_p0.py
- verify_mysql_faq_p0.py
- 项目问题清单.md
- app\main.py
- app\__init__.py
- app\api\routes_admin.py
- app\api\routes_query.py
- app\api\schemas.py
- app\api\__init__.py
- app\core\config.py
- app\core\logger.py
- app\core\metrics.py
- app\generation\answer_postprocess.py
- app\generation\llm_client.py
- app\generation\prompt_builder.py
- app\handlers\error_handler.py
- app\indexing\embedding_worker.py
- app\indexing\loaders.py
- app\indexing\milvus_upsert.py
- app\indexing\splitter.py
- app\indexing\__init__.py
- app\middleware\metrics_middleware.py
- app\middleware\request_logger.py
- app\models\document.py
- app\models\query.py
- app\models\response.py
- app\retrieval\bm25_retriever.py
- app\retrieval\hybrid_retriever.py
- app\retrieval\milvus_retriever.py
- app\retrieval\mysql_faq_retriever.py
- app\router\intent_router.py
- data\seed\demo_knowledge.jsonl
- docker\mysql\init\001_init_faq.sql
- scripts\reindex.py
- scripts\trace_log.py

## File: .env.example

- Extension: .example
- Language: unknown
- Size: 575 bytes
- Created: 2026-04-28 22:21:35
- Modified: 2026-04-29 19:27:06

### Code

```unknown
﻿APP_NAME=rag-project
APP_ENV=dev
LOG_LEVEL=INFO
DEBUG=false

MYSQL_ROOT_PASSWORD=CHANGE_ME
MYSQL_DATABASE=rag
TZ=Asia/Shanghai

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=CHANGE_ME
MYSQL_FAQ_TABLE=faq

MILVUS_HOST=127.0.0.1
MILVUS_PORT=19530
MILVUS_COLLECTION=rag_docs
MILVUS_USER=
MILVUS_PASSWORD=

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION=384
EMBEDDING_BATCH_SIZE=32
CHUNK_SIZE=500
CHUNK_OVERLAP=80

OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_MAX_OUTPUT_TOKENS=800

```

## File: .gitignore

- Extension: 
- Language: unknown
- Size: 380 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```unknown
# Python 缓存与字节码
__pycache__/
*.pyc
*.pyo
*.pyd

# 日志文件
logs/
*.log

# 环境与配置
.env
.venv/
venv/
.pytest_cache/

# 你的项目特有配置
# 如果 config.dev.yaml 里有敏感密码，建议把它也加入忽略列表
# 或者只上传一个 config.dev.yaml.example
configs/config.dev.yaml

# 你的本地开发文件
log_test.py
```

## File: check_text_chain.py

- Extension: .py
- Language: python
- Size: 5979 bytes
- Created: 2026-04-29 15:29:05
- Modified: 2026-04-29 15:39:04

### Code

```python
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
      
```

## File: docker-compose.yml

- Extension: .yml
- Language: yaml
- Size: 2497 bytes
- Created: 2026-04-28 17:25:50
- Modified: 2026-04-29 17:58:19

### Code

```yaml
﻿services:
  mysql:
    image: mysql:8.0
    container_name: rag-mysql
    restart: unless-stopped
    ports:
      - "3307:3306"
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      TZ: ${TZ}
      LANG: C.UTF-8
      LC_ALL: C.UTF-8
    command:
      - --default-authentication-plugin=mysql_native_password
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --skip-character-set-client-handshake
    volumes:
      - mysql_data:/var/lib/mysql
      - ./docker/mysql/init:/docker-entrypoint-initdb.d

  adminer:
    image: adminer:latest
    container_name: rag-adminer
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      ADMINER_DEFAULT_SERVER: mysql
    depends_on:
      - mysql

  etcd:
    container_name: milvus-etcd
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - etcd_data:/etcd
    command:
      - etcd
      - -advertise-client-urls=http://127.0.0.1:2379
      - -listen-client-urls
      - http://0.0.0.0:2379
      - --data-dir
      - /etcd
    healthcheck:
      test: ["CMD", "etcdctl", "endpoint", "health"]
      interval: 30s
      timeout: 20s
      retries: 3

  minio:
    container_name: milvus-minio
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    ports:
      - "9001:9001"
      - "9000:9000"
    volumes:
      - minio_data:/minio_data
    command: minio server /minio_data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  milvus-standalone:
    container_name: milvus-standalone
    image: milvusdb/milvus:v2.3.4
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    volumes:
      - milvus_data:/var/lib/milvus
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      interval: 30s
      start_period: 90s
      timeout: 20s
      retries: 3
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - etcd
      - minio

volumes:
  mysql_data:
  etcd_data:
  minio_data:
  milvus_data:

```

## File: insert_sql.sql

- Extension: .sql
- Language: sql
- Size: 2048 bytes
- Created: 2026-04-29 09:56:48
- Modified: 2026-04-29 10:10:06

### Code

```sql
#!/usr/bin/env python
"""修复数据库编码问题 - 重新插入正确的 UTF-8 数据"""

import pymysql
import sys

# 数据库配置
config = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'rag',
    'charset': 'utf8mb4',
    'use_unicode': True
}

# 正确的数据
faq_data = [
    ("你是谁", "我是 RAG 智能助手，基于检索增强生成技术构建，可以回答你的问题。"),
    ("你能做什么", "我可以回答问题、提供信息、协助解决问题等。"),
    ("什么是RAG", "RAG（Retrieval-Augmented Generation）是一种结合检索和生成的 AI 技术。"),
    ("如何使用", "直接输入问题，我会从知识库中检索相关信息并给出答案。"),
    ("联系方式", "请通过项目仓库提交问题或建议。"),
    ("系统健康吗", "系统当前运行正常，所有服务可用。")
]

print("="*60)
print("修复数据库编码")
print("="*60)

try:
    # 连接数据库
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    # 检查当前数据
    cursor.execute("SELECT COUNT(*) FROM faq")
    count = cursor.fetchone()[0]
    print(f"当前记录数: {count}")
    
    # 清空表
    cursor.execute("TRUNCATE TABLE faq")
    print("✅ 清空表成功")
    
    # 插入正确数据
    for question, answer in faq_data:
        cursor.execute(
            "INSERT INTO faq (question, answer) VALUES (%s, %s)",
            (question, answer)
        )
        print(f"✅ 插入: {question}")
    
    conn.commit()
    print(f"✅ 共插入 {len(faq_data)} 条记录")
    
    # 验证
    cursor.execute("SELECT id, question FROM faq")
    rows = cursor.fetchall()
    print("\n验证结果:")
    for row in rows:
        print(f"  ID {row[0]}: {row[1]}")
    
    cursor.close()
    conn.close()
    
    print("\n✅ 数据修复完成！")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    sys.exit(1)
```

## File: project_prompt.md

- Extension: .md
- Language: markdown
- Size: 138212 bytes
- Created: 2026-04-29 10:29:35
- Modified: 2026-05-05 16:39:11

### Code

```markdown
# Table of Contents
- .env.example
- .gitignore
- check_text_chain.py
- docker-compose.yml
- insert_sql.sql
- project_prompt.md
- README.md
- Record.md
- requirements.txt
- roadmap.md
- test_milvus.py
- test_sql.py
- verify_milvus_collection_p0.py
- verify_mysql_faq_p0.py
- 项目问题清单.md
- app\main.py
- app\__init__.py
- app\api\routes_admin.py
- app\api\routes_query.py
- app\api\schemas.py
- app\api\__init__.py
- app\core\config.py
- app\core\logger.py
- app\core\metrics.py
- app\generation\answer_postprocess.py
- app\generation\llm_client.py
- app\generation\prompt_builder.py
- app\handlers\error_handler.py
- app\indexing\embedding_worker.py
- app\indexing\loaders.py
- app\indexing\milvus_upsert.py
- app\indexing\splitter.py
- app\indexing\__init__.py
- app\middleware\metrics_middleware.py
- app\middleware\request_logger.py
- app\models\document.py
- app\models\query.py
- app\models\response.py
- app\retrieval\bm25_retriever.py
- app\retrieval\hybrid_retriever.py
- app\retrieval\milvus_retriever.py
- app\retrieval\mysql_faq_retriever.py
- app\router\intent_router.py
- data\seed\demo_knowledge.jsonl
- docker\mysql\init\001_init_faq.sql
- scripts\reindex.py
- scripts\trace_log.py

## File: .env.example

- Extension: .example
- Language: unknown
- Size: 575 bytes
- Created: 2026-04-28 22:21:35
- Modified: 2026-04-29 19:27:06

### Code

```unknown
﻿APP_NAME=rag-project
APP_ENV=dev
LOG_LEVEL=INFO
DEBUG=false

MYSQL_ROOT_PASSWORD=CHANGE_ME
MYSQL_DATABASE=rag
TZ=Asia/Shanghai

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=CHANGE_ME
MYSQL_FAQ_TABLE=faq

MILVUS_HOST=127.0.0.1
MILVUS_PORT=19530
MILVUS_COLLECTION=rag_docs
MILVUS_USER=
MILVUS_PASSWORD=

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION=384
EMBEDDING_BATCH_SIZE=32
CHUNK_SIZE=500
CHUNK_OVERLAP=80

OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_MAX_OUTPUT_TOKENS=800

```

## File: .gitignore

- Extension: 
- Language: unknown
- Size: 380 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```unknown
# Python 缓存与字节码
__pycache__/
*.pyc
*.pyo
*.pyd

# 日志文件
logs/
*.log

# 环境与配置
.env
.venv/
venv/
.pytest_cache/

# 你的项目特有配置
# 如果 config.dev.yaml 里有敏感密码，建议把它也加入忽略列表
# 或者只上传一个 config.dev.yaml.example
configs/config.dev.yaml

# 你的本地开发文件
log_test.py
```

## File: check_text_chain.py

- Extension: .py
- Language: python
- Size: 5979 bytes
- Created: 2026-04-29 15:29:05
- Modified: 2026-04-29 15:39:04

### Code

```python
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
      
```

## File: docker-compose.yml

- Extension: .yml
- Language: yaml
- Size: 2497 bytes
- Created: 2026-04-28 17:25:50
- Modified: 2026-04-29 17:58:19

### Code

```yaml
﻿services:
  mysql:
    image: mysql:8.0
    container_name: rag-mysql
    restart: unless-stopped
    ports:
      - "3307:3306"
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${MYSQL_DATABASE}
      TZ: ${TZ}
      LANG: C.UTF-8
      LC_ALL: C.UTF-8
    command:
      - --default-authentication-plugin=mysql_native_password
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
      - --skip-character-set-client-handshake
    volumes:
      - mysql_data:/var/lib/mysql
      - ./docker/mysql/init:/docker-entrypoint-initdb.d

  adminer:
    image: adminer:latest
    container_name: rag-adminer
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      ADMINER_DEFAULT_SERVER: mysql
    depends_on:
      - mysql

  etcd:
    container_name: milvus-etcd
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - etcd_data:/etcd
    command:
      - etcd
      - -advertise-client-urls=http://127.0.0.1:2379
      - -listen-client-urls
      - http://0.0.0.0:2379
      - --data-dir
      - /etcd
    healthcheck:
      test: ["CMD", "etcdctl", "endpoint", "health"]
      interval: 30s
      timeout: 20s
      retries: 3

  minio:
    container_name: milvus-minio
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    ports:
      - "9001:9001"
      - "9000:9000"
    volumes:
      - minio_data:/minio_data
    command: minio server /minio_data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  milvus-standalone:
    container_name: milvus-standalone
    image: milvusdb/milvus:v2.3.4
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    volumes:
      - milvus_data:/var/lib/milvus
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      interval: 30s
      start_period: 90s
      timeout: 20s
      retries: 3
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - etcd
      - minio

volumes:
  mysql_data:
  etcd_data:
  minio_data:
  milvus_data:

```

## File: insert_sql.sql

- Extension: .sql
- Language: sql
- Size: 2048 bytes
- Created: 2026-04-29 09:56:48
- Modified: 2026-04-29 10:10:06

### Code

```sql
#!/usr/bin/env python
"""修复数据库编码问题 - 重新插入正确的 UTF-8 数据"""

import pymysql
import sys

# 数据库配置
config = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'rag',
    'charset': 'utf8mb4',
    'use_unicode': True
}

# 正确的数据
faq_data = [
    ("你是谁", "我是 RAG 智能助手，基于检索增强生成技术构建，可以回答你的问题。"),
    ("你能做什么", "我可以回答问题、提供信息、协助解决问题等。"),
    ("什么是RAG", "RAG（Retrieval-Augmented Generation）是一种结合检索和生成的 AI 技术。"),
    ("如何使用", "直接输入问题，我会从知识库中检索相关信息并给出答案。"),
    ("联系方式", "请通过项目仓库提交问题或建议。"),
    ("系统健康吗", "系统当前运行正常，所有服务可用。")
]

print("="*60)
print("修复数据库编码")
print("="*60)

try:
    # 连接数据库
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    # 检查当前数据
    cursor.execute("SELECT COUNT(*) FROM faq")
    count = cursor.fetchone()[0]
    print(f"当前记录数: {count}")
    
    # 清空表
    cursor.execute("TRUNCATE TABLE faq")
    print("✅ 清空表成功")
    
    # 插入正确数据
    for question, answer in faq_data:
        cursor.execute(
            "INSERT INTO faq (question, answer) VALUES (%s, %s)",
            (question, answer)
        )
        print(f"✅ 插入: {question}")
    
    conn.commit()
    print(f"✅ 共插入 {len(faq_data)} 条记录")
    
    # 验证
    cursor.execute("SELECT id, question FROM faq")
    rows = cursor.fetchall()
    print("\n验证结果:")
    for row in rows:
        print(f"  ID {row[0]}: {row[1]}")
    
    cursor.close()
    conn.close()
    
    print("\n✅ 数据修复完成！")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    sys.exit(1)
```

## File: project_prompt.md

- Extension: .md
- Language: markdown
- Size: 34772 bytes
- Created: 2026-04-29 10:29:35
- Modified: 2026-04-29 10:29:35

### Code

```markdown
# Table of Contents
- .env.example
- .gitignore
- docker-compose.yml
- insert_sql.sql
- README.md
- requirements.txt
- roadmap.md
- test_sql.py
- app\main.py
- app\__init__.py
- app\api\routes_admin.py
- app\api\routes_query.py
- app\api\schemas.py
- app\api\__init__.py
- app\core\config.py
- app\core\logger.py
- app\core\metrics.py
- app\generation\llm_client.py
- app\handlers\error_handler.py
- app\middleware\metrics_middleware.py
- app\middleware\request_logger.py
- app\models\query.py
- app\models\response.py
- app\retrieval\hybrid_retriever.py
- app\retrieval\mysql_faq_retriever.py
- app\router\intent_router.py
- docker\mysql\init\001_init_faq.sql
- scripts\trace_log.py

## File: .env.example

- Extension: .example
- Language: unknown
- Size: 177 bytes
- Created: 2026-04-28 22:21:35
- Modified: 2026-04-28 22:24:43

### Code

```unknown
APP_NAME=rag-project
APP_ENV=dev
LOG_LEVEL=INFO
DEBUG=false

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=CHANGE_ME
MYSQL_DATABASE=rag
MYSQL_FAQ_TABLE=faq
```

## File: .gitignore

- Extension: 
- Language: unknown
- Size: 380 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```unknown
# Python 缓存与字节码
__pycache__/
*.pyc
*.pyo
*.pyd

# 日志文件
logs/
*.log

# 环境与配置
.env
.venv/
venv/
.pytest_cache/

# 你的项目特有配置
# 如果 config.dev.yaml 里有敏感密码，建议把它也加入忽略列表
# 或者只上传一个 config.dev.yaml.example
configs/config.dev.yaml

# 你的本地开发文件
log_test.py
```

## File: docker-compose.yml

- Extension: .yml
- Language: yaml
- Size: 708 bytes
- Created: 2026-04-28 17:25:50
- Modified: 2026-04-29 08:41:57

### Code

```yaml
services:
  mysql:
    image: mysql:8.0
    container_name: rag-mysql
    restart: unless-stopped
    env_file: .env
    ports:
      - "3307:3306"  # <--- 必须修改为 3307:3306
    command:
      - --default-authentication-plugin=mysql_native_password
      - --character-set-server=utf8mb4
      - --collation-server=utf8mb4_unicode_ci
    volumes:
      - mysql_data:/var/lib/mysql
      - ./docker/mysql/init:/docker-entrypoint-initdb.d

  adminer:
    image: adminer:latest
    container_name: rag-adminer
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      ADMINER_DEFAULT_SERVER: mysql
    depends_on:
      - mysql

volumes:
  mysql_data:
```

## File: insert_sql.sql

- Extension: .sql
- Language: sql
- Size: 2048 bytes
- Created: 2026-04-29 09:56:48
- Modified: 2026-04-29 10:10:06

### Code

```sql
#!/usr/bin/env python
"""修复数据库编码问题 - 重新插入正确的 UTF-8 数据"""

import pymysql
import sys

# 数据库配置
config = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'rag',
    'charset': 'utf8mb4',
    'use_unicode': True
}

# 正确的数据
faq_data = [
    ("你是谁", "我是 RAG 智能助手，基于检索增强生成技术构建，可以回答你的问题。"),
    ("你能做什么", "我可以回答问题、提供信息、协助解决问题等。"),
    ("什么是RAG", "RAG（Retrieval-Augmented Generation）是一种结合检索和生成的 AI 技术。"),
    ("如何使用", "直接输入问题，我会从知识库中检索相关信息并给出答案。"),
    ("联系方式", "请通过项目仓库提交问题或建议。"),
    ("系统健康吗", "系统当前运行正常，所有服务可用。")
]

print("="*60)
print("修复数据库编码")
print("="*60)

try:
    # 连接数据库
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    
    # 检查当前数据
    cursor.execute("SELECT COUNT(*) FROM faq")
    count = cursor.fetchone()[0]
    print(f"当前记录数: {count}")
    
    # 清空表
    cursor.execute("TRUNCATE TABLE faq")
    print("✅ 清空表成功")
    
    # 插入正确数据
    for question, answer in faq_data:
        cursor.execute(
            "INSERT INTO faq (question, answer) VALUES (%s, %s)",
            (question, answer)
        )
        print(f"✅ 插入: {question}")
    
    conn.commit()
    print(f"✅ 共插入 {len(faq_data)} 条记录")
    
    # 验证
    cursor.execute("SELECT id, question FROM faq")
    rows = cursor.fetchall()
    print("\n验证结果:")
    for row in rows:
        print(f"  ID {row[0]}: {row[1]}")
    
    cursor.close()
    conn.close()
    
    print("\n✅ 数据修复完成！")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    sys.exit(1)
```

## File: README.md

- Extension: .md
- Language: markdown
- Size: 663 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```markdown
## 项目目标
基于 FastAPI 的 RAG 问答系统：FAQ 直查 + RAG 回退，采用 MySQL/Milvus/Redis 架构，支持结构化日志与 Prometheus 监控

## 技术栈
* **API Framework**: FastAPI
* **Vector Store**: Milvus
* **Metadata Store**: MySQL
* **Monitoring**: Prometheus
* **Core Design**: Hybrid Retrieval & Intent Routing

## 当前进度 (Day 1)
- [x] 工程骨架搭建
- [x] 日志链路追踪 (RequestID)
- [x] 统一异常处理与指标监控
- [x] 意图路由基础占位
- [x] Mock 主链路联调

## 下一步计划
- [ ] 接入 MySQL FAQ 检索
- [ ] 接入 Milvus 向量检索
- [ ] 实现 RRF 混合重排算法

```

## File: requirements.txt

- Extension: .txt
- Language: plaintext
- Size: 279 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 16:30:12

### Code

```plaintext
# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.30.6
prometheus-client==0.20.0

# Data Validation
pydantic==2.9.0
pydantic-settings==2.5.0

# Config
pyyaml==6.0.2

# Logging
structlog==24.4.0

#=
PyMySQL
pymilvus

openai
httpx
sentence-transformers


```

## File: roadmap.md

- Extension: .md
- Language: markdown
- Size: 2391 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```markdown
rag_project/
├─ app/
│    ├─ main.py  ✅应用入口与装配层    
      初始化日志；注册中间件（请求日志、指标采集）；注册全局异常处理；挂载 /metrics；提供 /health 健康检查。
│    ├─ api/  
│    │  ├─ routes_query.py
│    │  ├─ routes_admin.py
│    │  └─ schemas.py

│    ├─ core/    ✅
│    │  ├─ config.py    #统一配置源
│    │  ├─ logger.py    #统一日志格式与输出通道
         通过 RequestIdFilter 给日志补 request_id；配置 console + file 双输出；格式统一；可接管 uvicorn 日志写入同一文件。
│    │  └─ metrics.py   #指标定义层

│    ├─ middleware/  ✅
│    │  ├─ request_context.py
│    │  ├─ request_logger.py    #请求日志中间件
│    │  └─ metrics_middleware.py    #请求指标中间件

│    ├─ handlers/   ✅
│    │  └─ error_handler.py     #统一异常出口

│    ├─ models/
│    │  ├─ document.py
│    │  ├─ query.py
│    │  └─ response.py

│    ├─ router/
│    │  ├─ intent_router.py
│    │  └─ threshold_policy.py

│    ├─ retrieval/
│    │  ├─ mysql_faq_retriever.py
│    │  ├─ bm25_retriever.py
│    │  ├─ milvus_retriever.py
│    │  ├─ hybrid_retriever.py
│    │  └─ reranker.py

│    ├─ generation/
│    │  ├─ prompt_builder.py
│    │  ├─ llm_client.py
│    │  └─ answer_postprocess.py

│    ├─ indexing/
│    │  ├─ loaders.py
│    │  ├─ splitter.py
│    │  ├─ embedding_worker.py
│    │  └─ milvus_upsert.py

│    ├─ cache/
│    │  ├─ redis_cache.py
│    │  └─ cache_keys.py

│    ├─ eval/
│    │  ├─ dataset.py
│    │  ├─ offline_eval.py
│    │  └─ online_eval.py

│    └─ tests/
│       ├─ test_api.py
│       ├─ test_router.py
│       ├─ test_retrieval.py
│       └─ test_generation.py

├─ scripts/
│  ├─ reindex.py
│  ├─ warmup_cache.py
│  └─ replay_logs.py

├─ configs/
│  ├─ config.dev.yaml
│  ├─ config.prod.yaml
│  └─ prompts.yaml

├─ requirements.txt

└─ README.md

```

## File: test_sql.py

- Extension: .py
- Language: python
- Size: 4106 bytes
- Created: 2026-04-28 22:36:51
- Modified: 2026-04-29 08:25:59

### Code

```python
#!/usr/bin/env python
"""测试 MySQL FAQ Retriever 连接"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.retrieval.mysql_faq_retriever import MysqlFAQRetriever
from app.core.config import settings

def test_connection():
    print("="*60)
    print("测试 MySQL 连接配置")
    print("="*60)
    
    # 1. 打印配置
    print(f"\n1. 当前配置:")
    print(f"   Host: {settings.mysql_host}")
    print(f"   Port: {settings.mysql_port}")
    print(f"   User: {settings.mysql_user}")
    print(f"   Database: {settings.mysql_database}")
    print(f"   Table: {settings.mysql_faq_table}")
    
    # 2. 测试直接连接
    print(f"\n2. 测试数据库连接...")
    try:
        retriever = MysqlFAQRetriever()
        print("   ✅ Retriever 初始化成功")
    except Exception as e:
        print(f"   ❌ Retriever 初始化失败: {e}")
        return False
    
    # 3. 测试查询
    print(f"\n3. 测试查询...")
    test_queries = [
        "什么是RAG？",
        "如何使用FastAPI？",
        "测试查询"
    ]
    
    for test_query in test_queries:
        print(f"\n   查询: '{test_query}'")
        try:
            result = retriever.retrieve(test_query)
            if result:
                print(f"   ✅ 找到结果: {result.question[:50]}...")
                print(f"      答案: {result.answer[:100]}...")
            else:
                print(f"   ⚠️ 未找到结果")
        except Exception as e:
            print(f"   ❌ 查询失败: {e}")
    
    return True

def test_direct_pymysql():

    # 在尝试连接前，强制打印确认配置
    print(f"\n[DEBUG] 正在尝试连接: Host={settings.mysql_host}, User={settings.mysql_user}, DB={settings.mysql_database}")

    """直接使用 pymysql 测试连接"""
    print("\n" + "="*60)
    print("直接 PyMySQL 连接测试")
    print("="*60)
    
    import pymysql
    
    try:
        conn = pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset="utf8mb4",
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor,
        )
        print("✅ 连接成功")
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION() as version, NOW() as now")
            result = cursor.fetchone()
            print(f"   MySQL 版本: {result['version']}")
            print(f"   当前时间: {result['now']}")
            
            # 检查表是否存在
            cursor.execute(f"SHOW TABLES LIKE '{settings.mysql_faq_table}'")
            if cursor.fetchone():
                print(f"   ✅ 表 '{settings.mysql_faq_table}' 存在")
                
                # 统计记录数
                cursor.execute(f"SELECT COUNT(*) as count FROM {settings.mysql_faq_table}")
                count = cursor.fetchone()
                print(f"   总记录数: {count['count']}")
            else:
                print(f"   ❌ 表 '{settings.mysql_faq_table}' 不存在")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print(f"   错误类型: {type(e).__name__}")
        return False

if __name__ == "__main__":
    # 先测试直接连接
    if test_direct_pymysql():
        print("\n" + "="*60)
        print("直接连接成功！现在测试 Retriever")
        test_connection()
    else:
        print("\n❌ 直接连接失败，请检查配置")
        
        # 提供调试建议
        print("\n调试建议:")
        print("1. 确认 .env 文件中的 MYSQL_HOST 是否正确")
        print("2. 检查防火墙设置")
        print("3. 尝试在 PowerShell 中运行: mysql -h 172.18.37.202 -P 3306 -uroot -proot -e 'SELECT 1'")
```

## File: app\main.py

- Extension: .py
- Language: python
- Size: 1315 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.logger import setup_logger

from app.handlers.error_handler import register_exception_handlers
from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.request_logger import RequestLoggerMiddleware
from app.api.routes_query import router as query_router

# 注册了哪些中间件？挂了哪些路由？异常处理在哪接入？

def create_app() -> FastAPI:

    setup_logger()

    app = FastAPI(title=settings.app_name,debug=settings.debug)
    @app.middleware("http")
    async def ensure_utf8_json(request, call_next):
        resp = await call_next(request)
        ct = resp.headers.get("content-type", "")
        if ct.startswith("application/json") and "charset" not in ct:
            resp.headers["content-type"] = "application/json; charset=utf-8"
        return resp

    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(MetricsMiddleware)

    register_exception_handlers(app)
    app.mount("/metrics", make_asgi_app())

    @app.get("/health")
    def health():
        return {"status": "ok", "env": settings.app_env}

    return app

app = create_app()
app.include_router(query_router)
```

## File: app\__init__.py

- Extension: .py
- Language: python
- Size: 0 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

```

## File: app\api\routes_admin.py

- Extension: .py
- Language: python
- Size: 0 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

```

## File: app\api\routes_query.py

- Extension: .py
- Language: python
- Size: 1980 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-29 09:28:25

### Code

```python
from fastapi import APIRouter, Request

from app.api.schemas import QueryRequest, QueryResponse, DocItem
from app.router.intent_router import IntentRouter
from app.models.query import RetrievalStrategy
from app.retrieval.hybrid_retriever import HybridRetriever
from app.generation.llm_client import LLMClient
from app.retrieval.mysql_faq_retriever import MysqlFAQRetriever
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["query"])

intent_router = IntentRouter()
faq_retriever = MysqlFAQRetriever()
retriever = HybridRetriever()
llm = LLMClient()


@router.post("/query", response_model=QueryResponse)
def query_api(req: QueryRequest, request: Request):
    
    trace_id = getattr(request.state, "request_id", "-")
    decision = intent_router.route(req.query)

    logger.info(f"[{trace_id}] Query: {req.query} | Route Strategy: {decision.strategy}")

    if decision.strategy == RetrievalStrategy.DIRECT_FAQ:
        faq_hit = faq_retriever.retrieve(req.query)
        if faq_hit:
            return QueryResponse(
                trace_id=trace_id,
                query=req.query,
                answer=faq_hit.answer,
                source="faq",
                route=decision.strategy.value,
                confidence=faq_hit.score,
                citations=[faq_hit.faq_id],
                retrieved_docs=[],
            )

    docs = retriever.retrieve(req.query, req.top_k)
    ans = llm.generator(req.query, docs)

    return QueryResponse(
        trace_id=trace_id,
        query=req.query,
        answer=ans.text,
        source="rag",
        route=RetrievalStrategy.RAG.value,
        confidence=decision.confidence,
        citations=ans.citations,
        retrieved_docs=[
            DocItem(
                doc_id=d.doc_id, 
                score=float(d.score), 
                snippet=d.snippet
            )for d in docs 
        ],
    )

```

## File: app\api\schemas.py

- Extension: .py
- Language: python
- Size: 525 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(3, ge=1, le=10)


class DocItem(BaseModel):
    doc_id: str
    score: float
    snippet: str


class QueryResponse(BaseModel):
    trace_id: str
    query: str
    answer: str
    source: str
    route: str
    confidence: float
    citations: list[str] = Field(default_factory=list)
    retrieved_docs: list[DocItem] = Field(default_factory=list)

```

## File: app\api\__init__.py

- Extension: .py
- Language: python
- Size: 0 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

```

## File: app\core\config.py

- Extension: .py
- Language: python
- Size: 981 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-29 08:49:48

### Code

```python
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"

class Settings(BaseSettings):
    # 基础配置
    app_name: str = "rag-project"
    app_env: str = "dev"
    log_level: str = "INFO"
    debug: bool = False

    # 数据库配置 (自动从 .env 读取)
    mysql_host: str = Field(..., alias="MYSQL_HOST")
    mysql_port: int = Field(3306, alias="MYSQL_PORT")
    mysql_user: str = Field(..., alias="MYSQL_USER")
    mysql_password: str = Field(..., alias="MYSQL_PASSWORD")
    mysql_database: str = Field(..., alias="MYSQL_DATABASE")
    mysql_faq_table: str = Field("faq", alias="MYSQL_FAQ_TABLE")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore" # 忽略环境中多余的变量
    )

settings = Settings()
```

## File: app\core\logger.py

- Extension: .py
- Language: python
- Size: 2057 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
import logging
from logging.config import dictConfig
from pathlib import Path
from app.core.config import settings


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def setup_logger() -> None:
    log_dir = getattr(settings, "log_dir", "logs")
    log_file = getattr(settings, "log_file", "app.log")
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_id_filter": {"()": RequestIdFilter}
            },
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(request_id)s | %(name)s | %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "filters": ["request_id_filter"],
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": str(Path(log_dir) / log_file),
                    "maxBytes": 10 * 1024 * 1024,
                    "backupCount": 5,
                    "formatter": "standard",
                    "filters": ["request_id_filter"],
                    "encoding": "utf-8",
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": settings.log_level.upper(),
            },
        }
    )

    # 让 uvicorn 日志走 root，统一进入文件
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

```

## File: app\core\metrics.py

- Extension: .py
- Language: python
- Size: 673 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from prometheus_client import Counter,Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "HTTP 请求总数",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP 请求耗时(秒)",
    ["method", "path"],
)

def record_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        path=path,
        status_code=str(status_code),
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method,
        path=path,
    ).observe(duration_seconds)
```

## File: app\generation\llm_client.py

- Extension: .py
- Language: python
- Size: 498 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from typing import List
from multiprocessing import context
from app.models.response import RetrievedDoc, GeneratedAnswer

class LLMClient:
    def generator(self, query: str, docs: List[RetrievedDoc]) -> GeneratedAnswer:
        context = ';'.join([d.snippet for d in docs])
        return GeneratedAnswer(
            text=f"基于检索结果，关于「{query}」”的回答是：{context}",
            citations=[d.doc_id for d in docs],
            model="mock-llm-v1",
        )
```

## File: app\handlers\error_handler.py

- Extension: .py
- Language: python
- Size: 1424 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.logger import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", "-")
        logger.warning(
            "http_exception status=%s detail=%s",
            exc.status_code,
            exc.detail,
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": str(exc.detail),
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "-")
        logger.exception(
            "unhandled_exception: %s",
            str(exc),
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "Internal Server Error",
                "request_id": request_id,
            },
        )

```

## File: app\middleware\metrics_middleware.py

- Extension: .py
- Language: python
- Size: 634 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.metrics import record_http_request


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        record_http_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration,
        )
        return response

```

## File: app\middleware\request_logger.py

- Extension: .py
- Language: python
- Size: 933 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logger import get_logger

logger = get_logger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={"request_id": request_id},
        )

        response.headers["X-Request-ID"] = request_id
        return response

```

## File: app\models\query.py

- Extension: .py
- Language: python
- Size: 820 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from dataclasses import dataclass
from enum import Enum

# TODO 将其升级为 Pydantic 的 BaseModel

class Intent(str,Enum): 
    FAQ = 'faq'                # FAQ: Frequently Asked Questions
    KNOWLEDGE = 'knowledge'

class RetrievalStrategy(str,Enum): #当你继承 Enum 时，Python 自动把你定义里的所有类属性（如 RAG）都转换成了一个对象（Instance）
    DIRECT_FAQ = "direct_faq"      #若不继承str，则输出: <enum 'MyEnum'> (它不是字符串，它是 MyEnum 这个枚举类的一个实例)
    RAG = "rag"

@dataclass  
class RouteDecision:    # if decision.confidence > 0.95: ...
    intent:Intent        # Python 的 “委托” (Delegation) 和 “混入” (Mixin)
    strategy:RetrievalStrategy
    confidence:float  
    direct_answer:str | None = None
```

## File: app\models\response.py

- Extension: .py
- Language: python
- Size: 533 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from dataclasses import dataclass

# TODO 将其升级为 Pydantic 的 BaseModel

@dataclass
class  RetrievedDoc:

    # TODO 后续扩充 metadata: dict 字段,把页码、章节、文件来源 URL 塞进去
    
    doc_id: str
    score: float
    snippet: str
    # matadata: json
     
@dataclass
class GeneratedAnswer:
    text: str
    citations: list[str]
    model: str # 不同模型间进行 A/B 测试或者平滑迁移时，这个字段能帮你追踪到：这条答案到底是哪个模型生成的。
```

## File: app\retrieval\hybrid_retriever.py

- Extension: .py
- Language: python
- Size: 651 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from app.models.response import RetrievedDoc
from typing import List

# 在 FastAPI 中，所有的 I/O 操作（未来你的数据库查询、LLM 调用）都是异步的

class HybridRetriever:
    def retrieve(self,query:str,top_k:int = 3) -> List[RetrievedDoc]:
        docs = [
            RetrievedDoc(doc_id="doc-1", score=0.89, snippet=f"与“{query}”相关的知识片段A"),
            RetrievedDoc(doc_id="doc-2", score=0.82, snippet=f"与“{query}”相关的知识片段B"),
            RetrievedDoc(doc_id="doc-3", score=0.77, snippet=f"与“{query}”相关的知识片段C"),
        ]
        return docs[:top_k]


```

## File: app\retrieval\mysql_faq_retriever.py

- Extension: .py
- Language: python
- Size: 2486 bytes
- Created: 2026-04-28 16:02:26
- Modified: 2026-04-29 09:51:57

### Code

```python
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
```

## File: app\router\intent_router.py

- Extension: .py
- Language: python
- Size: 684 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 16:04:34

### Code

```python
from app.models.query import Intent, RetrievalStrategy, RouteDecision
class IntentRouter:
    def route(self, query: str) -> RouteDecision:
        q = query.strip()
        # Day2 Step1: 这里只保留轻量路由判断，不再直接返回 FAQ 内容
        if len(q) <= 20:
            return RouteDecision(
                intent=Intent.FAQ,
                strategy=RetrievalStrategy.DIRECT_FAQ,
                confidence=0.80,
                direct_answer=None,
            )
        return RouteDecision(
            intent=Intent.KNOWLEDGE,
            strategy=RetrievalStrategy.RAG,
            confidence=0.60,
            direct_answer=None,
        )
```

## File: docker\mysql\init\001_init_faq.sql

- Extension: .sql
- Language: sql
- Size: 339 bytes
- Created: 2026-04-28 17:26:45
- Modified: 2026-04-29 08:12:27

### Code

```sql
USE rag;
CREATE TABLE IF NOT EXISTS faq (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    question VARCHAR(255) NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO faq (question, answer) VALUES
('你是谁', '我是你的RAG助手。'),
('系统健康吗', '系统当前健康。');
```

## File: scripts\trace_log.py

- Extension: .py
- Language: python
- Size: 1439 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
import argparse
import sys
from pathlib import Path

def trace_request(log_path: str, request_id: str):
    """
    按 request_id 筛选日志行
    """
    log_file = Path(log_path)
    if not log_file.exists():
        print(f"❌ 错误: 日志文件未找到: {log_path}")
        return

    print(f"🔍 正在追踪 Request ID: [{request_id}] ...\n" + "-"*50)
    
    found_count = 0
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # 假设日志格式中包含了 request_id
                if request_id in line:
                    print(line.strip())
                    found_count += 1
        
        if found_count == 0:
            print(f"⚠️ 未找到关联该 ID 的日志条目，请确认 ID 是否正确或日志路径是否匹配。")
        else:
            print("-"*50 + f"\n✅ 扫描结束，共找到 {found_count} 条相关日志。")
            
    except Exception as e:
        print(f"❌ 读取日志时发生错误: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="根据 Request ID 快速定位日志")
    parser.add_argument("req_id", help="需要查询的 request_id")
    parser.add_argument("--file", default="logs/app.log", help="日志文件路径 (默认: logs/app.log)")
    
    args = parser.parse_args()
    trace_request(args.file, args.req_id)
```


```

## File: README.md

- Extension: .md
- Language: markdown
- Size: 1356 bytes
- Created: 2026-04-29 23:27:29
- Modified: 2026-04-29 23:27:29

### Code

```markdown
## 项目目标
基于 FastAPI 的 RAG 问答系统：FAQ 直查 + RAG 回退，采用 MySQL/Milvus/Redis 架构，支持结构化日志与 Prometheus 监控

## 技术栈
* **API Framework**: FastAPI
* **Vector Store**: Milvus
* **Metadata Store**: MySQL
* **Monitoring**: Prometheus
* **Core Design**: Hybrid Retrieval & Intent Routing

## 当前进度 (Day 1)
- [x] 工程骨架搭建
- [x] 日志链路追踪 (RequestID)
- [x] 统一异常处理与指标监控
- [x] 意图路由基础占位
- [x] Mock 主链路联调

## 下一步计划
- [x] 接入 MySQL FAQ 检索
- [x] 接入 Milvus 向量检索
- [x] 实现 RRF 混合重排算法

### 今日任务概述(Day 2)

- 修复 MySQL 连接与 FAQ 初始化环境
- 接入最小真实 RAG 链路
- 抽离离线索引流数据结构

### 关键改动

- 修复 Docker / .env.example / 初始化 SQL / test_sql.py
- 新增 indexing 模块与 scripts/reindex.py
- HybridRetriever 改为真实 embedding 检索
- LLMClient 改为真实调用骨架
- 新增 app/models/document.py
- 修复并重建 Record.md

### 当前结果

- FAQ 链路可用
- MySQL 连接稳定
- reindex 入口可用
- RAG 主链路已从 mock 走向真实实现


### 后续计划

- 解耦 generation 层
- 准备真实文档并完成 reindex
- 验证 /query 的完整 RAG 路径

```

## File: Record.md

- Extension: .md
- Language: markdown
- Size: 15421 bytes
- Created: 2026-04-28 15:59:42
- Modified: 2026-05-05 16:18:03

### Code

```markdown
﻿# Project Record

## Day 1

### [Step 1] 主链路骨架完成

- 时间：2026-04-28
- 目标：先跑通 `/query` 的最小主链路，具备 FAQ 直返和 RAG 回退骨架。
- 变更内容：
  - 搭建 FastAPI 应用入口与基础目录结构。
  - 增加 `/health` 健康检查接口。
  - 增加请求日志中间件，记录 `request_id`、耗时、状态码。
  - 增加指标中间件与统一异常处理。
  - 增加 `IntentRouter`、`HybridRetriever`、`LLMClient` 的最小链路。
- 涉及文件：
  - `app/main.py`
  - `app/api/routes_query.py`
  - `app/router/intent_router.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/generation/llm_client.py`
  - `app/middleware/request_logger.py`
  - `app/middleware/metrics_middleware.py`
  - `app/handlers/error_handler.py`
- 当前结果：
  - `/query` 主链路代码可运行。
  - FAQ 命中可直接返回，未命中可进入 RAG 骨架。
- 验证方式：
  - 本地联调 `/query`
  - 检查日志输出与 `/health`
- 下一步：
  - 拆出 FAQ 检索器，替换硬编码 FAQ。

## Day 2

### [Step 1] 拆分 FAQ 检索职责

- 时间：2026-04-28
- 目标：将 FAQ 问答能力从路由层拆出，形成独立 FAQ 检索器。
- 变更内容：
  - 新增 `MysqlFAQRetriever`，封装 FAQ 查询接口。
  - 新增 `FAQHit` 结构，统一 FAQ 命中结果。
  - 将 `IntentRouter` 从“直接返回 FAQ 内容”调整为“只负责路由判断”。
  - 在 `/query` 主链路中接入 FAQ 检索。
- 涉及文件：
  - `app/retrieval/mysql_faq_retriever.py`
  - `app/router/intent_router.py`
  - `app/api/routes_query.py`
- 当前结果：
  - FAQ 命中逻辑已从路由层剥离。
  - 主链路职责更清晰。
- 验证方式：
  - FAQ 问题优先命中 FAQ 检索器。
  - 非 FAQ 问题继续走 RAG 路径。
- 下一步：
  - 将 FAQ 数据源接到真实 MySQL。

### [Step 2] FAQ 检索器接入 MySQL 查询骨架

- 时间：2026-04-28
- 目标：把 FAQ 检索从 mock 升级成真实数据库访问骨架。
- 变更内容：
  - 在 `config.py` 中增加 MySQL FAQ 相关配置。
  - 将 `MysqlFAQRetriever` 改为访问 MySQL。
  - FAQ 查询策略先采用精确匹配。
- 涉及文件：
  - `app/core/config.py`
  - `app/retrieval/mysql_faq_retriever.py`
- 当前结果：
  - FAQ 数据源已切到 MySQL。
  - 为后续真实 FAQ 维护预留了接口。
- 验证方式：
  - 在 MySQL 中准备 FAQ 测试数据。
  - 请求 FAQ 问题并确认返回数据库结果。
- 下一步：
  - 接入向量检索，补齐 RAG 链路。

### [架构补充] 同步 I/O 策略评估与异步升级计划

- 时间：2026-04-28
- 背景：当前 `/query`、`MysqlFAQRetriever` 先以同步实现满足低并发联调。
- 当前判断：
  - 本地开发与演示阶段，同步实现成本更低。
  - 随着 Milvus 与 LLM 调用接入，外部 I/O 会增加，同步模式会逐渐成为瓶颈。
- 风险点：
  - MySQL 每次请求新建连接，存在重复连接开销。
  - Milvus / LLM 持续用同步调用会影响并发能力。
- 结论：
  - 当前阶段先不强制异步化。
  - 后续真实外部 I/O 接入后，再评估 `async` 改造时机。
- 后续升级项：
  - `/query` 改为 `async def`
  - FAQ / Milvus / LLM 逐步异步化
  - 引入连接复用或连接池

### [环境准备] FAQ MySQL 数据表初始化

- 时间：2026-04-28
- 目标：为 FAQ 检索准备 MySQL 数据源。
- 变更内容：
  - 设计 `rag.faq` 表结构。
  - 准备 FAQ 初始化数据。
- 验证方式：
  - 直接 SQL 查询 `faq` 表。
  - 验证关键 FAQ 问题是否可精确命中。
- 下一步：
  - 完成 Docker 化部署并接通应用访问。

### [环境准备] MySQL Docker Compose 方案

- 时间：2026-04-28
- 目标：通过 Docker Compose 启动 MySQL，并自动初始化 FAQ 数据表。
- 变更内容：
  - 设计 `docker-compose.yml` 中的 MySQL 服务。
  - 暴露宿主机端口供本地 Python 应用访问。
  - 挂载初始化 SQL 目录。
- 配置约定：
  - 数据库：`rag`
  - FAQ 表：`faq`
  - 宿主机连接：`127.0.0.1:3307`
- 下一步：
  - 启动 MySQL 并验证 FAQ 表初始化。

## Day 3

### [Step 3] 接入 Milvus 向量检索

- 时间：2026-04-29
- 目标：将 RAG 链路从 mock 检索升级为真实向量检索。
- 变更内容：
  - 新增 `MilvusRetriever`，封装向量检索能力。
  - 增加 Milvus 相关配置项。
  - 将 `HybridRetriever` 改为调用 `MilvusRetriever`。
- 涉及文件：
  - `app/retrieval/milvus_retriever.py`
  - `app/core/config.py`
  - `app/retrieval/hybrid_retriever.py`
- 当前结果：
  - RAG 检索层具备真实向量检索骨架。
- 验证方式：
  - 启动 Milvus 容器并准备测试数据。
  - 请求非 FAQ 问题，确认能检索到文档。
- 下一步：
  - 完善真实 embedding 与索引链路。

### [环境准备] Milvus Docker Compose 配置

- 时间：2026-04-29
- 目标：为向量检索准备完整 Docker 环境。
- 变更内容：
  - 在 `docker-compose.yml` 中增加 `etcd`、`minio`、`milvus-standalone` 服务。
  - 配置依赖关系、健康检查、端口与数据卷。
- 配置约定：
  - Milvus：`19530`
  - MinIO：`9000 / 9001`
- 下一步：
  - 启动 Milvus 服务栈并验证健康状态。

### [测试验证] Milvus 服务健康性检查

- 时间：2026-04-29
- 目标：确认 Milvus 服务栈可用。
- 变更内容：
  - 通过 Compose 启动服务。
  - 编写 / 执行基础测试脚本验证连接与集合操作。
- 涉及文件：
  - `docker-compose.yml`
  - `test_milvus.py`
- 验证方式：
  - `docker compose ps`
  - `curl http://localhost:9091/healthz`
  - Python 连接测试
- 下一步：
  - 接入真实 embedding 与入库流程。

### [P0-1] 编码链路与 FAQ / Milvus 数据核验脚本

- 时间：2026-04-29
- 目标：定位乱码、FAQ 命中异常、Milvus 数据有效性问题。
- 变更内容：
  - 增加文本链路排查脚本。
  - 增加 FAQ 数据核验脚本。
  - 增加 Milvus 集合核验脚本。
- 涉及文件：
  - `scripts/check_text_chain.py`
  - `scripts/verify_mysql_faq_p0.py`
  - `scripts/verify_milvus_collection_p0.py`
- 当前结果：
  - 能独立判断乱码发生在源文件、入库链路、数据库存储还是日志显示。
- 下一步：
  - 修复 MySQL 字符集链路与脏数据。

### [P0-2] MySQL 字符集链路修正方案

- 时间：2026-04-29
- 目标：修正 FAQ 初始化链路中的字符集不一致问题，避免 UTF-8 中文被错误解释后写入 MySQL。
- 变更内容：
  - 统一应用、MySQL、初始化 SQL 的字符集链路。
  - 调整 `.env` / `docker-compose.yml` / 初始化 SQL 的相关配置。
- 涉及文件：
  - `app/core/config.py`
  - `docker-compose.yml`
  - `.env`
  - `.env.example`
  - `docker/mysql/init/001_init_faq.sql`
- 当前结果：
  - 新导入 FAQ 数据可以稳定按 UTF-8 入库。
- 下一步：
  - 删除旧库数据并重建 FAQ 数据。

### [P0-4] 修复 MySQL 连接环境问题

- 时间：2026-04-29
- 目标：修复 MySQL 容器反复重启、`test_sql.py` 无法连接、FAQ 初始化 SQL 无法正确执行的问题。
- 变更内容：
  - 修复 `.env` / `.env.example` 的格式问题。
  - 修复 `docker-compose.yml` 中 MySQL 容器的环境注入问题。
  - 修复 `docker/mysql/init/001_init_faq.sql` 的编码与 SQL 语法问题。
  - 重写 `test_sql.py`，提供干净的 MySQL 连通性验证。
- 涉及文件：
  - `.env`
  - `.env.example`
  - `docker-compose.yml`
  - `docker/mysql/init/001_init_faq.sql`
  - `test_sql.py`
- 当前结果：
  - MySQL 容器可正常启动。
  - `test_sql.py` 可连接并命中 FAQ 数据。
- 验证方式：
  - `docker compose config`
  - `docker compose down -v`
  - `docker compose up -d mysql`
  - `docker compose logs -f mysql`
  - `python test_sql.py`
- 下一步：
  - 继续推进 P1 的真实检索与生成链路。

### [P1-1] 接入最小真实索引链路与生成链路

- 时间：2026-04-29
- 目标：把随机向量检索与 mock 生成升级为最小可用的真实 RAG 主链路。
- 变更内容：
  - 在 `app/indexing/` 下补齐最小索引层：`loaders.py`、`splitter.py`、`embedding_worker.py`、`milvus_upsert.py`。
  - 新增 `scripts/reindex.py` 作为统一重建入口。
  - 将 `HybridRetriever` 改为真实 embedding 检索。
  - 将 `MilvusRetriever` 统一到配置维度。
  - 将 `LLMClient` 接入真实 OpenAI Responses API，并提供未配置密钥时的明确降级提示。
  - 扩展 embedding / chunk / OpenAI 相关配置。
- 涉及文件：
  - `app/core/config.py`
  - `app/indexing/__init__.py`
  - `app/indexing/loaders.py`
  - `app/indexing/splitter.py`
  - `app/indexing/embedding_worker.py`
  - `app/indexing/milvus_upsert.py`
  - `scripts/reindex.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/retrieval/milvus_retriever.py`
  - `app/generation/llm_client.py`
  - `requirements.txt`
- 当前结果：
  - 已具备最小文档入库链路。
  - 查询链路已升级为真实 embedding 检索。
  - 生成链路具备真实 LLM 接入能力。
- 验证方式：
  - `python scripts/reindex.py <input_path> --drop-old`
  - 配置 `OPENAI_API_KEY` 后请求 `/query`
- 下一步：
  - 准备真实文档并完成一次完整 reindex。

### [P1-2] 抽离离线索引流数据结构

- 时间：2026-04-29
- 目标：让离线索引链路中的文档数据结构从具体实现模块中解耦，形成清晰的内部模型边界。
- 变更内容：
  - 新增 `app/models/document.py`，统一承载 `SourceDocument` 与 `DocumentChunk`。
  - 调整 `app/indexing/loaders.py` 引用 `app.models.document`。
  - 调整 `app/indexing/splitter.py` 引用 `app.models.document`。 //纯字符计数切分
  - 调整 `app/indexing/milvus_upsert.py` 统一依赖 `DocumentChunk`。
- 涉及文件：
  - `app/models/document.py`
  - `app/indexing/loaders.py`
  - `app/indexing/splitter.py`
  - `app/indexing/milvus_upsert.py`
- 当前结果：
  - 在线查询流与离线索引流都具备明确的数据结构承载位置。
  - `schemas` 负责 API 边界，`models` 负责内部对象，`indexing / retrieval / generation` 负责处理逻辑。
- 验证方式：
  - `python -m py_compile app/models/document.py app/indexing/loaders.py app/indexing/splitter.py app/indexing/milvus_upsert.py`
  - `python scripts/reindex.py --help`
- 下一步：
  - 后续按需要扩展更细粒度的索引元数据模型。

## Day 4

### [P1-3] 增加最小管理观测接口，作为 RAG 下一阶段切入口

- 时间：2026-05-05
- 目标：在继续构建 RAG 主链路前，先补齐最小观测能力，明确 FAQ、Milvus、集合数据状态，避免后续开发过程“代码写了但不知道是否真的生效”。
- 变更内容：
  - 新增 `GET /admin/status`，统一暴露应用、FAQ、Milvus 的运行状态。
  - 新增 `GET /admin/milvus/sample`，用于抽样查看 Milvus 中的文档内容。
  - 为 `MysqlFAQRetriever` 增加 `health_status()`，返回 MySQL 连通性、FAQ 表存在性和 FAQ 数量。
  - 为 `MilvusRetriever` 增加 `health_status()`，返回 collection 状态和文档数量。
  - 为 `MilvusRetriever` 增加 `sample_documents()`，支持抽样查看当前集合中的 `id/text/source`。
  - 在 `app/main.py` 中挂载 `admin_router`。
- 涉及文件：
  - `app/main.py`
  - `app/api/routes_admin.py`
  - `app/retrieval/mysql_faq_retriever.py`
  - `app/retrieval/milvus_retriever.py`
- 当前结果：
  - `/admin/status` 已可返回当前系统关键状态。
  - FAQ 链路状态明确：MySQL 正常、FAQ 表存在、FAQ 数量为 `6`。
  - Milvus 链路状态明确：`rag_docs` collection 已存在，但 `row_count = 0`，当前还没有正式文档入库。
  - 这说明 FAQ 已经跑通，但最小 RAG 主链路还卡在“知识库数据尚未完成入库”这一层。
- 当前状态快照：
  - `/admin/status` 返回：
    ```json
    {
      "app_name": "rag-project",
      "app_env": "dev",
      "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
      "mysql": {
        "ok": true,
        "host": "127.0.0.1",
        "port": 3307,
        "database": "rag",
        "table": "faq",
        "table_exists": true,
        "faq_count": 6
      },
      "milvus": {
        "ok": true,
        "host": "127.0.0.1",
        "port": 19530,
        "collection": "rag_docs",
        "collection_exists": true,
        "stats": {
          "row_count": 0
        },
        "doc_count": 0
      }
    }
    ```
- 验证方式：
  - 请求 `GET /admin/status`
  - 请求 `GET /admin/milvus/sample`
  - 检查返回中的 `faq_count`、`collection_exists`、`row_count`
- 下一步：
  - 准备最小测试文档并执行一次 `python scripts/reindex.py <input_path> --drop-old`
  - 先把 Milvus 中的 `row_count` 从 `0` 推进到“大于 0”
  - 然后再继续验证 `/query` 的向量检索链路

### [P1-4] 打通最小 RAG 闭环：本地 embedding 降级 + 种子数据入库 + 查询降级返回

- 时间：2026-05-05
- 目标：在不依赖外部模型下载、也不依赖真实 LLM 联网可用的前提下，先把最小 RAG 闭环打通。
- 变更内容：
  - 重写 `EmbeddingWorker`，增加本地降级 embedding：
    - 优先尝试本地缓存的 `SentenceTransformer`
    - 若本地模型不可用，则自动退化为纯本地哈希向量
  - 将 `SentenceTransformer` 调整为 `local_files_only=True`，避免请求时卡在 HuggingFace 下载重试。
  - 调整 `HybridRetriever`，对 query embedding 失败增加兜底保护，避免直接抛异常。
  - 修复 `MilvusUpserter`，在写入后补 `flush`，保证 `row_count` 能正确反映入库数量。
  - 新增 `data/seed/demo_knowledge.jsonl`，提供最小测试知识库数据。
  - 重写 `LLMClient`：
    - 当未配置可用 LLM 时，直接返回检索片段
    - 当 LLM 调用失败时，不再返回 500，而是降级返回检索片段
- 涉及文件：
  - `app/indexing/embedding_worker.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/indexing/milvus_upsert.py`
  - `app/generation/llm_client.py`
  - `data/seed/demo_knowledge.jsonl`
- 当前结果：
  - 已成功执行 `python scripts/reindex.py data/seed --drop-old`
  - 种子知识库成功写入 Milvus
  - `rag_docs` 当前 `row_count = 5`
  - 非 FAQ 问题已能走到 Milvus 检索
  - 即使 OpenAI 调用失败，`/query` 也会以 200 正常返回检索片段，不再直接报 500
- 验证方式：
  - `python scripts/reindex.py data/seed --drop-old`
  - 检查 `GET /admin/status` 中 `milvus.stats.row_count == 5`
  - 检查 `GET /admin/milvus/sample`
  - 使用非 FAQ 问题请求 `/query`，确认返回 `source = "rag"` 且带 `retrieved_docs`
- 验证结果：
  - 重建输出：
    - `加载文档数: 5`
    - `切分后 chunk 数: 5`
    - `已写入 Milvus chunk 数: 5`
  - Milvus 状态：
    - `collection_exists = true`
    - `row_count = 5`
    - `doc_count = 5`
  - `/query` 非 FAQ 验证：
    - 请求：`RAG为什么要先检索再生成答案`
    - 返回：HTTP `200`
    - 路由：`rag`
    - 结果：成功返回检索片段 fallback
- 下一步：
  - 用真实业务文档替换 `data/seed/demo_knowledge.jsonl`
  - 再做一次正式 reindex
  - 然后开始优化 FAQ 路由规则和检索效果

```

## File: requirements.txt

- Extension: .txt
- Language: plaintext
- Size: 262 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-29 19:27:06

### Code

```plaintext
﻿# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.30.6
prometheus-client==0.20.0

# Data Validation
pydantic==2.9.0
pydantic-settings==2.5.0

# Config
pyyaml==6.0.2

# Logging
structlog==24.4.0

PyMySQL
pymilvus
numpy

openai
httpx
sentence-transformers

```

## File: roadmap.md

- Extension: .md
- Language: markdown
- Size: 2391 bytes
- Created: 2026-04-29 23:14:31
- Modified: 2026-04-29 23:14:31

### Code

```markdown
rag_project/
├─ app/
│    ├─ main.py  ✅应用入口与装配层    
      初始化日志；注册中间件（请求日志、指标采集）；注册全局异常处理；挂载 /metrics；提供 /health 健康检查。
│    ├─ api/  
│    │  ├─ routes_query.py
│    │  ├─ routes_admin.py
│    │  └─ schemas.py

│    ├─ core/    ✅
│    │  ├─ config.py    #统一配置源
│    │  ├─ logger.py    #统一日志格式与输出通道
         通过 RequestIdFilter 给日志补 request_id；配置 console + file 双输出；格式统一；可接管 uvicorn 日志写入同一文件。
│    │  └─ metrics.py   #指标定义层

│    ├─ middleware/  ✅
│    │  ├─ request_context.py
│    │  ├─ request_logger.py    #请求日志中间件
│    │  └─ metrics_middleware.py    #请求指标中间件

│    ├─ handlers/   ✅
│    │  └─ error_handler.py     #统一异常出口

│    ├─ models/
│    │  ├─ document.py
│    │  ├─ query.py
│    │  └─ response.py

│    ├─ router/
│    │  ├─ intent_router.py
│    │  └─ threshold_policy.py

│    ├─ retrieval/
│    │  ├─ mysql_faq_retriever.py
│    │  ├─ bm25_retriever.py
│    │  ├─ milvus_retriever.py
│    │  ├─ hybrid_retriever.py
│    │  └─ reranker.py

│    ├─ generation/
│    │  ├─ prompt_builder.py
│    │  ├─ llm_client.py
│    │  └─ answer_postprocess.py

│    ├─ indexing/
│    │  ├─ loaders.py
│    │  ├─ splitter.py
│    │  ├─ embedding_worker.py
│    │  └─ milvus_upsert.py

│    ├─ cache/
│    │  ├─ redis_cache.py
│    │  └─ cache_keys.py

│    ├─ eval/
│    │  ├─ dataset.py
│    │  ├─ offline_eval.py
│    │  └─ online_eval.py

│    └─ tests/
│       ├─ test_api.py
│       ├─ test_router.py
│       ├─ test_retrieval.py
│       └─ test_generation.py

├─ scripts/
│  ├─ reindex.py
│  ├─ warmup_cache.py
│  └─ replay_logs.py

├─ configs/
│  ├─ config.dev.yaml
│  ├─ config.prod.yaml
│  └─ prompts.yaml

├─ requirements.txt

└─ README.md

```

## File: test_milvus.py

- Extension: .py
- Language: python
- Size: 3498 bytes
- Created: 2026-04-29 11:51:44
- Modified: 2026-04-29 11:52:27

### Code

```python
#!/usr/bin/env python3
"""
Milvus服务健康性测试脚本
测试Milvus连接、集合创建、文档插入和向量搜索功能
"""

import sys
import time
from pymilvus import MilvusClient, DataType
import numpy as np

def test_milvus_health():
    """测试Milvus服务健康性"""
    print("🔍 开始测试Milvus服务健康性...")

    try:
        # 连接Milvus
        client = MilvusClient(uri="http://127.0.0.1:19530")
        print("✅ 成功连接到Milvus")

        # 测试集合操作
        collection_name = "test_collection"

        # 删除已存在的测试集合
        if client.has_collection(collection_name):
            client.drop_collection(collection_name)
            print(f"🗑️ 删除已存在的测试集合: {collection_name}")

        # 创建测试集合
        schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=100, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=768)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=2000)

        index_params = client.prepare_index_params()
        index_params.add_index(field_name="vector", index_type="FLAT", metric_type="COSINE")

        client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params
        )
        print(f"✅ 成功创建测试集合: {collection_name}")

        # 插入测试数据
        test_docs = [
            {
                "id": "doc1",
                "vector": np.random.rand(768).tolist(),
                "text": "这是一个测试文档，关于人工智能和机器学习。"
            },
            {
                "id": "doc2",
                "vector": np.random.rand(768).tolist(),
                "text": "另一个测试文档，讨论自然语言处理技术。"
            },
            {
                "id": "doc3",
                "vector": np.random.rand(768).tolist(),
                "text": "第三个测试文档，涉及向量数据库和检索系统。"
            }
        ]

        client.insert(collection_name=collection_name, data=test_docs)
        print(f"✅ 成功插入 {len(test_docs)} 条测试文档")

        # 等待索引构建
        time.sleep(2)

        # 测试向量搜索
        query_vector = np.random.rand(768).tolist()
        search_results = client.search(
            collection_name=collection_name,
            data=[query_vector],
            anns_field="vector",
            search_params={"metric_type": "COSINE", "params": {}},
            limit=3,
            output_fields=["text"]
        )

        print(f"✅ 向量搜索成功，返回 {len(search_results[0])} 条结果")
        for i, hit in enumerate(search_results[0]):
            print(f"  结果{i+1}: ID={hit['id']}, 相似度={hit['distance']:.4f}")

        # 清理测试集合
        client.drop_collection(collection_name)
        print(f"🧹 清理测试集合: {collection_name}")

        print("\n🎉 Milvus服务健康性测试全部通过！")
        return True

    except Exception as e:
        print(f"❌ Milvus测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_milvus_health()
    sys.exit(0 if success else 1)
```

## File: test_sql.py

- Extension: .py
- Language: python
- Size: 3474 bytes
- Created: 2026-04-28 22:36:51
- Modified: 2026-05-05 15:09:23

### Code

```python
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

```

## File: verify_milvus_collection_p0.py

- Extension: .py
- Language: python
- Size: 3037 bytes
- Created: 2026-04-29 23:27:29
- Modified: 2026-05-05 15:09:23

### Code

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pymilvus import MilvusClient  # noqa: E402
from app.core.config import settings  # noqa: E402

SUSPECT_GARBLED_PATTERNS = [
    "浣", "鎴", "绯", "鍚", "妫", "璇", "鐨", "銆", "锛", "锟", "�"
]


def has_garbled_text(text: str) -> bool:
    if not text:
        return False
    return any(token in text for token in SUSPECT_GARBLED_PATTERNS)


def short_text(text: str, limit: int = 160) -> str:
    text = (text or "").replace("\n", "\\n")
    return text if len(text) <= limit else text[:limit] + "..."


def main():
    print("=" * 80)
    print("P0-3 Milvus 集合核验")
    print("=" * 80)

    client = MilvusClient(
        uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
        user=settings.milvus_user or None,
        password=settings.milvus_password or None,
    )

    collection_name = settings.milvus_collection
    print(f"目标集合: {collection_name}")

    exists = client.has_collection(collection_name)
    print(f"集合存在: {exists}")

    if not exists:
        print("结论: 业务集合还没准备好，当前 RAG 检索不成立。")
        return

    try:
        stats = client.get_collection_stats(collection_name=collection_name)
        print(f"集合统计: {stats}")
    except Exception as e:
        print(f"读取集合统计失败: {e}")

    print("\n尝试抽样查询 text 字段...")
    try:
        rows = client.query(
            collection_name=collection_name,
            filter="id != ''",
            output_fields=["id", "text"],
            limit=10,
        )
    except Exception as e:
        print(f"抽样查询失败: {e}")
        return

    if not rows:
        print("集合存在，但没有可读样本，基本等于没数据。")
        return

    normal_count = 0
    garbled_count = 0
    empty_count = 0

    for idx, row in enumerate(rows, start=1):
        doc_id = row.get("id", "")
        text = row.get("text", "")

        if not text:
            empty_count += 1
            flag = "空文本"
        elif has_garbled_text(text):
            garbled_count += 1
            flag = "疑似乱码"
        else:
            normal_count += 1
            flag = "正常"

        print(f"[{idx}] id={doc_id} | {flag} | text={short_text(text)}")

    print("\n统计:")
    print(f"正常样本: {normal_count}")
    print(f"疑似乱码样本: {garbled_count}")
    print(f"空文本样本: {empty_count}")

    if garbled_count > 0:
        print("结论: Milvus 内部 text 字段存在乱码风险。")
    elif normal_count > 0:
        print("结论: Milvus 至少有部分文本样本是正常的。")
    else:
        print("结论: 当前集合数据质量可疑。")


if __name__ == "__main__":
    main()

```

## File: verify_mysql_faq_p0.py

- Extension: .py
- Language: python
- Size: 2655 bytes
- Created: 2026-04-29 23:27:29
- Modified: 2026-05-05 15:09:23

### Code

```python
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

```

## File: 项目问题清单.md

- Extension: .md
- Language: markdown
- Size: 5129 bytes
- Created: 2026-05-05 15:49:53
- Modified: 2026-05-05 15:49:53

### Code

```markdown
# 项目问题清单

## 当前结论

当前项目已经有基础骨架，但本质上还是一个 **最小可用原型**：

- 在线问答主链路已具备雏形
- FAQ / 向量检索 / LLM 生成已经串起来了
- 但还不是完整的 Hybrid RAG
- 当前最重要目标不是“继续加功能”，而是 **先把整体稳定跑通**

---

## P0：必须先解决的问题

### 1. Embedding 模型在线加载不稳定

现象：

- `EmbeddingWorker` 在请求时动态加载 `SentenceTransformer`
- 如果本地没有缓存好，会在查询时触发模型下载
- 现有日志里已经出现加载失败，导致 `/query` 直接报错

影响：

- 主链路不稳定
- 用户第一次调用就可能失败

建议：

- 先保证 embedding 模型本地可用
- 不要把“首次下载模型”放在在线请求里
- 最好改成“启动前准备好”或“reindex 前准备好”

---

### 2. `HybridRetriever` 名字和真实能力不一致

现状：

- 当前只有 Milvus 向量检索
- 没有 BM25
- 没有 RRF
- 没有 rerank

影响：

- 容易误判项目完成度
- 后续排查问题时会混淆真实瓶颈

建议：

- 短期先承认事实：当前就是“向量检索版 RAG”
- 等主链路稳定后，再逐步补 BM25 / RRF / rerank

---

### 3. README 与代码真实状态不一致

现状：

- README 写了 Redis
- README 写了已实现 RRF 混合重排
- 但代码里没有对应实现

影响：

- 容易误导自己和后续维护者

建议：

- 后续统一文档口径
- 文档只写“已经落地”的能力

---

### 4. FAQ 检索能力过弱

现状：

- MySQL FAQ 走的是 `question = %s` 精确匹配

影响：

- 只有完全一样的问题才能命中
- 稍微换种问法就失败

建议：

- 短期先保留精确匹配，先保证能跑
- 跑通后再升级成模糊匹配 / 全文检索 / FAQ embedding 检索

---

### 5. 在线查询承担了过多初始化责任

现状：

- 查询时才初始化 embedding 模型
- 查询时才初始化 MilvusRetriever
- MilvusRetriever 内部还会检查/创建 collection

影响：

- 首次请求慢
- 请求期行为不稳定
- 排查困难

建议：

- 在线查询只做“查询”
- 初始化、建 collection、建索引，尽量放到离线阶段

---

## P1：跑通后优先优化的问题

### 6. IntentRouter 规则过于粗糙

现状：

- 仅按 `query` 长度判断 FAQ / RAG

影响：

- 路由误判概率高

建议：

- 先保持简单规则
- 后续再增加关键词规则、置信度规则，或者小模型分类

---

### 7. 文本切分过于原始

现状：

- 当前是固定长度字符切分

影响：

- 容易切断语义
- 影响召回质量

建议：

- 跑通后再升级为按段落 / 标题 / 语义边界切分

---

### 8. 检索结果元数据不足

现状：

- 当前只保留 `doc_id / score / snippet`

影响：

- citation 弱
- 不利于定位来源

建议：

- 后续补 `source / title / section / page / chunk_index`

---

### 9. MySQL 每次请求新建连接

现状：

- FAQ 查询每次都直接 `pymysql.connect`

影响：

- 延迟增加
- 并发能力差

建议：

- 跑通后再改连接池

---

### 10. generation 层职责还没拆干净

现状：

- `prompt_builder.py` 还是空壳
- `answer_postprocess.py` 还是占位
- `LLMClient` 同时承担 prompt / 调用 / fallback

影响：

- 不利于后续替换模型和调 prompt

建议：

- 后续拆成：
  - prompt 构造
  - LLM 调用
  - 回答后处理

---

## P2：后续增强项

### 11. 增加 BM25 检索

目标：

- 补上关键词召回

---

### 12. 增加 RRF 融合

目标：

- 融合 FAQ / BM25 / 向量结果

---

### 13. 增加 rerank

目标：

- 对 topN 候选做二次排序

---

### 14. 增加缓存层

目标：

- 如果后续确实需要 Redis，再引入
- 不建议现在为了“架构完整”提前上 Redis

---

### 15. 增加管理与运维能力

目标：

- reindex 管理入口
- collection 状态检查
- FAQ 数据管理

---

## 建议推进顺序

### 阶段 1：先把整体跑通

目标：

- `/health` 正常
- `/query` 至少能稳定返回
- FAQ 可查
- Milvus 可查
- LLM 未配置时也能 fallback

先做：

1. 固定 embedding 模型加载方式
2. 确保 MySQL / Milvus / FastAPI 配置正确
3. 准备一小批真实测试文档
4. 跑通 `scripts/reindex.py`
5. 跑通 `/query`

---

### 阶段 2：把链路做稳定

目标：

- 首次请求不炸
- 检索失败可控
- 错误更容易定位

再做：

1. 减少在线初始化
2. 补更清晰的启动检查
3. 清理 README 与真实状态不一致问题

---

### 阶段 3：开始做效果优化

目标：

- 提升召回质量
- 提升回答质量

再做：

1. FAQ 检索增强
2. 文本切分优化
3. 补元数据
4. prompt_builder 落地

---

### 阶段 4：再升级成真正的 Hybrid RAG

目标：

- 关键词召回 + 向量召回 + 融合重排

最后做：

1. BM25
2. RRF
3. rerank
4. 缓存层

---

## 最终原则

先做：

- 能跑
- 稳定
- 可排查

再做：

- 更准
- 更快
- 更完整

不要一开始就把系统做复杂。

```

## File: app\main.py

- Extension: .py
- Language: python
- Size: 1400 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-05-05 15:56:32

### Code

```python
from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.logger import setup_logger

from app.handlers.error_handler import register_exception_handlers
from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.request_logger import RequestLoggerMiddleware
from app.api.routes_admin import router as admin_router
from app.api.routes_query import router as query_router

# 注册了哪些中间件？挂了哪些路由？异常处理在哪接入？

def create_app() -> FastAPI:

    setup_logger()

    app = FastAPI(title=settings.app_name,debug=settings.debug)
    @app.middleware("http")
    async def ensure_utf8_json(request, call_next):
        resp = await call_next(request)
        ct = resp.headers.get("content-type", "")
        if ct.startswith("application/json") and "charset" not in ct:
            resp.headers["content-type"] = "application/json; charset=utf-8"
        return resp

    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(MetricsMiddleware)

    register_exception_handlers(app)
    app.mount("/metrics", make_asgi_app())

    @app.get("/health")
    def health():
        return {"status": "ok", "env": settings.app_env}

    return app

app = create_app()
app.include_router(admin_router)
app.include_router(query_router)

```

## File: app\__init__.py

- Extension: .py
- Language: python
- Size: 0 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

```

## File: app\api\routes_admin.py

- Extension: .py
- Language: python
- Size: 1174 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-05-05 15:56:24

### Code

```python
from fastapi import APIRouter

from app.core.config import settings
from app.retrieval.milvus_retriever import MilvusRetriever
from app.retrieval.mysql_faq_retriever import MysqlFAQRetriever

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status")
def admin_status():
    result = {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "embedding_model": settings.embedding_model,
        "mysql": {"ok": False},
        "milvus": {"ok": False},
    }

    try:
        result["mysql"] = MysqlFAQRetriever().health_status()
    except Exception as e:
        result["mysql"] = {
            "ok": False,
            "error": str(e),
        }

    try:
        result["milvus"] = MilvusRetriever().health_status()
    except Exception as e:
        result["milvus"] = {
            "ok": False,
            "error": str(e),
        }

    return result


@router.get("/milvus/sample")
def milvus_sample(limit: int = 5):
    retriever = MilvusRetriever()
    return {
        "collection": settings.milvus_collection,
        "limit": limit,
        "items": retriever.sample_documents(limit=max(1, min(limit, 20))),
    }

```

## File: app\api\routes_query.py

- Extension: .py
- Language: python
- Size: 1981 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-05-05 15:10:53

### Code

```python
from fastapi import APIRouter, Request

from app.api.schemas import QueryRequest, QueryResponse, DocItem
from app.router.intent_router import IntentRouter
from app.models.query import RetrievalStrategy
from app.retrieval.hybrid_retriever import HybridRetriever
from app.generation.llm_client import LLMClient
from app.retrieval.mysql_faq_retriever import MysqlFAQRetriever
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["query"])

intent_router = IntentRouter()
faq_retriever = MysqlFAQRetriever()
llm = LLMClient()

retriever = HybridRetriever()


@router.post("/query", response_model=QueryResponse)
def query_api(req: QueryRequest, request: Request):
    
    trace_id = getattr(request.state, "request_id", "-")
    decision = intent_router.route(req.query)

    logger.info(f"[{trace_id}] Query: {req.query} | Route Strategy: {decision.strategy}")

    if decision.strategy == RetrievalStrategy.DIRECT_FAQ:
        faq_hit = faq_retriever.retrieve(req.query)
        if faq_hit:
            return QueryResponse(
                trace_id=trace_id,
                query=req.query,
                answer=faq_hit.answer,
                source="faq",
                route=decision.strategy.value,
                confidence=faq_hit.score,
                citations=[faq_hit.faq_id],
                retrieved_docs=[],
            )

    docs = retriever.retrieve(req.query, req.top_k)

    ans = llm.generator(req.query, docs)

    return QueryResponse(
        trace_id=trace_id,
        query=req.query,
        answer=ans.text,
        source="rag",
        route=RetrievalStrategy.RAG.value,
        confidence=decision.confidence,
        citations=ans.citations,
        retrieved_docs=[
            DocItem(
                doc_id=d.doc_id, 
                score=float(d.score), 
                snippet=d.snippet
            )for d in docs 
        ],
    )

```

## File: app\api\schemas.py

- Extension: .py
- Language: python
- Size: 525 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(3, ge=1, le=10)


class DocItem(BaseModel):
    doc_id: str
    score: float
    snippet: str


class QueryResponse(BaseModel):
    trace_id: str
    query: str
    answer: str
    source: str
    route: str
    confidence: float
    citations: list[str] = Field(default_factory=list)
    retrieved_docs: list[DocItem] = Field(default_factory=list)

```

## File: app\api\__init__.py

- Extension: .py
- Language: python
- Size: 0 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

```

## File: app\core\config.py

- Extension: .py
- Language: python
- Size: 2121 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-05-05 15:09:23

### Code

```python
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = Field(default="rag-project", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=False, alias="DEBUG")

    mysql_host: str = Field(..., alias="MYSQL_HOST")
    mysql_port: int = Field(..., alias="MYSQL_PORT")
    mysql_user: str = Field(..., alias="MYSQL_USER")
    mysql_password: str = Field(..., alias="MYSQL_PASSWORD")
    mysql_database: str = Field(..., alias="MYSQL_DATABASE")
    mysql_faq_table: str = Field(default="faq", alias="MYSQL_FAQ_TABLE")

    milvus_host: str = Field(default="127.0.0.1", alias="MILVUS_HOST")
    milvus_port: int = Field(default=19530, alias="MILVUS_PORT")
    milvus_collection: str = Field(default="rag_docs", alias="MILVUS_COLLECTION")
    milvus_user: str = Field(default="", alias="MILVUS_USER")
    milvus_password: str = Field(default="", alias="MILVUS_PASSWORD")

    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        alias="EMBEDDING_MODEL",
    )
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")
    chunk_size: int = Field(default=500, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=80, alias="CHUNK_OVERLAP")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_max_output_tokens: int = Field(default=800, alias="OPENAI_MAX_OUTPUT_TOKENS")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


settings = Settings()

```

## File: app\core\logger.py

- Extension: .py
- Language: python
- Size: 2057 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
import logging
from logging.config import dictConfig
from pathlib import Path
from app.core.config import settings


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def setup_logger() -> None:
    log_dir = getattr(settings, "log_dir", "logs")
    log_file = getattr(settings, "log_file", "app.log")
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_id_filter": {"()": RequestIdFilter}
            },
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(request_id)s | %(name)s | %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "filters": ["request_id_filter"],
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": str(Path(log_dir) / log_file),
                    "maxBytes": 10 * 1024 * 1024,
                    "backupCount": 5,
                    "formatter": "standard",
                    "filters": ["request_id_filter"],
                    "encoding": "utf-8",
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": settings.log_level.upper(),
            },
        }
    )

    # 让 uvicorn 日志走 root，统一进入文件
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

```

## File: app\core\metrics.py

- Extension: .py
- Language: python
- Size: 673 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from prometheus_client import Counter,Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "HTTP 请求总数",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP 请求耗时(秒)",
    ["method", "path"],
)

def record_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        path=path,
        status_code=str(status_code),
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method,
        path=path,
    ).observe(duration_seconds)
```

## File: app\generation\answer_postprocess.py

- Extension: .py
- Language: python
- Size: 118 bytes
- Created: 2026-04-29 22:13:32
- Modified: 2026-04-29 22:23:52

### Code

```python
"""
  - 清洗输出文本
  - 空答案处理
  - fallback
  - citation 整理
  - 转成 GeneratedAnswer
"""

```

## File: app\generation\llm_client.py

- Extension: .py
- Language: python
- Size: 2619 bytes
- Created: 2026-05-05 16:15:47
- Modified: 2026-05-05 16:15:47

### Code

```python
from typing import List

from openai import OpenAI

from app.core.config import settings
from app.core.logger import get_logger
from app.models.response import GeneratedAnswer, RetrievedDoc

logger = get_logger(__name__)


class LLMClient:
    def __init__(self):
        self.api_key = settings.openai_api_key.strip()
        self.base_url = settings.openai_base_url.strip()
        self.model = settings.openai_model
        self.max_output_tokens = settings.openai_max_output_tokens
        self.client = None

        if self.api_key:
            kwargs = {"api_key": self.api_key}
            if self.base_url and (
                self.base_url.startswith("http://") or self.base_url.startswith("https://")
            ):
                kwargs["base_url"] = self.base_url
            self.client = OpenAI(**kwargs)

    def generator(self, query: str, docs: List[RetrievedDoc]) -> GeneratedAnswer:
        citations = [d.doc_id for d in docs]
        if not docs:
            return GeneratedAnswer(
                text="未检索到相关资料，暂时无法基于知识库回答这个问题。",
                citations=citations,
                model="no-context",
            )

        context = "\n\n".join([f"[文档 {doc.doc_id}]\n{doc.snippet}" for doc in docs])

        if not self.client:
            return GeneratedAnswer(
                text="未配置可用的 LLM，当前返回检索到的资料片段：\n\n" + context,
                citations=citations,
                model="fallback-no-openai",
            )

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=(
                    "你是一个 RAG 问答助手。"
                    "只能基于提供的检索资料回答。"
                    "如果资料不足，就明确说不知道，不要编造。"
                    "回答尽量简洁直接。"
                ),
                input=f"用户问题：{query}\n\n检索资料：\n{context}",
                max_output_tokens=self.max_output_tokens,
            )
            return GeneratedAnswer(
                text=response.output_text.strip(),
                citations=citations,
                model=self.model,
            )
        except Exception as e:
            logger.warning(f"LLM generation failed, fallback to retrieved docs: {e}")
            return GeneratedAnswer(
                text="LLM 调用失败，当前返回检索到的资料片段：\n\n" + context,
                citations=citations,
                model="fallback-llm-error",
            )

```

## File: app\generation\prompt_builder.py

- Extension: .py
- Language: python
- Size: 342 bytes
- Created: 2026-04-29 22:13:26
- Modified: 2026-04-30 16:53:33

### Code

```python
"""
  职责应该是：

  - 输入：
      - query
      - retrieved_docs
  - 输出：
      - system / instructions
      - user input / context prompt
"""

from __future__ import annotations
from app.models.response import RetrievedDoc


def build_prompt(query: str, docs: list[RetrievedDoc]) -> tuple[str, str]:
    ...
```

## File: app\handlers\error_handler.py

- Extension: .py
- Language: python
- Size: 1424 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.logger import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", "-")
        logger.warning(
            "http_exception status=%s detail=%s",
            exc.status_code,
            exc.detail,
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": str(exc.detail),
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "-")
        logger.exception(
            "unhandled_exception: %s",
            str(exc),
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "Internal Server Error",
                "request_id": request_id,
            },
        )

```

## File: app\indexing\embedding_worker.py

- Extension: .py
- Language: python
- Size: 3119 bytes
- Created: 2026-05-05 16:07:57
- Modified: 2026-05-05 16:13:43

### Code

```python
from __future__ import annotations

import hashlib
import math

from app.core.config import settings

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


class EmbeddingWorker:
    _model_cache: dict[str, object] = {}
    _model_load_failed: set[str] = set()

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self.dimension = settings.embedding_dimension

    @property
    def model(self):
        if self.model_name in self._model_cache:
            return self._model_cache[self.model_name]

        if self.model_name in self._model_load_failed:
            return None

        if SentenceTransformer is None:
            self._model_load_failed.add(self.model_name)
            return None

        try:
            model = SentenceTransformer(self.model_name, local_files_only=True)
            self._model_cache[self.model_name] = model
            return model
        except Exception:
            self._model_load_failed.add(self.model_name)
            return None

    def embed_query(self, query: str) -> list[float]:
        return self._embed_one(query)

    def embed_texts(self, texts: list[str], batch_size: int | None = None) -> list[list[float]]:
        if not texts:
            return []

        model = self.model
        if model is not None:
            vectors = model.encode(
                texts,
                batch_size=batch_size or settings.embedding_batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return vectors.tolist()

        return [self._fallback_embed(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        model = self.model
        if model is not None:
            vector = model.encode(text, normalize_embeddings=True)
            return vector.tolist()
        return self._fallback_embed(text)

    def _fallback_embed(self, text: str) -> list[float]:
        text = (text or "").strip().lower()
        if not text:
            return [0.0] * self.dimension

        vector = [0.0] * self.dimension
        units = self._split_units(text)

        for idx, unit in enumerate(units):
            bucket = self._hash_to_bucket(unit)
            weight = 1.0 + min(idx, 8) * 0.03
            vector[bucket] += weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]

    def _split_units(self, text: str) -> list[str]:
        units: list[str] = []
        for token in text.split():
            units.append(token)

        chars = [char for char in text if not char.isspace()]
        units.extend(chars)

        for i in range(len(chars) - 1):
            units.append(chars[i] + chars[i + 1])

        return units or [text]

    def _hash_to_bucket(self, text: str) -> int:
        digest = hashlib.md5(text.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % self.dimension

```

## File: app\indexing\loaders.py

- Extension: .py
- Language: python
- Size: 1844 bytes
- Created: 2026-04-29 19:27:06
- Modified: 2026-05-05 15:09:23

### Code

```python
from pathlib import Path
import json

from app.models.document import SourceDocument


SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".markdown"}


class DocumentLoader:
    def load(self, input_path: str) -> list[SourceDocument]:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"输入路径不存在: {input_path}")

        if path.is_file():
            return self._load_file(path)

        documents: list[SourceDocument] = []
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_TEXT_SUFFIXES | {".jsonl"}:
                documents.extend(self._load_file(file_path))
        return documents

    def _load_file(self, file_path: Path) -> list[SourceDocument]:
        if file_path.suffix.lower() == ".jsonl":
            return self._load_jsonl(file_path)

        text = file_path.read_text(encoding="utf-8")
        return [
            SourceDocument(
                doc_id=file_path.stem,
                text=text,
                source=str(file_path),
            )
        ]

    def _load_jsonl(self, file_path: Path) -> list[SourceDocument]:
        documents: list[SourceDocument] = []
        with file_path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                text = (record.get("text") or "").strip()
                if not text:
                    continue
                doc_id = str(record.get("id") or f"{file_path.stem}-{idx}")
                source = str(record.get("source") or file_path)
                documents.append(SourceDocument(doc_id=doc_id, text=text, source=source))
        return documents

```

## File: app\indexing\milvus_upsert.py

- Extension: .py
- Language: python
- Size: 2582 bytes
- Created: 2026-05-05 16:11:42
- Modified: 2026-05-05 16:11:42

### Code

```python
from pymilvus import DataType, MilvusClient

from app.core.config import settings
from app.core.logger import get_logger
from app.models.document import DocumentChunk

logger = get_logger(__name__)


class MilvusUpserter:
    def __init__(self):
        self.client = MilvusClient(
            uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
            user=settings.milvus_user or None,
            password=settings.milvus_password or None,
        )
        self.collection_name = settings.milvus_collection

    def ensure_collection(self, drop_old: bool = False) -> None:
        if drop_old and self.client.has_collection(self.collection_name):
            self.client.drop_collection(self.collection_name)
            logger.info(f"Dropped Milvus collection: {self.collection_name}")

        if self.client.has_collection(self.collection_name):
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=100, is_primary=True)
        schema.add_field(
            field_name="vector",
            datatype=DataType.FLOAT_VECTOR,
            dim=settings.embedding_dimension,
        )
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=4000)
        schema.add_field(field_name="source", datatype=DataType.VARCHAR, max_length=500)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="FLAT",
            metric_type="COSINE",
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        logger.info(f"Created Milvus collection: {self.collection_name}")

    def upsert_chunks(self, chunks: list[DocumentChunk], vectors: list[list[float]]) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("chunks 与 vectors 数量不一致")

        if not chunks:
            return 0

        rows = [
            {
                "id": chunk.chunk_id,
                "vector": vector,
                "text": chunk.text,
                "source": chunk.source,
            }
            for chunk, vector in zip(chunks, vectors)
        ]
        self.client.insert(collection_name=self.collection_name, data=rows)
        self.client.flush(collection_name=self.collection_name)
        logger.info(f"Inserted {len(rows)} chunks into Milvus")
        return len(rows)

```

## File: app\indexing\splitter.py

- Extension: .py
- Language: python
- Size: 1591 bytes
- Created: 2026-04-29 19:27:06
- Modified: 2026-05-05 15:09:23

### Code

```python
from app.models.document import DocumentChunk, SourceDocument


class TextSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能小于 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents: list[SourceDocument]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for doc in documents:
            chunks.extend(self._split_one(doc))
        return chunks

    def _split_one(self, document: SourceDocument) -> list[DocumentChunk]:
        text = document.text.strip()
        if not text:
            return []

        chunks: list[DocumentChunk] = []
        start = 0
        index = 0
        step = self.chunk_size - self.chunk_overlap

        while start < len(text):
            end = min(len(text), start + self.chunk_size)
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document.doc_id}#chunk-{index}",
                        text=chunk_text,
                        source=document.source,
                    )
                )
                index += 1
            if end >= len(text):
                break
            start += step

        return chunks

```

## File: app\indexing\__init__.py

- Extension: .py
- Language: python
- Size: 35 bytes
- Created: 2026-04-29 19:27:06
- Modified: 2026-05-05 15:09:23

### Code

```python
"""索引链路相关模块。"""

```

## File: app\middleware\metrics_middleware.py

- Extension: .py
- Language: python
- Size: 634 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.metrics import record_http_request


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        record_http_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration,
        )
        return response

```

## File: app\middleware\request_logger.py

- Extension: .py
- Language: python
- Size: 933 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logger import get_logger

logger = get_logger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={"request_id": request_id},
        )

        response.headers["X-Request-ID"] = request_id
        return response

```

## File: app\models\document.py

- Extension: .py
- Language: python
- Size: 441 bytes
- Created: 2026-04-29 20:36:51
- Modified: 2026-05-05 15:09:23

### Code

```python
from dataclasses import dataclass
"""
  #### 索引文档模型

  - SourceDocument
  - DocumentChunk
"""


@dataclass
class SourceDocument:
    """
    - title
    - metadata
    - tags
    - section
    - source_type
    """
    doc_id: str
    text: str
    source: str


@dataclass
class DocumentChunk:
    """
    - title
    - metadata
    - tags
    - section
    - source_type
    """
    chunk_id: str
    text: str
    source: str

```

## File: app\models\query.py

- Extension: .py
- Language: python
- Size: 919 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-29 21:24:18

### Code

```python
from dataclasses import dataclass
from enum import Enum

"""
  #### 查询决策模型

  - Intent
  - RetrievalStrategy
  - RouteDecision
"""



# TODO 将其升级为 Pydantic 的 BaseModel

class Intent(str,Enum): 
    FAQ = 'faq'                # FAQ: Frequently Asked Questions
    KNOWLEDGE = 'knowledge'

class RetrievalStrategy(str,Enum): #当你继承 Enum 时，Python 自动把你定义里的所有类属性（如 RAG）都转换成了一个对象（Instance）
    DIRECT_FAQ = "direct_faq"      #若不继承str，则输出: <enum 'MyEnum'> (它不是字符串，它是 MyEnum 这个枚举类的一个实例)
    RAG = "rag"

@dataclass  
class RouteDecision:    # if decision.confidence > 0.95: ...
    intent:Intent        # Python 的 “委托” (Delegation) 和 “混入” (Mixin)
    strategy:RetrievalStrategy
    confidence:float  
    direct_answer:str | None = None
```

## File: app\models\response.py

- Extension: .py
- Language: python
- Size: 613 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-29 21:24:29

### Code

```python
from dataclasses import dataclass

"""
  #### 查询结果模型

  - RetrievedDoc
  - GeneratedAnswer
"""

# TODO 将其升级为 Pydantic 的 BaseModel

@dataclass
class  RetrievedDoc:

    # TODO 后续扩充 metadata: dict 字段,把页码、章节、文件来源 URL 塞进去
    
    doc_id: str
    score: float
    snippet: str
    # matadata: json
     
@dataclass
class GeneratedAnswer:
    text: str
    citations: list[str]
    model: str # 不同模型间进行 A/B 测试或者平滑迁移时，这个字段能帮你追踪到：这条答案到底是哪个模型生成的。
```

## File: app\retrieval\bm25_retriever.py

- Extension: .py
- Language: python
- Size: 2 bytes
- Created: 2026-04-29 22:11:25
- Modified: 2026-05-05 15:09:23

### Code

```python


```

## File: app\retrieval\hybrid_retriever.py

- Extension: .py
- Language: python
- Size: 1523 bytes
- Created: 2026-05-05 16:08:44
- Modified: 2026-05-05 16:08:44

### Code

```python
from typing import List

from app.core.logger import get_logger
from app.indexing.embedding_worker import EmbeddingWorker
from app.models.response import RetrievedDoc
from app.retrieval.milvus_retriever import MilvusRetriever

logger = get_logger(__name__)


class HybridRetriever:
    def __init__(self):
        self.embedder = EmbeddingWorker()
        self._milvus_retriever: MilvusRetriever | None = None

    def _get_milvus_retriever(self) -> MilvusRetriever | None:
        if self._milvus_retriever is not None:
            return self._milvus_retriever

        try:
            self._milvus_retriever = MilvusRetriever()
            return self._milvus_retriever
        except Exception as e:
            logger.warning(f"Milvus 初始化失败: {e}")
            return None

    def retrieve(self, query: str, top_k: int = 3) -> List[RetrievedDoc]:
        query = query.strip()
        if not query:
            return []

        milvus_retriever = self._get_milvus_retriever()
        if not milvus_retriever:
            return []

        try:
            query_vector = self.embedder.embed_query(query)
        except Exception as e:
            logger.error(f"Embedding query failed: {e}")
            return []

        logger.info(f"Searching Milvus for query: {query}")
        docs: List[RetrievedDoc] = milvus_retriever.search(query_vector, top_k)

        if not docs:
            logger.warning("No documents found in Milvus, returning empty results")
            return []

        return docs

```

## File: app\retrieval\milvus_retriever.py

- Extension: .py
- Language: python
- Size: 4300 bytes
- Created: 2026-05-05 15:56:12
- Modified: 2026-05-05 15:56:12

### Code

```python
from typing import List

from pymilvus import DataType, MilvusClient

from app.core.config import settings
from app.core.logger import get_logger
from app.models.response import RetrievedDoc

logger = get_logger(__name__)


class MilvusRetriever:
    def __init__(self):
        self.client = MilvusClient(
            uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
            user=settings.milvus_user or None,
            password=settings.milvus_password or None,
        )
        self.collection_name = settings.milvus_collection
        self._ensure_collection()

    def _ensure_collection(self):
        if self.client.has_collection(self.collection_name):
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=100, is_primary=True)
        schema.add_field(
            field_name="vector",
            datatype=DataType.FLOAT_VECTOR,
            dim=settings.embedding_dimension,
        )
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=4000)
        schema.add_field(field_name="source", datatype=DataType.VARCHAR, max_length=500)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="FLAT",
            metric_type="COSINE",
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        logger.info(f"Created Milvus collection: {self.collection_name}")

    def search(self, query_vector: List[float], top_k: int = 3) -> List[RetrievedDoc]:
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                anns_field="vector",
                search_params={"metric_type": "COSINE", "params": {}},
                limit=top_k,
                output_fields=["text"],
            )

            docs: list[RetrievedDoc] = []
            for hits in results:
                for hit in hits:
                    entity = hit.get("entity", {})
                    docs.append(
                        RetrievedDoc(
                            doc_id=str(hit["id"]),
                            score=float(hit["distance"]),
                            snippet=entity.get("text", ""),
                        )
                    )
            return docs
        except Exception as e:
            logger.error(f"Milvus search failed: {e}")
            return []

    def insert_documents(self, documents: List[dict]):
        try:
            self.client.insert(collection_name=self.collection_name, data=documents)
            logger.info(f"Inserted {len(documents)} documents to Milvus")
        except Exception as e:
            logger.error(f"Failed to insert documents: {e}")

    def health_status(self) -> dict:
        exists = self.client.has_collection(self.collection_name)
        info = {
            "ok": True,
            "host": settings.milvus_host,
            "port": settings.milvus_port,
            "collection": self.collection_name,
            "collection_exists": exists,
        }

        if not exists:
            info["doc_count"] = 0
            return info

        try:
            stats = self.client.get_collection_stats(collection_name=self.collection_name)
            info["stats"] = stats
            info["doc_count"] = int(stats.get("row_count", 0))
        except Exception as e:
            info["stats_error"] = str(e)
            info["doc_count"] = None

        return info

    def sample_documents(self, limit: int = 5) -> list[dict]:
        if not self.client.has_collection(self.collection_name):
            return []

        rows = self.client.query(
            collection_name=self.collection_name,
            filter="id != ''",
            output_fields=["id", "text", "source"],
            limit=limit,
        )
        return [
            {
                "id": row.get("id", ""),
                "text": row.get("text", ""),
                "source": row.get("source", ""),
            }
            for row in rows
        ]

```

## File: app\retrieval\mysql_faq_retriever.py

- Extension: .py
- Language: python
- Size: 3316 bytes
- Created: 2026-05-05 15:55:39
- Modified: 2026-05-05 15:55:39

### Code

```python
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

```

## File: app\router\intent_router.py

- Extension: .py
- Language: python
- Size: 684 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 16:04:34

### Code

```python
from app.models.query import Intent, RetrievalStrategy, RouteDecision
class IntentRouter:
    def route(self, query: str) -> RouteDecision:
        q = query.strip()
        # Day2 Step1: 这里只保留轻量路由判断，不再直接返回 FAQ 内容
        if len(q) <= 20:
            return RouteDecision(
                intent=Intent.FAQ,
                strategy=RetrievalStrategy.DIRECT_FAQ,
                confidence=0.80,
                direct_answer=None,
            )
        return RouteDecision(
            intent=Intent.KNOWLEDGE,
            strategy=RetrievalStrategy.RAG,
            confidence=0.60,
            direct_answer=None,
        )
```

## File: data\seed\demo_knowledge.jsonl

- Extension: .jsonl
- Language: unknown
- Size: 1540 bytes
- Created: 2026-05-05 16:09:00
- Modified: 2026-05-05 16:09:00

### Code

```unknown
{"id":"rag-intro","source":"seed/rag-intro","text":"RAG 是 Retrieval-Augmented Generation，即检索增强生成。它的基本流程是先根据用户问题从知识库中检索相关片段，再把检索结果交给大模型生成答案。这样可以降低模型幻觉，并让回答更贴近企业私有知识。"}
{"id":"faq-vs-rag","source":"seed/faq-vs-rag","text":"FAQ 更适合固定问题和固定答案，通常使用精确匹配、模糊匹配或规则命中。RAG 更适合开放问题，需要从文档中检索上下文后再生成回答。FAQ 和 RAG 可以组合：先查 FAQ，FAQ 未命中时再回退到 RAG。"}
{"id":"milvus-role","source":"seed/milvus-role","text":"Milvus 是向量数据库，适合存储文档切片的 embedding，并支持相似度检索。在一个最小 RAG 项目里，文档先被切分成 chunk，再经过 embedding 编码写入 Milvus，查询时再用 query embedding 去搜索最相关的 chunk。"}
{"id":"reindex-flow","source":"seed/reindex-flow","text":"最小离线索引流程通常包括四步：加载原始文档、文本切分、生成 embedding、写入向量库。只有完成这条 reindex 链路，在线查询阶段的向量检索才有真实数据可查。"}
{"id":"fallback-answer","source":"seed/fallback-answer","text":"如果系统没有配置真实大模型接口，最小可用做法是返回检索到的文档片段作为 fallback。这样虽然还没有自然语言生成能力，但可以先验证检索链路、召回质量和上下文组织是否正常。"}

```

## File: docker\mysql\init\001_init_faq.sql

- Extension: .sql
- Language: sql
- Size: 816 bytes
- Created: 2026-04-28 17:26:45
- Modified: 2026-04-29 17:58:19

### Code

```sql
﻿SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

USE rag;

CREATE TABLE IF NOT EXISTS faq (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    question VARCHAR(255) NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO faq (question, answer) VALUES
('你是谁', '我是你的 RAG 助手。'),
('系统健康吗', '系统当前健康。'),
('联系方式', '请通过项目仓库提交问题或建议。'),
('你能做什么', '我可以回答问题、提供信息，并结合检索结果生成答案。'),
('什么是RAG', 'RAG（Retrieval-Augmented Generation）是一种结合检索和生成的 AI 技术。'),
('如何使用', '直接输入问题，我会先检索相关信息，再给出回答。');

```

## File: scripts\reindex.py

- Extension: .py
- Language: python
- Size: 1829 bytes
- Created: 2026-04-29 19:27:06
- Modified: 2026-05-05 16:32:55

### Code

```python
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.indexing.embedding_worker import EmbeddingWorker
from app.indexing.loaders import DocumentLoader
from app.indexing.milvus_upsert import MilvusUpserter
from app.indexing.splitter import TextSplitter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="重建 Milvus 文档索引")
    parser.add_argument("input_path", help="输入文件或目录，支持 txt/md/jsonl")
    parser.add_argument("--drop-old", action="store_true", help="重建前删除旧集合")
    parser.add_argument("--chunk-size", type=int, default=settings.chunk_size)
    parser.add_argument("--chunk-overlap", type=int, default=settings.chunk_overlap)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    loader = DocumentLoader()
    splitter = TextSplitter(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    embedder = EmbeddingWorker()
    upserter = MilvusUpserter()

    documents = loader.load(args.input_path)
    print(f"加载文档数: {len(documents)}")
    if not documents:
        print("没有可索引文档，退出")
        return

    chunks = splitter.split_documents(documents)
    print(f"切分后 chunk 数: {len(chunks)}")
    if not chunks:
        print("切分后没有有效 chunk，退出")
        return

    vectors = embedder.embed_texts([chunk.text for chunk in chunks])
    upserter.ensure_collection(drop_old=args.drop_old)
    
    inserted = upserter.upsert_chunks(chunks, vectors)

    print(f"已写入 Milvus chunk 数: {inserted}")
    print(f"集合名: {settings.milvus_collection}")
    print("重建完成")


if __name__ == "__main__":
    main()

```

## File: scripts\trace_log.py

- Extension: .py
- Language: python
- Size: 1439 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
import argparse
import sys
from pathlib import Path

def trace_request(log_path: str, request_id: str):
    """
    按 request_id 筛选日志行
    """
    log_file = Path(log_path)
    if not log_file.exists():
        print(f"❌ 错误: 日志文件未找到: {log_path}")
        return

    print(f"🔍 正在追踪 Request ID: [{request_id}] ...\n" + "-"*50)
    
    found_count = 0
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # 假设日志格式中包含了 request_id
                if request_id in line:
                    print(line.strip())
                    found_count += 1
        
        if found_count == 0:
            print(f"⚠️ 未找到关联该 ID 的日志条目，请确认 ID 是否正确或日志路径是否匹配。")
        else:
            print("-"*50 + f"\n✅ 扫描结束，共找到 {found_count} 条相关日志。")
            
    except Exception as e:
        print(f"❌ 读取日志时发生错误: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="根据 Request ID 快速定位日志")
    parser.add_argument("req_id", help="需要查询的 request_id")
    parser.add_argument("--file", default="logs/app.log", help="日志文件路径 (默认: logs/app.log)")
    
    args = parser.parse_args()
    trace_request(args.file, args.req_id)
```


```

## File: README.md

- Extension: .md
- Language: markdown
- Size: 1356 bytes
- Created: 2026-04-29 23:27:29
- Modified: 2026-04-29 23:27:29

### Code

```markdown
## 项目目标
基于 FastAPI 的 RAG 问答系统：FAQ 直查 + RAG 回退，采用 MySQL/Milvus/Redis 架构，支持结构化日志与 Prometheus 监控

## 技术栈
* **API Framework**: FastAPI
* **Vector Store**: Milvus
* **Metadata Store**: MySQL
* **Monitoring**: Prometheus
* **Core Design**: Hybrid Retrieval & Intent Routing

## 当前进度 (Day 1)
- [x] 工程骨架搭建
- [x] 日志链路追踪 (RequestID)
- [x] 统一异常处理与指标监控
- [x] 意图路由基础占位
- [x] Mock 主链路联调

## 下一步计划
- [x] 接入 MySQL FAQ 检索
- [x] 接入 Milvus 向量检索
- [x] 实现 RRF 混合重排算法

### 今日任务概述(Day 2)

- 修复 MySQL 连接与 FAQ 初始化环境
- 接入最小真实 RAG 链路
- 抽离离线索引流数据结构

### 关键改动

- 修复 Docker / .env.example / 初始化 SQL / test_sql.py
- 新增 indexing 模块与 scripts/reindex.py
- HybridRetriever 改为真实 embedding 检索
- LLMClient 改为真实调用骨架
- 新增 app/models/document.py
- 修复并重建 Record.md

### 当前结果

- FAQ 链路可用
- MySQL 连接稳定
- reindex 入口可用
- RAG 主链路已从 mock 走向真实实现


### 后续计划

- 解耦 generation 层
- 准备真实文档并完成 reindex
- 验证 /query 的完整 RAG 路径

```

## File: Record.md

- Extension: .md
- Language: markdown
- Size: 17223 bytes
- Created: 2026-04-28 15:59:42
- Modified: 2026-05-05 16:55:11

### Code

```markdown
﻿# Project Record

## Day 1

### [Step 1] 主链路骨架完成

- 时间：2026-04-28
- 目标：先跑通 `/query` 的最小主链路，具备 FAQ 直返和 RAG 回退骨架。
- 变更内容：
  - 搭建 FastAPI 应用入口与基础目录结构。
  - 增加 `/health` 健康检查接口。
  - 增加请求日志中间件，记录 `request_id`、耗时、状态码。
  - 增加指标中间件与统一异常处理。
  - 增加 `IntentRouter`、`HybridRetriever`、`LLMClient` 的最小链路。
- 涉及文件：
  - `app/main.py`
  - `app/api/routes_query.py`
  - `app/router/intent_router.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/generation/llm_client.py`
  - `app/middleware/request_logger.py`
  - `app/middleware/metrics_middleware.py`
  - `app/handlers/error_handler.py`
- 当前结果：
  - `/query` 主链路代码可运行。
  - FAQ 命中可直接返回，未命中可进入 RAG 骨架。
- 验证方式：
  - 本地联调 `/query`
  - 检查日志输出与 `/health`
- 下一步：
  - 拆出 FAQ 检索器，替换硬编码 FAQ。

## Day 2

### [Step 1] 拆分 FAQ 检索职责

- 时间：2026-04-28
- 目标：将 FAQ 问答能力从路由层拆出，形成独立 FAQ 检索器。
- 变更内容：
  - 新增 `MysqlFAQRetriever`，封装 FAQ 查询接口。
  - 新增 `FAQHit` 结构，统一 FAQ 命中结果。
  - 将 `IntentRouter` 从“直接返回 FAQ 内容”调整为“只负责路由判断”。
  - 在 `/query` 主链路中接入 FAQ 检索。
- 涉及文件：
  - `app/retrieval/mysql_faq_retriever.py`
  - `app/router/intent_router.py`
  - `app/api/routes_query.py`
- 当前结果：
  - FAQ 命中逻辑已从路由层剥离。
  - 主链路职责更清晰。
- 验证方式：
  - FAQ 问题优先命中 FAQ 检索器。
  - 非 FAQ 问题继续走 RAG 路径。
- 下一步：
  - 将 FAQ 数据源接到真实 MySQL。

### [Step 2] FAQ 检索器接入 MySQL 查询骨架

- 时间：2026-04-28
- 目标：把 FAQ 检索从 mock 升级成真实数据库访问骨架。
- 变更内容：
  - 在 `config.py` 中增加 MySQL FAQ 相关配置。
  - 将 `MysqlFAQRetriever` 改为访问 MySQL。
  - FAQ 查询策略先采用精确匹配。
- 涉及文件：
  - `app/core/config.py`
  - `app/retrieval/mysql_faq_retriever.py`
- 当前结果：
  - FAQ 数据源已切到 MySQL。
  - 为后续真实 FAQ 维护预留了接口。
- 验证方式：
  - 在 MySQL 中准备 FAQ 测试数据。
  - 请求 FAQ 问题并确认返回数据库结果。
- 下一步：
  - 接入向量检索，补齐 RAG 链路。

### [架构补充] 同步 I/O 策略评估与异步升级计划

- 时间：2026-04-28
- 背景：当前 `/query`、`MysqlFAQRetriever` 先以同步实现满足低并发联调。
- 当前判断：
  - 本地开发与演示阶段，同步实现成本更低。
  - 随着 Milvus 与 LLM 调用接入，外部 I/O 会增加，同步模式会逐渐成为瓶颈。
- 风险点：
  - MySQL 每次请求新建连接，存在重复连接开销。
  - Milvus / LLM 持续用同步调用会影响并发能力。
- 结论：
  - 当前阶段先不强制异步化。
  - 后续真实外部 I/O 接入后，再评估 `async` 改造时机。
- 后续升级项：
  - `/query` 改为 `async def`
  - FAQ / Milvus / LLM 逐步异步化
  - 引入连接复用或连接池

### [环境准备] FAQ MySQL 数据表初始化

- 时间：2026-04-28
- 目标：为 FAQ 检索准备 MySQL 数据源。
- 变更内容：
  - 设计 `rag.faq` 表结构。
  - 准备 FAQ 初始化数据。
- 验证方式：
  - 直接 SQL 查询 `faq` 表。
  - 验证关键 FAQ 问题是否可精确命中。
- 下一步：
  - 完成 Docker 化部署并接通应用访问。

### [环境准备] MySQL Docker Compose 方案

- 时间：2026-04-28
- 目标：通过 Docker Compose 启动 MySQL，并自动初始化 FAQ 数据表。
- 变更内容：
  - 设计 `docker-compose.yml` 中的 MySQL 服务。
  - 暴露宿主机端口供本地 Python 应用访问。
  - 挂载初始化 SQL 目录。
- 配置约定：
  - 数据库：`rag`
  - FAQ 表：`faq`
  - 宿主机连接：`127.0.0.1:3307`
- 下一步：
  - 启动 MySQL 并验证 FAQ 表初始化。

## Day 3

### [Step 3] 接入 Milvus 向量检索

- 时间：2026-04-29
- 目标：将 RAG 链路从 mock 检索升级为真实向量检索。
- 变更内容：
  - 新增 `MilvusRetriever`，封装向量检索能力。
  - 增加 Milvus 相关配置项。
  - 将 `HybridRetriever` 改为调用 `MilvusRetriever`。
- 涉及文件：
  - `app/retrieval/milvus_retriever.py`
  - `app/core/config.py`
  - `app/retrieval/hybrid_retriever.py`
- 当前结果：
  - RAG 检索层具备真实向量检索骨架。
- 验证方式：
  - 启动 Milvus 容器并准备测试数据。
  - 请求非 FAQ 问题，确认能检索到文档。
- 下一步：
  - 完善真实 embedding 与索引链路。

### [环境准备] Milvus Docker Compose 配置

- 时间：2026-04-29
- 目标：为向量检索准备完整 Docker 环境。
- 变更内容：
  - 在 `docker-compose.yml` 中增加 `etcd`、`minio`、`milvus-standalone` 服务。
  - 配置依赖关系、健康检查、端口与数据卷。
- 配置约定：
  - Milvus：`19530`
  - MinIO：`9000 / 9001`
- 下一步：
  - 启动 Milvus 服务栈并验证健康状态。

### [测试验证] Milvus 服务健康性检查

- 时间：2026-04-29
- 目标：确认 Milvus 服务栈可用。
- 变更内容：
  - 通过 Compose 启动服务。
  - 编写 / 执行基础测试脚本验证连接与集合操作。
- 涉及文件：
  - `docker-compose.yml`
  - `test_milvus.py`
- 验证方式：
  - `docker compose ps`
  - `curl http://localhost:9091/healthz`
  - Python 连接测试
- 下一步：
  - 接入真实 embedding 与入库流程。

### [P0-1] 编码链路与 FAQ / Milvus 数据核验脚本

- 时间：2026-04-29
- 目标：定位乱码、FAQ 命中异常、Milvus 数据有效性问题。
- 变更内容：
  - 增加文本链路排查脚本。
  - 增加 FAQ 数据核验脚本。
  - 增加 Milvus 集合核验脚本。
- 涉及文件：
  - `scripts/check_text_chain.py`
  - `scripts/verify_mysql_faq_p0.py`
  - `scripts/verify_milvus_collection_p0.py`
- 当前结果：
  - 能独立判断乱码发生在源文件、入库链路、数据库存储还是日志显示。
- 下一步：
  - 修复 MySQL 字符集链路与脏数据。

### [P0-2] MySQL 字符集链路修正方案

- 时间：2026-04-29
- 目标：修正 FAQ 初始化链路中的字符集不一致问题，避免 UTF-8 中文被错误解释后写入 MySQL。
- 变更内容：
  - 统一应用、MySQL、初始化 SQL 的字符集链路。
  - 调整 `.env` / `docker-compose.yml` / 初始化 SQL 的相关配置。
- 涉及文件：
  - `app/core/config.py`
  - `docker-compose.yml`
  - `.env`
  - `.env.example`
  - `docker/mysql/init/001_init_faq.sql`
- 当前结果：
  - 新导入 FAQ 数据可以稳定按 UTF-8 入库。
- 下一步：
  - 删除旧库数据并重建 FAQ 数据。

### [P0-4] 修复 MySQL 连接环境问题

- 时间：2026-04-29
- 目标：修复 MySQL 容器反复重启、`test_sql.py` 无法连接、FAQ 初始化 SQL 无法正确执行的问题。
- 变更内容：
  - 修复 `.env` / `.env.example` 的格式问题。
  - 修复 `docker-compose.yml` 中 MySQL 容器的环境注入问题。
  - 修复 `docker/mysql/init/001_init_faq.sql` 的编码与 SQL 语法问题。
  - 重写 `test_sql.py`，提供干净的 MySQL 连通性验证。
- 涉及文件：
  - `.env`
  - `.env.example`
  - `docker-compose.yml`
  - `docker/mysql/init/001_init_faq.sql`
  - `test_sql.py`
- 当前结果：
  - MySQL 容器可正常启动。
  - `test_sql.py` 可连接并命中 FAQ 数据。
- 验证方式：
  - `docker compose config`
  - `docker compose down -v`
  - `docker compose up -d mysql`
  - `docker compose logs -f mysql`
  - `python test_sql.py`
- 下一步：
  - 继续推进 P1 的真实检索与生成链路。

### [P1-1] 接入最小真实索引链路与生成链路

- 时间：2026-04-29
- 目标：把随机向量检索与 mock 生成升级为最小可用的真实 RAG 主链路。
- 变更内容：
  - 在 `app/indexing/` 下补齐最小索引层：`loaders.py`、`splitter.py`、`embedding_worker.py`、`milvus_upsert.py`。
  - 新增 `scripts/reindex.py` 作为统一重建入口。
  - 将 `HybridRetriever` 改为真实 embedding 检索。
  - 将 `MilvusRetriever` 统一到配置维度。
  - 将 `LLMClient` 接入真实 OpenAI Responses API，并提供未配置密钥时的明确降级提示。
  - 扩展 embedding / chunk / OpenAI 相关配置。
- 涉及文件：
  - `app/core/config.py`
  - `app/indexing/__init__.py`
  - `app/indexing/loaders.py`
  - `app/indexing/splitter.py`
  - `app/indexing/embedding_worker.py`
  - `app/indexing/milvus_upsert.py`
  - `scripts/reindex.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/retrieval/milvus_retriever.py`
  - `app/generation/llm_client.py`
  - `requirements.txt`
- 当前结果：
  - 已具备最小文档入库链路。
  - 查询链路已升级为真实 embedding 检索。
  - 生成链路具备真实 LLM 接入能力。
- 验证方式：
  - `python scripts/reindex.py <input_path> --drop-old`
  - 配置 `OPENAI_API_KEY` 后请求 `/query`
- 下一步：
  - 准备真实文档并完成一次完整 reindex。

### [P1-2] 抽离离线索引流数据结构

- 时间：2026-04-29
- 目标：让离线索引链路中的文档数据结构从具体实现模块中解耦，形成清晰的内部模型边界。
- 变更内容：
  - 新增 `app/models/document.py`，统一承载 `SourceDocument` 与 `DocumentChunk`。
  - 调整 `app/indexing/loaders.py` 引用 `app.models.document`。
  - 调整 `app/indexing/splitter.py` 引用 `app.models.document`。 //纯字符计数切分
  - 调整 `app/indexing/milvus_upsert.py` 统一依赖 `DocumentChunk`。
- 涉及文件：
  - `app/models/document.py`
  - `app/indexing/loaders.py`
  - `app/indexing/splitter.py`
  - `app/indexing/milvus_upsert.py`
- 当前结果：
  - 在线查询流与离线索引流都具备明确的数据结构承载位置。
  - `schemas` 负责 API 边界，`models` 负责内部对象，`indexing / retrieval / generation` 负责处理逻辑。
- 验证方式：
  - `python -m py_compile app/models/document.py app/indexing/loaders.py app/indexing/splitter.py app/indexing/milvus_upsert.py`
  - `python scripts/reindex.py --help`
- 下一步：
  - 后续按需要扩展更细粒度的索引元数据模型。

## Day 4

### [P1-3] 增加最小管理观测接口，作为 RAG 下一阶段切入口

- 时间：2026-05-05
- 目标：在继续构建 RAG 主链路前，先补齐最小观测能力，明确 FAQ、Milvus、集合数据状态，避免后续开发过程“代码写了但不知道是否真的生效”。
- 变更内容：
  - 新增 `GET /admin/status`，统一暴露应用、FAQ、Milvus 的运行状态。
  - 新增 `GET /admin/milvus/sample`，用于抽样查看 Milvus 中的文档内容。
  - 为 `MysqlFAQRetriever` 增加 `health_status()`，返回 MySQL 连通性、FAQ 表存在性和 FAQ 数量。
  - 为 `MilvusRetriever` 增加 `health_status()`，返回 collection 状态和文档数量。
  - 为 `MilvusRetriever` 增加 `sample_documents()`，支持抽样查看当前集合中的 `id/text/source`。
  - 在 `app/main.py` 中挂载 `admin_router`。
- 涉及文件：
  - `app/main.py`
  - `app/api/routes_admin.py`
  - `app/retrieval/mysql_faq_retriever.py`
  - `app/retrieval/milvus_retriever.py`
- 当前结果：
  - `/admin/status` 已可返回当前系统关键状态。
  - FAQ 链路状态明确：MySQL 正常、FAQ 表存在、FAQ 数量为 `6`。
  - Milvus 链路状态明确：`rag_docs` collection 已存在，但 `row_count = 0`，当前还没有正式文档入库。
  - 这说明 FAQ 已经跑通，但最小 RAG 主链路还卡在“知识库数据尚未完成入库”这一层。
- 当前状态快照：
  - `/admin/status` 返回：
    ```json
    {
      "app_name": "rag-project",
      "app_env": "dev",
      "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
      "mysql": {
        "ok": true,
        "host": "127.0.0.1",
        "port": 3307,
        "database": "rag",
        "table": "faq",
        "table_exists": true,
        "faq_count": 6
      },
      "milvus": {
        "ok": true,
        "host": "127.0.0.1",
        "port": 19530,
        "collection": "rag_docs",
        "collection_exists": true,
        "stats": {
          "row_count": 0
        },
        "doc_count": 0
      }
    }
    ```
- 验证方式：
  - 请求 `GET /admin/status`
  - 请求 `GET /admin/milvus/sample`
  - 检查返回中的 `faq_count`、`collection_exists`、`row_count`
- 下一步：
  - 准备最小测试文档并执行一次 `python scripts/reindex.py <input_path> --drop-old`
  - 先把 Milvus 中的 `row_count` 从 `0` 推进到“大于 0”
  - 然后再继续验证 `/query` 的向量检索链路

### [P1-4] 打通最小 RAG 闭环：本地 embedding 降级 + 种子数据入库 + 查询降级返回

- 时间：2026-05-05
- 目标：在不依赖外部模型下载、也不依赖真实 LLM 联网可用的前提下，先把最小 RAG 闭环打通。
- 变更内容：
  - 重写 `EmbeddingWorker`，增加本地降级 embedding：
    - 优先尝试本地缓存的 `SentenceTransformer`
    - 若本地模型不可用，则自动退化为纯本地哈希向量
  - 将 `SentenceTransformer` 调整为 `local_files_only=True`，避免请求时卡在 HuggingFace 下载重试。
  - 调整 `HybridRetriever`，对 query embedding 失败增加兜底保护，避免直接抛异常。
  - 修复 `MilvusUpserter`，在写入后补 `flush`，保证 `row_count` 能正确反映入库数量。
  - 新增 `data/seed/demo_knowledge.jsonl`，提供最小测试知识库数据。
  - 重写 `LLMClient`：
    - 当未配置可用 LLM 时，直接返回检索片段
    - 当 LLM 调用失败时，不再返回 500，而是降级返回检索片段
- 涉及文件：
  - `app/indexing/embedding_worker.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/indexing/milvus_upsert.py`
  - `app/generation/llm_client.py`
  - `data/seed/demo_knowledge.jsonl`
- 当前结果：
  - 已成功执行 `python scripts/reindex.py data/seed --drop-old`
  - 种子知识库成功写入 Milvus
  - `rag_docs` 当前 `row_count = 5`
  - 非 FAQ 问题已能走到 Milvus 检索
  - 即使 OpenAI 调用失败，`/query` 也会以 200 正常返回检索片段，不再直接报 500
- 验证方式：
  - `python scripts/reindex.py data/seed --drop-old`
  - 检查 `GET /admin/status` 中 `milvus.stats.row_count == 5`
  - 检查 `GET /admin/milvus/sample`
  - 使用非 FAQ 问题请求 `/query`，确认返回 `source = "rag"` 且带 `retrieved_docs`
- 验证结果：
  - 重建输出：
    - `加载文档数: 5`
    - `切分后 chunk 数: 5`
    - `已写入 Milvus chunk 数: 5`
  - Milvus 状态：
    - `collection_exists = true`
    - `row_count = 5`
    - `doc_count = 5`
  - `/query` 非 FAQ 验证：
    - 请求：`RAG为什么要先检索再生成答案`
    - 返回：HTTP `200`
    - 路由：`rag`
    - 结果：成功返回检索片段 fallback
- 下一步：
  - 用真实业务文档替换 `data/seed/demo_knowledge.jsonl`
  - 再做一次正式 reindex
  - 然后开始优化 FAQ 路由规则和检索效果

### [P1-5] 为后续优化点补充 TODO 注释

- 时间：2026-05-05
- 目标：把已经识别出的后续优化方向直接标在代码里，方便后续按模块逐步学习和逐步优化，避免遗忘。
- 变更内容：
  - 在 `MysqlFAQRetriever` 中补充 TODO：
    - 后续评估接入 MySQL 连接池
    - 后续把 FAQ 精确匹配升级为模糊匹配、全文检索或 FAQ 向量检索
  - 在 `scripts/reindex.py` 中补充 TODO：
    - 后续将 `batch_size` 做成参数或配置项
    - 后续增加 `tqdm / logging` 提升重建过程可观测性
  - 在 `MilvusUpserter` 中补充 TODO：
    - 当前每批写入后立即 `flush`
    - 后续可改为全部写完后统一 `flush` 提升性能
  - 在 `HybridRetriever` 中补充 TODO：
    - 后续补 BM25 / RRF / rerank，真正升级为 Hybrid Retrieval
  - 在 `LLMClient` 中补充 TODO：
    - 后续把 prompt 构造拆到 `prompt_builder`
    - 后续补更细的错误分类、重试和超时控制
  - 在 `IntentRouter` 中补充 TODO：
    - 当前仅按长度路由
    - 后续升级为关键词规则、FAQ 分数或小模型分类
- 涉及文件：
  - `app/retrieval/mysql_faq_retriever.py`
  - `scripts/reindex.py`
  - `app/indexing/milvus_upsert.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/generation/llm_client.py`
  - `app/router/intent_router.py`
- 当前结果：
  - 代码中已经明确标出后续优化切入点。
  - 后续可以按模块逐个学习，而不用一次记住全部优化方向。
- 验证方式：
  - 直接查看上述文件中的 `TODO` 注释
  - 执行基础语法检查，确认仅补注释未引入新问题
- 下一步：
  - 按模块逐个消化 TODO
  - 优先从 `scripts/reindex.py` 和 `app/indexing/milvus_upsert.py` 开始学习离线入库链路

```

## File: requirements.txt

- Extension: .txt
- Language: plaintext
- Size: 262 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-29 19:27:06

### Code

```plaintext
﻿# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.30.6
prometheus-client==0.20.0

# Data Validation
pydantic==2.9.0
pydantic-settings==2.5.0

# Config
pyyaml==6.0.2

# Logging
structlog==24.4.0

PyMySQL
pymilvus
numpy

openai
httpx
sentence-transformers

```

## File: roadmap.md

- Extension: .md
- Language: markdown
- Size: 2391 bytes
- Created: 2026-04-29 23:14:31
- Modified: 2026-04-29 23:14:31

### Code

```markdown
rag_project/
├─ app/
│    ├─ main.py  ✅应用入口与装配层    
      初始化日志；注册中间件（请求日志、指标采集）；注册全局异常处理；挂载 /metrics；提供 /health 健康检查。
│    ├─ api/  
│    │  ├─ routes_query.py
│    │  ├─ routes_admin.py
│    │  └─ schemas.py

│    ├─ core/    ✅
│    │  ├─ config.py    #统一配置源
│    │  ├─ logger.py    #统一日志格式与输出通道
         通过 RequestIdFilter 给日志补 request_id；配置 console + file 双输出；格式统一；可接管 uvicorn 日志写入同一文件。
│    │  └─ metrics.py   #指标定义层

│    ├─ middleware/  ✅
│    │  ├─ request_context.py
│    │  ├─ request_logger.py    #请求日志中间件
│    │  └─ metrics_middleware.py    #请求指标中间件

│    ├─ handlers/   ✅
│    │  └─ error_handler.py     #统一异常出口

│    ├─ models/
│    │  ├─ document.py
│    │  ├─ query.py
│    │  └─ response.py

│    ├─ router/
│    │  ├─ intent_router.py
│    │  └─ threshold_policy.py

│    ├─ retrieval/
│    │  ├─ mysql_faq_retriever.py
│    │  ├─ bm25_retriever.py
│    │  ├─ milvus_retriever.py
│    │  ├─ hybrid_retriever.py
│    │  └─ reranker.py

│    ├─ generation/
│    │  ├─ prompt_builder.py
│    │  ├─ llm_client.py
│    │  └─ answer_postprocess.py

│    ├─ indexing/
│    │  ├─ loaders.py
│    │  ├─ splitter.py
│    │  ├─ embedding_worker.py
│    │  └─ milvus_upsert.py

│    ├─ cache/
│    │  ├─ redis_cache.py
│    │  └─ cache_keys.py

│    ├─ eval/
│    │  ├─ dataset.py
│    │  ├─ offline_eval.py
│    │  └─ online_eval.py

│    └─ tests/
│       ├─ test_api.py
│       ├─ test_router.py
│       ├─ test_retrieval.py
│       └─ test_generation.py

├─ scripts/
│  ├─ reindex.py
│  ├─ warmup_cache.py
│  └─ replay_logs.py

├─ configs/
│  ├─ config.dev.yaml
│  ├─ config.prod.yaml
│  └─ prompts.yaml

├─ requirements.txt

└─ README.md

```

## File: test_milvus.py

- Extension: .py
- Language: python
- Size: 3498 bytes
- Created: 2026-04-29 11:51:44
- Modified: 2026-04-29 11:52:27

### Code

```python
#!/usr/bin/env python3
"""
Milvus服务健康性测试脚本
测试Milvus连接、集合创建、文档插入和向量搜索功能
"""

import sys
import time
from pymilvus import MilvusClient, DataType
import numpy as np

def test_milvus_health():
    """测试Milvus服务健康性"""
    print("🔍 开始测试Milvus服务健康性...")

    try:
        # 连接Milvus
        client = MilvusClient(uri="http://127.0.0.1:19530")
        print("✅ 成功连接到Milvus")

        # 测试集合操作
        collection_name = "test_collection"

        # 删除已存在的测试集合
        if client.has_collection(collection_name):
            client.drop_collection(collection_name)
            print(f"🗑️ 删除已存在的测试集合: {collection_name}")

        # 创建测试集合
        schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=100, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=768)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=2000)

        index_params = client.prepare_index_params()
        index_params.add_index(field_name="vector", index_type="FLAT", metric_type="COSINE")

        client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params
        )
        print(f"✅ 成功创建测试集合: {collection_name}")

        # 插入测试数据
        test_docs = [
            {
                "id": "doc1",
                "vector": np.random.rand(768).tolist(),
                "text": "这是一个测试文档，关于人工智能和机器学习。"
            },
            {
                "id": "doc2",
                "vector": np.random.rand(768).tolist(),
                "text": "另一个测试文档，讨论自然语言处理技术。"
            },
            {
                "id": "doc3",
                "vector": np.random.rand(768).tolist(),
                "text": "第三个测试文档，涉及向量数据库和检索系统。"
            }
        ]

        client.insert(collection_name=collection_name, data=test_docs)
        print(f"✅ 成功插入 {len(test_docs)} 条测试文档")

        # 等待索引构建
        time.sleep(2)

        # 测试向量搜索
        query_vector = np.random.rand(768).tolist()
        search_results = client.search(
            collection_name=collection_name,
            data=[query_vector],
            anns_field="vector",
            search_params={"metric_type": "COSINE", "params": {}},
            limit=3,
            output_fields=["text"]
        )

        print(f"✅ 向量搜索成功，返回 {len(search_results[0])} 条结果")
        for i, hit in enumerate(search_results[0]):
            print(f"  结果{i+1}: ID={hit['id']}, 相似度={hit['distance']:.4f}")

        # 清理测试集合
        client.drop_collection(collection_name)
        print(f"🧹 清理测试集合: {collection_name}")

        print("\n🎉 Milvus服务健康性测试全部通过！")
        return True

    except Exception as e:
        print(f"❌ Milvus测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_milvus_health()
    sys.exit(0 if success else 1)
```

## File: test_sql.py

- Extension: .py
- Language: python
- Size: 3474 bytes
- Created: 2026-04-28 22:36:51
- Modified: 2026-05-05 15:09:23

### Code

```python
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

```

## File: verify_milvus_collection_p0.py

- Extension: .py
- Language: python
- Size: 3037 bytes
- Created: 2026-04-29 23:27:29
- Modified: 2026-05-05 15:09:23

### Code

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pymilvus import MilvusClient  # noqa: E402
from app.core.config import settings  # noqa: E402

SUSPECT_GARBLED_PATTERNS = [
    "浣", "鎴", "绯", "鍚", "妫", "璇", "鐨", "銆", "锛", "锟", "�"
]


def has_garbled_text(text: str) -> bool:
    if not text:
        return False
    return any(token in text for token in SUSPECT_GARBLED_PATTERNS)


def short_text(text: str, limit: int = 160) -> str:
    text = (text or "").replace("\n", "\\n")
    return text if len(text) <= limit else text[:limit] + "..."


def main():
    print("=" * 80)
    print("P0-3 Milvus 集合核验")
    print("=" * 80)

    client = MilvusClient(
        uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
        user=settings.milvus_user or None,
        password=settings.milvus_password or None,
    )

    collection_name = settings.milvus_collection
    print(f"目标集合: {collection_name}")

    exists = client.has_collection(collection_name)
    print(f"集合存在: {exists}")

    if not exists:
        print("结论: 业务集合还没准备好，当前 RAG 检索不成立。")
        return

    try:
        stats = client.get_collection_stats(collection_name=collection_name)
        print(f"集合统计: {stats}")
    except Exception as e:
        print(f"读取集合统计失败: {e}")

    print("\n尝试抽样查询 text 字段...")
    try:
        rows = client.query(
            collection_name=collection_name,
            filter="id != ''",
            output_fields=["id", "text"],
            limit=10,
        )
    except Exception as e:
        print(f"抽样查询失败: {e}")
        return

    if not rows:
        print("集合存在，但没有可读样本，基本等于没数据。")
        return

    normal_count = 0
    garbled_count = 0
    empty_count = 0

    for idx, row in enumerate(rows, start=1):
        doc_id = row.get("id", "")
        text = row.get("text", "")

        if not text:
            empty_count += 1
            flag = "空文本"
        elif has_garbled_text(text):
            garbled_count += 1
            flag = "疑似乱码"
        else:
            normal_count += 1
            flag = "正常"

        print(f"[{idx}] id={doc_id} | {flag} | text={short_text(text)}")

    print("\n统计:")
    print(f"正常样本: {normal_count}")
    print(f"疑似乱码样本: {garbled_count}")
    print(f"空文本样本: {empty_count}")

    if garbled_count > 0:
        print("结论: Milvus 内部 text 字段存在乱码风险。")
    elif normal_count > 0:
        print("结论: Milvus 至少有部分文本样本是正常的。")
    else:
        print("结论: 当前集合数据质量可疑。")


if __name__ == "__main__":
    main()

```

## File: verify_mysql_faq_p0.py

- Extension: .py
- Language: python
- Size: 2655 bytes
- Created: 2026-04-29 23:27:29
- Modified: 2026-05-05 15:09:23

### Code

```python
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

```

## File: 项目问题清单.md

- Extension: .md
- Language: markdown
- Size: 5129 bytes
- Created: 2026-05-05 15:49:53
- Modified: 2026-05-05 15:49:53

### Code

```markdown
# 项目问题清单

## 当前结论

当前项目已经有基础骨架，但本质上还是一个 **最小可用原型**：

- 在线问答主链路已具备雏形
- FAQ / 向量检索 / LLM 生成已经串起来了
- 但还不是完整的 Hybrid RAG
- 当前最重要目标不是“继续加功能”，而是 **先把整体稳定跑通**

---

## P0：必须先解决的问题

### 1. Embedding 模型在线加载不稳定

现象：

- `EmbeddingWorker` 在请求时动态加载 `SentenceTransformer`
- 如果本地没有缓存好，会在查询时触发模型下载
- 现有日志里已经出现加载失败，导致 `/query` 直接报错

影响：

- 主链路不稳定
- 用户第一次调用就可能失败

建议：

- 先保证 embedding 模型本地可用
- 不要把“首次下载模型”放在在线请求里
- 最好改成“启动前准备好”或“reindex 前准备好”

---

### 2. `HybridRetriever` 名字和真实能力不一致

现状：

- 当前只有 Milvus 向量检索
- 没有 BM25
- 没有 RRF
- 没有 rerank

影响：

- 容易误判项目完成度
- 后续排查问题时会混淆真实瓶颈

建议：

- 短期先承认事实：当前就是“向量检索版 RAG”
- 等主链路稳定后，再逐步补 BM25 / RRF / rerank

---

### 3. README 与代码真实状态不一致

现状：

- README 写了 Redis
- README 写了已实现 RRF 混合重排
- 但代码里没有对应实现

影响：

- 容易误导自己和后续维护者

建议：

- 后续统一文档口径
- 文档只写“已经落地”的能力

---

### 4. FAQ 检索能力过弱

现状：

- MySQL FAQ 走的是 `question = %s` 精确匹配

影响：

- 只有完全一样的问题才能命中
- 稍微换种问法就失败

建议：

- 短期先保留精确匹配，先保证能跑
- 跑通后再升级成模糊匹配 / 全文检索 / FAQ embedding 检索

---

### 5. 在线查询承担了过多初始化责任

现状：

- 查询时才初始化 embedding 模型
- 查询时才初始化 MilvusRetriever
- MilvusRetriever 内部还会检查/创建 collection

影响：

- 首次请求慢
- 请求期行为不稳定
- 排查困难

建议：

- 在线查询只做“查询”
- 初始化、建 collection、建索引，尽量放到离线阶段

---

## P1：跑通后优先优化的问题

### 6. IntentRouter 规则过于粗糙

现状：

- 仅按 `query` 长度判断 FAQ / RAG

影响：

- 路由误判概率高

建议：

- 先保持简单规则
- 后续再增加关键词规则、置信度规则，或者小模型分类

---

### 7. 文本切分过于原始

现状：

- 当前是固定长度字符切分

影响：

- 容易切断语义
- 影响召回质量

建议：

- 跑通后再升级为按段落 / 标题 / 语义边界切分

---

### 8. 检索结果元数据不足

现状：

- 当前只保留 `doc_id / score / snippet`

影响：

- citation 弱
- 不利于定位来源

建议：

- 后续补 `source / title / section / page / chunk_index`

---

### 9. MySQL 每次请求新建连接

现状：

- FAQ 查询每次都直接 `pymysql.connect`

影响：

- 延迟增加
- 并发能力差

建议：

- 跑通后再改连接池

---

### 10. generation 层职责还没拆干净

现状：

- `prompt_builder.py` 还是空壳
- `answer_postprocess.py` 还是占位
- `LLMClient` 同时承担 prompt / 调用 / fallback

影响：

- 不利于后续替换模型和调 prompt

建议：

- 后续拆成：
  - prompt 构造
  - LLM 调用
  - 回答后处理

---

## P2：后续增强项

### 11. 增加 BM25 检索

目标：

- 补上关键词召回

---

### 12. 增加 RRF 融合

目标：

- 融合 FAQ / BM25 / 向量结果

---

### 13. 增加 rerank

目标：

- 对 topN 候选做二次排序

---

### 14. 增加缓存层

目标：

- 如果后续确实需要 Redis，再引入
- 不建议现在为了“架构完整”提前上 Redis

---

### 15. 增加管理与运维能力

目标：

- reindex 管理入口
- collection 状态检查
- FAQ 数据管理

---

## 建议推进顺序

### 阶段 1：先把整体跑通

目标：

- `/health` 正常
- `/query` 至少能稳定返回
- FAQ 可查
- Milvus 可查
- LLM 未配置时也能 fallback

先做：

1. 固定 embedding 模型加载方式
2. 确保 MySQL / Milvus / FastAPI 配置正确
3. 准备一小批真实测试文档
4. 跑通 `scripts/reindex.py`
5. 跑通 `/query`

---

### 阶段 2：把链路做稳定

目标：

- 首次请求不炸
- 检索失败可控
- 错误更容易定位

再做：

1. 减少在线初始化
2. 补更清晰的启动检查
3. 清理 README 与真实状态不一致问题

---

### 阶段 3：开始做效果优化

目标：

- 提升召回质量
- 提升回答质量

再做：

1. FAQ 检索增强
2. 文本切分优化
3. 补元数据
4. prompt_builder 落地

---

### 阶段 4：再升级成真正的 Hybrid RAG

目标：

- 关键词召回 + 向量召回 + 融合重排

最后做：

1. BM25
2. RRF
3. rerank
4. 缓存层

---

## 最终原则

先做：

- 能跑
- 稳定
- 可排查

再做：

- 更准
- 更快
- 更完整

不要一开始就把系统做复杂。

```

## File: app\main.py

- Extension: .py
- Language: python
- Size: 1400 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-05-05 15:56:32

### Code

```python
from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.logger import setup_logger

from app.handlers.error_handler import register_exception_handlers
from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.request_logger import RequestLoggerMiddleware
from app.api.routes_admin import router as admin_router
from app.api.routes_query import router as query_router

# 注册了哪些中间件？挂了哪些路由？异常处理在哪接入？

def create_app() -> FastAPI:

    setup_logger()

    app = FastAPI(title=settings.app_name,debug=settings.debug)
    @app.middleware("http")
    async def ensure_utf8_json(request, call_next):
        resp = await call_next(request)
        ct = resp.headers.get("content-type", "")
        if ct.startswith("application/json") and "charset" not in ct:
            resp.headers["content-type"] = "application/json; charset=utf-8"
        return resp

    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(MetricsMiddleware)

    register_exception_handlers(app)
    app.mount("/metrics", make_asgi_app())

    @app.get("/health")
    def health():
        return {"status": "ok", "env": settings.app_env}

    return app

app = create_app()
app.include_router(admin_router)
app.include_router(query_router)

```

## File: app\__init__.py

- Extension: .py
- Language: python
- Size: 0 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

```

## File: app\api\routes_admin.py

- Extension: .py
- Language: python
- Size: 1174 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-05-05 15:56:24

### Code

```python
from fastapi import APIRouter

from app.core.config import settings
from app.retrieval.milvus_retriever import MilvusRetriever
from app.retrieval.mysql_faq_retriever import MysqlFAQRetriever

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status")
def admin_status():
    result = {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "embedding_model": settings.embedding_model,
        "mysql": {"ok": False},
        "milvus": {"ok": False},
    }

    try:
        result["mysql"] = MysqlFAQRetriever().health_status()
    except Exception as e:
        result["mysql"] = {
            "ok": False,
            "error": str(e),
        }

    try:
        result["milvus"] = MilvusRetriever().health_status()
    except Exception as e:
        result["milvus"] = {
            "ok": False,
            "error": str(e),
        }

    return result


@router.get("/milvus/sample")
def milvus_sample(limit: int = 5):
    retriever = MilvusRetriever()
    return {
        "collection": settings.milvus_collection,
        "limit": limit,
        "items": retriever.sample_documents(limit=max(1, min(limit, 20))),
    }

```

## File: app\api\routes_query.py

- Extension: .py
- Language: python
- Size: 1981 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-05-05 15:10:53

### Code

```python
from fastapi import APIRouter, Request

from app.api.schemas import QueryRequest, QueryResponse, DocItem
from app.router.intent_router import IntentRouter
from app.models.query import RetrievalStrategy
from app.retrieval.hybrid_retriever import HybridRetriever
from app.generation.llm_client import LLMClient
from app.retrieval.mysql_faq_retriever import MysqlFAQRetriever
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["query"])

intent_router = IntentRouter()
faq_retriever = MysqlFAQRetriever()
llm = LLMClient()

retriever = HybridRetriever()


@router.post("/query", response_model=QueryResponse)
def query_api(req: QueryRequest, request: Request):
    
    trace_id = getattr(request.state, "request_id", "-")
    decision = intent_router.route(req.query)

    logger.info(f"[{trace_id}] Query: {req.query} | Route Strategy: {decision.strategy}")

    if decision.strategy == RetrievalStrategy.DIRECT_FAQ:
        faq_hit = faq_retriever.retrieve(req.query)
        if faq_hit:
            return QueryResponse(
                trace_id=trace_id,
                query=req.query,
                answer=faq_hit.answer,
                source="faq",
                route=decision.strategy.value,
                confidence=faq_hit.score,
                citations=[faq_hit.faq_id],
                retrieved_docs=[],
            )

    docs = retriever.retrieve(req.query, req.top_k)

    ans = llm.generator(req.query, docs)

    return QueryResponse(
        trace_id=trace_id,
        query=req.query,
        answer=ans.text,
        source="rag",
        route=RetrievalStrategy.RAG.value,
        confidence=decision.confidence,
        citations=ans.citations,
        retrieved_docs=[
            DocItem(
                doc_id=d.doc_id, 
                score=float(d.score), 
                snippet=d.snippet
            )for d in docs 
        ],
    )

```

## File: app\api\schemas.py

- Extension: .py
- Language: python
- Size: 525 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(3, ge=1, le=10)


class DocItem(BaseModel):
    doc_id: str
    score: float
    snippet: str


class QueryResponse(BaseModel):
    trace_id: str
    query: str
    answer: str
    source: str
    route: str
    confidence: float
    citations: list[str] = Field(default_factory=list)
    retrieved_docs: list[DocItem] = Field(default_factory=list)

```

## File: app\api\__init__.py

- Extension: .py
- Language: python
- Size: 0 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

```

## File: app\core\config.py

- Extension: .py
- Language: python
- Size: 2121 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-05-05 15:09:23

### Code

```python
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = Field(default="rag-project", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=False, alias="DEBUG")

    mysql_host: str = Field(..., alias="MYSQL_HOST")
    mysql_port: int = Field(..., alias="MYSQL_PORT")
    mysql_user: str = Field(..., alias="MYSQL_USER")
    mysql_password: str = Field(..., alias="MYSQL_PASSWORD")
    mysql_database: str = Field(..., alias="MYSQL_DATABASE")
    mysql_faq_table: str = Field(default="faq", alias="MYSQL_FAQ_TABLE")

    milvus_host: str = Field(default="127.0.0.1", alias="MILVUS_HOST")
    milvus_port: int = Field(default=19530, alias="MILVUS_PORT")
    milvus_collection: str = Field(default="rag_docs", alias="MILVUS_COLLECTION")
    milvus_user: str = Field(default="", alias="MILVUS_USER")
    milvus_password: str = Field(default="", alias="MILVUS_PASSWORD")

    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        alias="EMBEDDING_MODEL",
    )
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")
    chunk_size: int = Field(default=500, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=80, alias="CHUNK_OVERLAP")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_max_output_tokens: int = Field(default=800, alias="OPENAI_MAX_OUTPUT_TOKENS")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


settings = Settings()

```

## File: app\core\logger.py

- Extension: .py
- Language: python
- Size: 2057 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
import logging
from logging.config import dictConfig
from pathlib import Path
from app.core.config import settings


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def setup_logger() -> None:
    log_dir = getattr(settings, "log_dir", "logs")
    log_file = getattr(settings, "log_file", "app.log")
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_id_filter": {"()": RequestIdFilter}
            },
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(request_id)s | %(name)s | %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "filters": ["request_id_filter"],
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": str(Path(log_dir) / log_file),
                    "maxBytes": 10 * 1024 * 1024,
                    "backupCount": 5,
                    "formatter": "standard",
                    "filters": ["request_id_filter"],
                    "encoding": "utf-8",
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": settings.log_level.upper(),
            },
        }
    )

    # 让 uvicorn 日志走 root，统一进入文件
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

```

## File: app\core\metrics.py

- Extension: .py
- Language: python
- Size: 673 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from prometheus_client import Counter,Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "HTTP 请求总数",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP 请求耗时(秒)",
    ["method", "path"],
)

def record_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        path=path,
        status_code=str(status_code),
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method,
        path=path,
    ).observe(duration_seconds)
```

## File: app\generation\answer_postprocess.py

- Extension: .py
- Language: python
- Size: 118 bytes
- Created: 2026-04-29 22:13:32
- Modified: 2026-04-29 22:23:52

### Code

```python
"""
  - 清洗输出文本
  - 空答案处理
  - fallback
  - citation 整理
  - 转成 GeneratedAnswer
"""

```

## File: app\generation\llm_client.py

- Extension: .py
- Language: python
- Size: 2864 bytes
- Created: 2026-05-05 16:51:26
- Modified: 2026-05-05 16:51:26

### Code

```python
from typing import List

from openai import OpenAI

from app.core.config import settings
from app.core.logger import get_logger
from app.models.response import GeneratedAnswer, RetrievedDoc

logger = get_logger(__name__)


class LLMClient:
    def __init__(self):
        self.api_key = settings.openai_api_key.strip()
        self.base_url = settings.openai_base_url.strip()
        self.model = settings.openai_model
        self.max_output_tokens = settings.openai_max_output_tokens
        self.client = None

        if self.api_key:
            kwargs = {"api_key": self.api_key}
            if self.base_url and (
                self.base_url.startswith("http://") or self.base_url.startswith("https://")
            ):
                kwargs["base_url"] = self.base_url
            self.client = OpenAI(**kwargs)

    def generator(self, query: str, docs: List[RetrievedDoc]) -> GeneratedAnswer:
        citations = [d.doc_id for d in docs]
        if not docs:
            return GeneratedAnswer(
                text="未检索到相关资料，暂时无法基于知识库回答这个问题。",
                citations=citations,
                model="no-context",
            )

        context = "\n\n".join([f"[文档 {doc.doc_id}]\n{doc.snippet}" for doc in docs])

        if not self.client:
            return GeneratedAnswer(
                text="未配置可用的 LLM，当前返回检索到的资料片段：\n\n" + context,
                citations=citations,
                model="fallback-no-openai",
            )

        try:
            # TODO: 后续将 prompt 构造拆到 prompt_builder，并补回答后处理与引用整理。
            response = self.client.responses.create(
                model=self.model,
                instructions=(
                    "你是一个 RAG 问答助手。"
                    "只能基于提供的检索资料回答。"
                    "如果资料不足，就明确说不知道，不要编造。"
                    "回答尽量简洁直接。"
                ),
                input=f"用户问题：{query}\n\n检索资料：\n{context}",
                max_output_tokens=self.max_output_tokens,
            )
            return GeneratedAnswer(
                text=response.output_text.strip(),
                citations=citations,
                model=self.model,
            )
        except Exception as e:
            # TODO: 当前生成失败直接降级返回检索片段；后续可补更细的错误分类、重试策略和超时控制。
            logger.warning(f"LLM generation failed, fallback to retrieved docs: {e}")
            return GeneratedAnswer(
                text="LLM 调用失败，当前返回检索到的资料片段：\n\n" + context,
                citations=citations,
                model="fallback-llm-error",
            )

```

## File: app\generation\prompt_builder.py

- Extension: .py
- Language: python
- Size: 342 bytes
- Created: 2026-04-29 22:13:26
- Modified: 2026-04-30 16:53:33

### Code

```python
"""
  职责应该是：

  - 输入：
      - query
      - retrieved_docs
  - 输出：
      - system / instructions
      - user input / context prompt
"""

from __future__ import annotations
from app.models.response import RetrievedDoc


def build_prompt(query: str, docs: list[RetrievedDoc]) -> tuple[str, str]:
    ...
```

## File: app\handlers\error_handler.py

- Extension: .py
- Language: python
- Size: 1424 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.logger import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", "-")
        logger.warning(
            "http_exception status=%s detail=%s",
            exc.status_code,
            exc.detail,
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": str(exc.detail),
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "-")
        logger.exception(
            "unhandled_exception: %s",
            str(exc),
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "Internal Server Error",
                "request_id": request_id,
            },
        )

```

## File: app\indexing\embedding_worker.py

- Extension: .py
- Language: python
- Size: 3119 bytes
- Created: 2026-05-05 16:07:57
- Modified: 2026-05-05 16:13:43

### Code

```python
from __future__ import annotations

import hashlib
import math

from app.core.config import settings

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


class EmbeddingWorker:
    _model_cache: dict[str, object] = {}
    _model_load_failed: set[str] = set()

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self.dimension = settings.embedding_dimension

    @property
    def model(self):
        if self.model_name in self._model_cache:
            return self._model_cache[self.model_name]

        if self.model_name in self._model_load_failed:
            return None

        if SentenceTransformer is None:
            self._model_load_failed.add(self.model_name)
            return None

        try:
            model = SentenceTransformer(self.model_name, local_files_only=True)
            self._model_cache[self.model_name] = model
            return model
        except Exception:
            self._model_load_failed.add(self.model_name)
            return None

    def embed_query(self, query: str) -> list[float]:
        return self._embed_one(query)

    def embed_texts(self, texts: list[str], batch_size: int | None = None) -> list[list[float]]:
        if not texts:
            return []

        model = self.model
        if model is not None:
            vectors = model.encode(
                texts,
                batch_size=batch_size or settings.embedding_batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return vectors.tolist()

        return [self._fallback_embed(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        model = self.model
        if model is not None:
            vector = model.encode(text, normalize_embeddings=True)
            return vector.tolist()
        return self._fallback_embed(text)

    def _fallback_embed(self, text: str) -> list[float]:
        text = (text or "").strip().lower()
        if not text:
            return [0.0] * self.dimension

        vector = [0.0] * self.dimension
        units = self._split_units(text)

        for idx, unit in enumerate(units):
            bucket = self._hash_to_bucket(unit)
            weight = 1.0 + min(idx, 8) * 0.03
            vector[bucket] += weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]

    def _split_units(self, text: str) -> list[str]:
        units: list[str] = []
        for token in text.split():
            units.append(token)

        chars = [char for char in text if not char.isspace()]
        units.extend(chars)

        for i in range(len(chars) - 1):
            units.append(chars[i] + chars[i + 1])

        return units or [text]

    def _hash_to_bucket(self, text: str) -> int:
        digest = hashlib.md5(text.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % self.dimension

```

## File: app\indexing\loaders.py

- Extension: .py
- Language: python
- Size: 1844 bytes
- Created: 2026-04-29 19:27:06
- Modified: 2026-05-05 15:09:23

### Code

```python
from pathlib import Path
import json

from app.models.document import SourceDocument


SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".markdown"}


class DocumentLoader:
    def load(self, input_path: str) -> list[SourceDocument]:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"输入路径不存在: {input_path}")

        if path.is_file():
            return self._load_file(path)

        documents: list[SourceDocument] = []
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_TEXT_SUFFIXES | {".jsonl"}:
                documents.extend(self._load_file(file_path))
        return documents

    def _load_file(self, file_path: Path) -> list[SourceDocument]:
        if file_path.suffix.lower() == ".jsonl":
            return self._load_jsonl(file_path)

        text = file_path.read_text(encoding="utf-8")
        return [
            SourceDocument(
                doc_id=file_path.stem,
                text=text,
                source=str(file_path),
            )
        ]

    def _load_jsonl(self, file_path: Path) -> list[SourceDocument]:
        documents: list[SourceDocument] = []
        with file_path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                text = (record.get("text") or "").strip()
                if not text:
                    continue
                doc_id = str(record.get("id") or f"{file_path.stem}-{idx}")
                source = str(record.get("source") or file_path)
                documents.append(SourceDocument(doc_id=doc_id, text=text, source=source))
        return documents

```

## File: app\indexing\milvus_upsert.py

- Extension: .py
- Language: python
- Size: 2720 bytes
- Created: 2026-05-05 16:11:42
- Modified: 2026-05-05 16:49:57

### Code

```python
from pymilvus import DataType, MilvusClient

from app.core.config import settings
from app.core.logger import get_logger
from app.models.document import DocumentChunk

logger = get_logger(__name__)


class MilvusUpserter:
    def __init__(self):
        self.client = MilvusClient(
            uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
            user=settings.milvus_user or None,
            password=settings.milvus_password or None,
        )
        self.collection_name = settings.milvus_collection

    def ensure_collection(self, drop_old: bool = False) -> None:
        if drop_old and self.client.has_collection(self.collection_name):
            self.client.drop_collection(self.collection_name)
            logger.info(f"Dropped Milvus collection: {self.collection_name}")

        if self.client.has_collection(self.collection_name):
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=100, is_primary=True)
        schema.add_field(
            field_name="vector",
            datatype=DataType.FLOAT_VECTOR,
            dim=settings.embedding_dimension,
        )
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=4000)
        schema.add_field(field_name="source", datatype=DataType.VARCHAR, max_length=500)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="FLAT",
            metric_type="COSINE",
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        logger.info(f"Created Milvus collection: {self.collection_name}")

    def upsert_chunks(self, chunks: list[DocumentChunk], vectors: list[list[float]]) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("chunks 与 vectors 数量不一致")

        if not chunks:
            return 0

        rows = [
            {
                "id": chunk.chunk_id,
                "vector": vector,
                "text": chunk.text,
                "source": chunk.source,
            }
            for chunk, vector in zip(chunks, vectors)
        ]
        # TODO: 当前每批写入后立即 flush，优先保证数据可见；后续可改为全部写完后统一 flush 提升性能。
        self.client.insert(collection_name=self.collection_name, data=rows)
        self.client.flush(collection_name=self.collection_name)
        logger.info(f"Inserted {len(rows)} chunks into Milvus")
        return len(rows)

```

## File: app\indexing\splitter.py

- Extension: .py
- Language: python
- Size: 1591 bytes
- Created: 2026-04-29 19:27:06
- Modified: 2026-05-05 15:09:23

### Code

```python
from app.models.document import DocumentChunk, SourceDocument


class TextSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能小于 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents: list[SourceDocument]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for doc in documents:
            chunks.extend(self._split_one(doc))
        return chunks

    def _split_one(self, document: SourceDocument) -> list[DocumentChunk]:
        text = document.text.strip()
        if not text:
            return []

        chunks: list[DocumentChunk] = []
        start = 0
        index = 0
        step = self.chunk_size - self.chunk_overlap

        while start < len(text):
            end = min(len(text), start + self.chunk_size)
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document.doc_id}#chunk-{index}",
                        text=chunk_text,
                        source=document.source,
                    )
                )
                index += 1
            if end >= len(text):
                break
            start += step

        return chunks

```

## File: app\indexing\__init__.py

- Extension: .py
- Language: python
- Size: 35 bytes
- Created: 2026-04-29 19:27:06
- Modified: 2026-05-05 15:09:23

### Code

```python
"""索引链路相关模块。"""

```

## File: app\middleware\metrics_middleware.py

- Extension: .py
- Language: python
- Size: 634 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.metrics import record_http_request


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        record_http_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration,
        )
        return response

```

## File: app\middleware\request_logger.py

- Extension: .py
- Language: python
- Size: 933 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logger import get_logger

logger = get_logger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={"request_id": request_id},
        )

        response.headers["X-Request-ID"] = request_id
        return response

```

## File: app\models\document.py

- Extension: .py
- Language: python
- Size: 441 bytes
- Created: 2026-04-29 20:36:51
- Modified: 2026-05-05 15:09:23

### Code

```python
from dataclasses import dataclass
"""
  #### 索引文档模型

  - SourceDocument
  - DocumentChunk
"""


@dataclass
class SourceDocument:
    """
    - title
    - metadata
    - tags
    - section
    - source_type
    """
    doc_id: str
    text: str
    source: str


@dataclass
class DocumentChunk:
    """
    - title
    - metadata
    - tags
    - section
    - source_type
    """
    chunk_id: str
    text: str
    source: str

```

## File: app\models\query.py

- Extension: .py
- Language: python
- Size: 919 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-29 21:24:18

### Code

```python
from dataclasses import dataclass
from enum import Enum

"""
  #### 查询决策模型

  - Intent
  - RetrievalStrategy
  - RouteDecision
"""



# TODO 将其升级为 Pydantic 的 BaseModel

class Intent(str,Enum): 
    FAQ = 'faq'                # FAQ: Frequently Asked Questions
    KNOWLEDGE = 'knowledge'

class RetrievalStrategy(str,Enum): #当你继承 Enum 时，Python 自动把你定义里的所有类属性（如 RAG）都转换成了一个对象（Instance）
    DIRECT_FAQ = "direct_faq"      #若不继承str，则输出: <enum 'MyEnum'> (它不是字符串，它是 MyEnum 这个枚举类的一个实例)
    RAG = "rag"

@dataclass  
class RouteDecision:    # if decision.confidence > 0.95: ...
    intent:Intent        # Python 的 “委托” (Delegation) 和 “混入” (Mixin)
    strategy:RetrievalStrategy
    confidence:float  
    direct_answer:str | None = None
```

## File: app\models\response.py

- Extension: .py
- Language: python
- Size: 613 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-29 21:24:29

### Code

```python
from dataclasses import dataclass

"""
  #### 查询结果模型

  - RetrievedDoc
  - GeneratedAnswer
"""

# TODO 将其升级为 Pydantic 的 BaseModel

@dataclass
class  RetrievedDoc:

    # TODO 后续扩充 metadata: dict 字段,把页码、章节、文件来源 URL 塞进去
    
    doc_id: str
    score: float
    snippet: str
    # matadata: json
     
@dataclass
class GeneratedAnswer:
    text: str
    citations: list[str]
    model: str # 不同模型间进行 A/B 测试或者平滑迁移时，这个字段能帮你追踪到：这条答案到底是哪个模型生成的。
```

## File: app\retrieval\bm25_retriever.py

- Extension: .py
- Language: python
- Size: 2 bytes
- Created: 2026-04-29 22:11:25
- Modified: 2026-05-05 15:09:23

### Code

```python


```

## File: app\retrieval\hybrid_retriever.py

- Extension: .py
- Language: python
- Size: 1634 bytes
- Created: 2026-05-05 16:08:44
- Modified: 2026-05-05 16:50:19

### Code

```python
from typing import List

from app.core.logger import get_logger
from app.indexing.embedding_worker import EmbeddingWorker
from app.models.response import RetrievedDoc
from app.retrieval.milvus_retriever import MilvusRetriever

logger = get_logger(__name__)


class HybridRetriever:
    def __init__(self):
        self.embedder = EmbeddingWorker()
        self._milvus_retriever: MilvusRetriever | None = None

    def _get_milvus_retriever(self) -> MilvusRetriever | None:
        if self._milvus_retriever is not None:
            return self._milvus_retriever

        try:
            self._milvus_retriever = MilvusRetriever()
            return self._milvus_retriever
        except Exception as e:
            logger.warning(f"Milvus 初始化失败: {e}")
            return None

    def retrieve(self, query: str, top_k: int = 3) -> List[RetrievedDoc]:
        query = query.strip()
        if not query:
            return []

        milvus_retriever = self._get_milvus_retriever()
        if not milvus_retriever:
            return []

        try:
            query_vector = self.embedder.embed_query(query)
        except Exception as e:
            logger.error(f"Embedding query failed: {e}")
            return []

        # TODO: 当前只有向量检索；后续补 BM25 / RRF / rerank，真正升级为 Hybrid Retrieval。
        logger.info(f"Searching Milvus for query: {query}")
        docs: List[RetrievedDoc] = milvus_retriever.search(query_vector, top_k)

        if not docs:
            logger.warning("No documents found in Milvus, returning empty results")
            return []

        return docs

```

## File: app\retrieval\milvus_retriever.py

- Extension: .py
- Language: python
- Size: 4300 bytes
- Created: 2026-05-05 15:56:12
- Modified: 2026-05-05 15:56:12

### Code

```python
from typing import List

from pymilvus import DataType, MilvusClient

from app.core.config import settings
from app.core.logger import get_logger
from app.models.response import RetrievedDoc

logger = get_logger(__name__)


class MilvusRetriever:
    def __init__(self):
        self.client = MilvusClient(
            uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
            user=settings.milvus_user or None,
            password=settings.milvus_password or None,
        )
        self.collection_name = settings.milvus_collection
        self._ensure_collection()

    def _ensure_collection(self):
        if self.client.has_collection(self.collection_name):
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=100, is_primary=True)
        schema.add_field(
            field_name="vector",
            datatype=DataType.FLOAT_VECTOR,
            dim=settings.embedding_dimension,
        )
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=4000)
        schema.add_field(field_name="source", datatype=DataType.VARCHAR, max_length=500)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="FLAT",
            metric_type="COSINE",
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        logger.info(f"Created Milvus collection: {self.collection_name}")

    def search(self, query_vector: List[float], top_k: int = 3) -> List[RetrievedDoc]:
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                anns_field="vector",
                search_params={"metric_type": "COSINE", "params": {}},
                limit=top_k,
                output_fields=["text"],
            )

            docs: list[RetrievedDoc] = []
            for hits in results:
                for hit in hits:
                    entity = hit.get("entity", {})
                    docs.append(
                        RetrievedDoc(
                            doc_id=str(hit["id"]),
                            score=float(hit["distance"]),
                            snippet=entity.get("text", ""),
                        )
                    )
            return docs
        except Exception as e:
            logger.error(f"Milvus search failed: {e}")
            return []

    def insert_documents(self, documents: List[dict]):
        try:
            self.client.insert(collection_name=self.collection_name, data=documents)
            logger.info(f"Inserted {len(documents)} documents to Milvus")
        except Exception as e:
            logger.error(f"Failed to insert documents: {e}")

    def health_status(self) -> dict:
        exists = self.client.has_collection(self.collection_name)
        info = {
            "ok": True,
            "host": settings.milvus_host,
            "port": settings.milvus_port,
            "collection": self.collection_name,
            "collection_exists": exists,
        }

        if not exists:
            info["doc_count"] = 0
            return info

        try:
            stats = self.client.get_collection_stats(collection_name=self.collection_name)
            info["stats"] = stats
            info["doc_count"] = int(stats.get("row_count", 0))
        except Exception as e:
            info["stats_error"] = str(e)
            info["doc_count"] = None

        return info

    def sample_documents(self, limit: int = 5) -> list[dict]:
        if not self.client.has_collection(self.collection_name):
            return []

        rows = self.client.query(
            collection_name=self.collection_name,
            filter="id != ''",
            output_fields=["id", "text", "source"],
            limit=limit,
        )
        return [
            {
                "id": row.get("id", ""),
                "text": row.get("text", ""),
                "source": row.get("source", ""),
            }
            for row in rows
        ]

```

## File: app\retrieval\mysql_faq_retriever.py

- Extension: .py
- Language: python
- Size: 3534 bytes
- Created: 2026-05-05 15:55:39
- Modified: 2026-05-05 16:49:28

### Code

```python
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

```

## File: app\router\intent_router.py

- Extension: .py
- Language: python
- Size: 708 bytes
- Created: 2026-05-05 16:52:21
- Modified: 2026-05-05 16:52:21

### Code

```python
from app.models.query import Intent, RetrievalStrategy, RouteDecision


class IntentRouter:
    def route(self, query: str) -> RouteDecision:
        q = query.strip()
        # TODO: 当前仅按长度做最小路由；后续可升级为关键词规则、FAQ 召回分数或小模型分类。
        if len(q) <= 20:
            return RouteDecision(
                intent=Intent.FAQ,
                strategy=RetrievalStrategy.DIRECT_FAQ,
                confidence=0.80,
                direct_answer=None,
            )
        return RouteDecision(
            intent=Intent.KNOWLEDGE,
            strategy=RetrievalStrategy.RAG,
            confidence=0.60,
            direct_answer=None,
        )

```

## File: data\seed\demo_knowledge.jsonl

- Extension: .jsonl
- Language: unknown
- Size: 1540 bytes
- Created: 2026-05-05 16:09:00
- Modified: 2026-05-05 16:09:00

### Code

```unknown
{"id":"rag-intro","source":"seed/rag-intro","text":"RAG 是 Retrieval-Augmented Generation，即检索增强生成。它的基本流程是先根据用户问题从知识库中检索相关片段，再把检索结果交给大模型生成答案。这样可以降低模型幻觉，并让回答更贴近企业私有知识。"}
{"id":"faq-vs-rag","source":"seed/faq-vs-rag","text":"FAQ 更适合固定问题和固定答案，通常使用精确匹配、模糊匹配或规则命中。RAG 更适合开放问题，需要从文档中检索上下文后再生成回答。FAQ 和 RAG 可以组合：先查 FAQ，FAQ 未命中时再回退到 RAG。"}
{"id":"milvus-role","source":"seed/milvus-role","text":"Milvus 是向量数据库，适合存储文档切片的 embedding，并支持相似度检索。在一个最小 RAG 项目里，文档先被切分成 chunk，再经过 embedding 编码写入 Milvus，查询时再用 query embedding 去搜索最相关的 chunk。"}
{"id":"reindex-flow","source":"seed/reindex-flow","text":"最小离线索引流程通常包括四步：加载原始文档、文本切分、生成 embedding、写入向量库。只有完成这条 reindex 链路，在线查询阶段的向量检索才有真实数据可查。"}
{"id":"fallback-answer","source":"seed/fallback-answer","text":"如果系统没有配置真实大模型接口，最小可用做法是返回检索到的文档片段作为 fallback。这样虽然还没有自然语言生成能力，但可以先验证检索链路、召回质量和上下文组织是否正常。"}

```

## File: docker\mysql\init\001_init_faq.sql

- Extension: .sql
- Language: sql
- Size: 816 bytes
- Created: 2026-04-28 17:26:45
- Modified: 2026-04-29 17:58:19

### Code

```sql
﻿SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

USE rag;

CREATE TABLE IF NOT EXISTS faq (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    question VARCHAR(255) NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO faq (question, answer) VALUES
('你是谁', '我是你的 RAG 助手。'),
('系统健康吗', '系统当前健康。'),
('联系方式', '请通过项目仓库提交问题或建议。'),
('你能做什么', '我可以回答问题、提供信息，并结合检索结果生成答案。'),
('什么是RAG', 'RAG（Retrieval-Augmented Generation）是一种结合检索和生成的 AI 技术。'),
('如何使用', '直接输入问题，我会先检索相关信息，再给出回答。');

```

## File: scripts\reindex.py

- Extension: .py
- Language: python
- Size: 2318 bytes
- Created: 2026-04-29 19:27:06
- Modified: 2026-05-05 16:49:42

### Code

```python
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.indexing.embedding_worker import EmbeddingWorker
from app.indexing.loaders import DocumentLoader
from app.indexing.milvus_upsert import MilvusUpserter
from app.indexing.splitter import TextSplitter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="重建 Milvus 文档索引")
    parser.add_argument("input_path", help="输入文件或目录，支持 txt/md/jsonl")
    parser.add_argument("--drop-old", action="store_true", help="重建前删除旧集合")
    parser.add_argument("--chunk-size", type=int, default=settings.chunk_size)
    parser.add_argument("--chunk-overlap", type=int, default=settings.chunk_overlap)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    embedder = EmbeddingWorker()
    loader = DocumentLoader()
    splitter = TextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    upserter = MilvusUpserter()

    documents = loader.load(args.input_path)
    if not documents:
        print("Error: 未找到任何文档。")
        return

    chunks = splitter.split_documents(documents)
    if not chunks:
        print("Error: 文档切分后没有可入库的 chunk。")
        return

    print(f"待处理 Chunks 总数: {len(chunks)}")

    upserter.ensure_collection(drop_old=args.drop_old)

    # TODO: 后续可将 batch_size 提升为命令行参数或配置项，便于按机器资源调优。
    batch_size = 64
    total_inserted = 0

    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        batch_texts = [c.text for c in batch_chunks]

        # TODO: 后续可补充 tqdm / logging，增强大规模重建时的进度可观测性。
        batch_vectors = embedder.embed_texts(batch_texts)
        inserted = upserter.upsert_chunks(batch_chunks, batch_vectors)
        total_inserted += inserted

    print("\n重建完成！")
    print(f"- 原始文档数: {len(documents)}")
    print(f"- 成功写入 Chunk 数: {total_inserted}")
    print(f"- Collection: {settings.milvus_collection}")


if __name__ == "__main__":
    main()

```

## File: scripts\trace_log.py

- Extension: .py
- Language: python
- Size: 1439 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
import argparse
import sys
from pathlib import Path

def trace_request(log_path: str, request_id: str):
    """
    按 request_id 筛选日志行
    """
    log_file = Path(log_path)
    if not log_file.exists():
        print(f"❌ 错误: 日志文件未找到: {log_path}")
        return

    print(f"🔍 正在追踪 Request ID: [{request_id}] ...\n" + "-"*50)
    
    found_count = 0
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # 假设日志格式中包含了 request_id
                if request_id in line:
                    print(line.strip())
                    found_count += 1
        
        if found_count == 0:
            print(f"⚠️ 未找到关联该 ID 的日志条目，请确认 ID 是否正确或日志路径是否匹配。")
        else:
            print("-"*50 + f"\n✅ 扫描结束，共找到 {found_count} 条相关日志。")
            
    except Exception as e:
        print(f"❌ 读取日志时发生错误: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="根据 Request ID 快速定位日志")
    parser.add_argument("req_id", help="需要查询的 request_id")
    parser.add_argument("--file", default="logs/app.log", help="日志文件路径 (默认: logs/app.log)")
    
    args = parser.parse_args()
    trace_request(args.file, args.req_id)
```


```

## File: README.md

- Extension: .md
- Language: markdown
- Size: 1356 bytes
- Created: 2026-04-29 23:27:29
- Modified: 2026-04-29 23:27:29

### Code

```markdown
## 项目目标
基于 FastAPI 的 RAG 问答系统：FAQ 直查 + RAG 回退，采用 MySQL/Milvus/Redis 架构，支持结构化日志与 Prometheus 监控

## 技术栈
* **API Framework**: FastAPI
* **Vector Store**: Milvus
* **Metadata Store**: MySQL
* **Monitoring**: Prometheus
* **Core Design**: Hybrid Retrieval & Intent Routing

## 当前进度 (Day 1)
- [x] 工程骨架搭建
- [x] 日志链路追踪 (RequestID)
- [x] 统一异常处理与指标监控
- [x] 意图路由基础占位
- [x] Mock 主链路联调

## 下一步计划
- [x] 接入 MySQL FAQ 检索
- [x] 接入 Milvus 向量检索
- [x] 实现 RRF 混合重排算法

### 今日任务概述(Day 2)

- 修复 MySQL 连接与 FAQ 初始化环境
- 接入最小真实 RAG 链路
- 抽离离线索引流数据结构

### 关键改动

- 修复 Docker / .env.example / 初始化 SQL / test_sql.py
- 新增 indexing 模块与 scripts/reindex.py
- HybridRetriever 改为真实 embedding 检索
- LLMClient 改为真实调用骨架
- 新增 app/models/document.py
- 修复并重建 Record.md

### 当前结果

- FAQ 链路可用
- MySQL 连接稳定
- reindex 入口可用
- RAG 主链路已从 mock 走向真实实现


### 后续计划

- 解耦 generation 层
- 准备真实文档并完成 reindex
- 验证 /query 的完整 RAG 路径

```

## File: Record.md

- Extension: .md
- Language: markdown
- Size: 22323 bytes
- Created: 2026-04-28 15:59:42
- Modified: 2026-05-05 17:43:03

### Code

```markdown
﻿# Project Record

## Day 1

### [Step 1] 主链路骨架完成

- 时间：2026-04-28
- 目标：先跑通 `/query` 的最小主链路，具备 FAQ 直返和 RAG 回退骨架。
- 变更内容：
  - 搭建 FastAPI 应用入口与基础目录结构。
  - 增加 `/health` 健康检查接口。
  - 增加请求日志中间件，记录 `request_id`、耗时、状态码。
  - 增加指标中间件与统一异常处理。
  - 增加 `IntentRouter`、`HybridRetriever`、`LLMClient` 的最小链路。
- 涉及文件：
  - `app/main.py`
  - `app/api/routes_query.py`
  - `app/router/intent_router.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/generation/llm_client.py`
  - `app/middleware/request_logger.py`
  - `app/middleware/metrics_middleware.py`
  - `app/handlers/error_handler.py`
- 当前结果：
  - `/query` 主链路代码可运行。
  - FAQ 命中可直接返回，未命中可进入 RAG 骨架。
- 验证方式：
  - 本地联调 `/query`
  - 检查日志输出与 `/health`
- 下一步：
  - 拆出 FAQ 检索器，替换硬编码 FAQ。

## Day 2

### [Step 1] 拆分 FAQ 检索职责

- 时间：2026-04-28
- 目标：将 FAQ 问答能力从路由层拆出，形成独立 FAQ 检索器。
- 变更内容：
  - 新增 `MysqlFAQRetriever`，封装 FAQ 查询接口。
  - 新增 `FAQHit` 结构，统一 FAQ 命中结果。
  - 将 `IntentRouter` 从“直接返回 FAQ 内容”调整为“只负责路由判断”。
  - 在 `/query` 主链路中接入 FAQ 检索。
- 涉及文件：
  - `app/retrieval/mysql_faq_retriever.py`
  - `app/router/intent_router.py`
  - `app/api/routes_query.py`
- 当前结果：
  - FAQ 命中逻辑已从路由层剥离。
  - 主链路职责更清晰。
- 验证方式：
  - FAQ 问题优先命中 FAQ 检索器。
  - 非 FAQ 问题继续走 RAG 路径。
- 下一步：
  - 将 FAQ 数据源接到真实 MySQL。

### [Step 2] FAQ 检索器接入 MySQL 查询骨架

- 时间：2026-04-28
- 目标：把 FAQ 检索从 mock 升级成真实数据库访问骨架。
- 变更内容：
  - 在 `config.py` 中增加 MySQL FAQ 相关配置。
  - 将 `MysqlFAQRetriever` 改为访问 MySQL。
  - FAQ 查询策略先采用精确匹配。
- 涉及文件：
  - `app/core/config.py`
  - `app/retrieval/mysql_faq_retriever.py`
- 当前结果：
  - FAQ 数据源已切到 MySQL。
  - 为后续真实 FAQ 维护预留了接口。
- 验证方式：
  - 在 MySQL 中准备 FAQ 测试数据。
  - 请求 FAQ 问题并确认返回数据库结果。
- 下一步：
  - 接入向量检索，补齐 RAG 链路。

### [架构补充] 同步 I/O 策略评估与异步升级计划

- 时间：2026-04-28
- 背景：当前 `/query`、`MysqlFAQRetriever` 先以同步实现满足低并发联调。
- 当前判断：
  - 本地开发与演示阶段，同步实现成本更低。
  - 随着 Milvus 与 LLM 调用接入，外部 I/O 会增加，同步模式会逐渐成为瓶颈。
- 风险点：
  - MySQL 每次请求新建连接，存在重复连接开销。
  - Milvus / LLM 持续用同步调用会影响并发能力。
- 结论：
  - 当前阶段先不强制异步化。
  - 后续真实外部 I/O 接入后，再评估 `async` 改造时机。
- 后续升级项：
  - `/query` 改为 `async def`
  - FAQ / Milvus / LLM 逐步异步化
  - 引入连接复用或连接池

### [环境准备] FAQ MySQL 数据表初始化

- 时间：2026-04-28
- 目标：为 FAQ 检索准备 MySQL 数据源。
- 变更内容：
  - 设计 `rag.faq` 表结构。
  - 准备 FAQ 初始化数据。
- 验证方式：
  - 直接 SQL 查询 `faq` 表。
  - 验证关键 FAQ 问题是否可精确命中。
- 下一步：
  - 完成 Docker 化部署并接通应用访问。

### [环境准备] MySQL Docker Compose 方案

- 时间：2026-04-28
- 目标：通过 Docker Compose 启动 MySQL，并自动初始化 FAQ 数据表。
- 变更内容：
  - 设计 `docker-compose.yml` 中的 MySQL 服务。
  - 暴露宿主机端口供本地 Python 应用访问。
  - 挂载初始化 SQL 目录。
- 配置约定：
  - 数据库：`rag`
  - FAQ 表：`faq`
  - 宿主机连接：`127.0.0.1:3307`
- 下一步：
  - 启动 MySQL 并验证 FAQ 表初始化。

## Day 3

### [Step 3] 接入 Milvus 向量检索

- 时间：2026-04-29
- 目标：将 RAG 链路从 mock 检索升级为真实向量检索。
- 变更内容：
  - 新增 `MilvusRetriever`，封装向量检索能力。
  - 增加 Milvus 相关配置项。
  - 将 `HybridRetriever` 改为调用 `MilvusRetriever`。
- 涉及文件：
  - `app/retrieval/milvus_retriever.py`
  - `app/core/config.py`
  - `app/retrieval/hybrid_retriever.py`
- 当前结果：
  - RAG 检索层具备真实向量检索骨架。
- 验证方式：
  - 启动 Milvus 容器并准备测试数据。
  - 请求非 FAQ 问题，确认能检索到文档。
- 下一步：
  - 完善真实 embedding 与索引链路。

### [环境准备] Milvus Docker Compose 配置

- 时间：2026-04-29
- 目标：为向量检索准备完整 Docker 环境。
- 变更内容：
  - 在 `docker-compose.yml` 中增加 `etcd`、`minio`、`milvus-standalone` 服务。
  - 配置依赖关系、健康检查、端口与数据卷。
- 配置约定：
  - Milvus：`19530`
  - MinIO：`9000 / 9001`
- 下一步：
  - 启动 Milvus 服务栈并验证健康状态。

### [测试验证] Milvus 服务健康性检查

- 时间：2026-04-29
- 目标：确认 Milvus 服务栈可用。
- 变更内容：
  - 通过 Compose 启动服务。
  - 编写 / 执行基础测试脚本验证连接与集合操作。
- 涉及文件：
  - `docker-compose.yml`
  - `test_milvus.py`
- 验证方式：
  - `docker compose ps`
  - `curl http://localhost:9091/healthz`
  - Python 连接测试
- 下一步：
  - 接入真实 embedding 与入库流程。

### [P0-1] 编码链路与 FAQ / Milvus 数据核验脚本

- 时间：2026-04-29
- 目标：定位乱码、FAQ 命中异常、Milvus 数据有效性问题。
- 变更内容：
  - 增加文本链路排查脚本。
  - 增加 FAQ 数据核验脚本。
  - 增加 Milvus 集合核验脚本。
- 涉及文件：
  - `scripts/check_text_chain.py`
  - `scripts/verify_mysql_faq_p0.py`
  - `scripts/verify_milvus_collection_p0.py`
- 当前结果：
  - 能独立判断乱码发生在源文件、入库链路、数据库存储还是日志显示。
- 下一步：
  - 修复 MySQL 字符集链路与脏数据。

### [P0-2] MySQL 字符集链路修正方案

- 时间：2026-04-29
- 目标：修正 FAQ 初始化链路中的字符集不一致问题，避免 UTF-8 中文被错误解释后写入 MySQL。
- 变更内容：
  - 统一应用、MySQL、初始化 SQL 的字符集链路。
  - 调整 `.env` / `docker-compose.yml` / 初始化 SQL 的相关配置。
- 涉及文件：
  - `app/core/config.py`
  - `docker-compose.yml`
  - `.env`
  - `.env.example`
  - `docker/mysql/init/001_init_faq.sql`
- 当前结果：
  - 新导入 FAQ 数据可以稳定按 UTF-8 入库。
- 下一步：
  - 删除旧库数据并重建 FAQ 数据。

### [P0-4] 修复 MySQL 连接环境问题

- 时间：2026-04-29
- 目标：修复 MySQL 容器反复重启、`test_sql.py` 无法连接、FAQ 初始化 SQL 无法正确执行的问题。
- 变更内容：
  - 修复 `.env` / `.env.example` 的格式问题。
  - 修复 `docker-compose.yml` 中 MySQL 容器的环境注入问题。
  - 修复 `docker/mysql/init/001_init_faq.sql` 的编码与 SQL 语法问题。
  - 重写 `test_sql.py`，提供干净的 MySQL 连通性验证。
- 涉及文件：
  - `.env`
  - `.env.example`
  - `docker-compose.yml`
  - `docker/mysql/init/001_init_faq.sql`
  - `test_sql.py`
- 当前结果：
  - MySQL 容器可正常启动。
  - `test_sql.py` 可连接并命中 FAQ 数据。
- 验证方式：
  - `docker compose config`
  - `docker compose down -v`
  - `docker compose up -d mysql`
  - `docker compose logs -f mysql`
  - `python test_sql.py`
- 下一步：
  - 继续推进 P1 的真实检索与生成链路。

### [P1-1] 接入最小真实索引链路与生成链路

- 时间：2026-04-29
- 目标：把随机向量检索与 mock 生成升级为最小可用的真实 RAG 主链路。
- 变更内容：
  - 在 `app/indexing/` 下补齐最小索引层：`loaders.py`、`splitter.py`、`embedding_worker.py`、`milvus_upsert.py`。
  - 新增 `scripts/reindex.py` 作为统一重建入口。
  - 将 `HybridRetriever` 改为真实 embedding 检索。
  - 将 `MilvusRetriever` 统一到配置维度。
  - 将 `LLMClient` 接入真实 OpenAI Responses API，并提供未配置密钥时的明确降级提示。
  - 扩展 embedding / chunk / OpenAI 相关配置。
- 涉及文件：
  - `app/core/config.py`
  - `app/indexing/__init__.py`
  - `app/indexing/loaders.py`
  - `app/indexing/splitter.py`
  - `app/indexing/embedding_worker.py`
  - `app/indexing/milvus_upsert.py`
  - `scripts/reindex.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/retrieval/milvus_retriever.py`
  - `app/generation/llm_client.py`
  - `requirements.txt`
- 当前结果：
  - 已具备最小文档入库链路。
  - 查询链路已升级为真实 embedding 检索。
  - 生成链路具备真实 LLM 接入能力。
- 验证方式：
  - `python scripts/reindex.py <input_path> --drop-old`
  - 配置 `OPENAI_API_KEY` 后请求 `/query`
- 下一步：
  - 准备真实文档并完成一次完整 reindex。

### [P1-2] 抽离离线索引流数据结构

- 时间：2026-04-29
- 目标：让离线索引链路中的文档数据结构从具体实现模块中解耦，形成清晰的内部模型边界。
- 变更内容：
  - 新增 `app/models/document.py`，统一承载 `SourceDocument` 与 `DocumentChunk`。
  - 调整 `app/indexing/loaders.py` 引用 `app.models.document`。
  - 调整 `app/indexing/splitter.py` 引用 `app.models.document`。 //纯字符计数切分
  - 调整 `app/indexing/milvus_upsert.py` 统一依赖 `DocumentChunk`。
- 涉及文件：
  - `app/models/document.py`
  - `app/indexing/loaders.py`
  - `app/indexing/splitter.py`
  - `app/indexing/milvus_upsert.py`
- 当前结果：
  - 在线查询流与离线索引流都具备明确的数据结构承载位置。
  - `schemas` 负责 API 边界，`models` 负责内部对象，`indexing / retrieval / generation` 负责处理逻辑。
- 验证方式：
  - `python -m py_compile app/models/document.py app/indexing/loaders.py app/indexing/splitter.py app/indexing/milvus_upsert.py`
  - `python scripts/reindex.py --help`
- 下一步：
  - 后续按需要扩展更细粒度的索引元数据模型。

## Day 4

### [P1-3] 增加最小管理观测接口，作为 RAG 下一阶段切入口

- 时间：2026-05-05
- 目标：在继续构建 RAG 主链路前，先补齐最小观测能力，明确 FAQ、Milvus、集合数据状态，避免后续开发过程“代码写了但不知道是否真的生效”。
- 变更内容：
  - 新增 `GET /admin/status`，统一暴露应用、FAQ、Milvus 的运行状态。
  - 新增 `GET /admin/milvus/sample`，用于抽样查看 Milvus 中的文档内容。
  - 为 `MysqlFAQRetriever` 增加 `health_status()`，返回 MySQL 连通性、FAQ 表存在性和 FAQ 数量。
  - 为 `MilvusRetriever` 增加 `health_status()`，返回 collection 状态和文档数量。
  - 为 `MilvusRetriever` 增加 `sample_documents()`，支持抽样查看当前集合中的 `id/text/source`。
  - 在 `app/main.py` 中挂载 `admin_router`。
- 涉及文件：
  - `app/main.py`
  - `app/api/routes_admin.py`
  - `app/retrieval/mysql_faq_retriever.py`
  - `app/retrieval/milvus_retriever.py`
- 当前结果：
  - `/admin/status` 已可返回当前系统关键状态。
  - FAQ 链路状态明确：MySQL 正常、FAQ 表存在、FAQ 数量为 `6`。
  - Milvus 链路状态明确：`rag_docs` collection 已存在，但 `row_count = 0`，当前还没有正式文档入库。
  - 这说明 FAQ 已经跑通，但最小 RAG 主链路还卡在“知识库数据尚未完成入库”这一层。
- 当前状态快照：
  - `/admin/status` 返回：
    ```json
    {
      "app_name": "rag-project",
      "app_env": "dev",
      "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
      "mysql": {
        "ok": true,
        "host": "127.0.0.1",
        "port": 3307,
        "database": "rag",
        "table": "faq",
        "table_exists": true,
        "faq_count": 6
      },
      "milvus": {
        "ok": true,
        "host": "127.0.0.1",
        "port": 19530,
        "collection": "rag_docs",
        "collection_exists": true,
        "stats": {
          "row_count": 0
        },
        "doc_count": 0
      }
    }
    ```
- 验证方式：
  - 请求 `GET /admin/status`
  - 请求 `GET /admin/milvus/sample`
  - 检查返回中的 `faq_count`、`collection_exists`、`row_count`
- 下一步：
  - 准备最小测试文档并执行一次 `python scripts/reindex.py <input_path> --drop-old`
  - 先把 Milvus 中的 `row_count` 从 `0` 推进到“大于 0”
  - 然后再继续验证 `/query` 的向量检索链路

### [P1-4] 打通最小 RAG 闭环：本地 embedding 降级 + 种子数据入库 + 查询降级返回

- 时间：2026-05-05
- 目标：在不依赖外部模型下载、也不依赖真实 LLM 联网可用的前提下，先把最小 RAG 闭环打通。
- 变更内容：
  - 重写 `EmbeddingWorker`，增加本地降级 embedding：
    - 优先尝试本地缓存的 `SentenceTransformer`
    - 若本地模型不可用，则自动退化为纯本地哈希向量
  - 将 `SentenceTransformer` 调整为 `local_files_only=True`，避免请求时卡在 HuggingFace 下载重试。
  - 调整 `HybridRetriever`，对 query embedding 失败增加兜底保护，避免直接抛异常。
  - 修复 `MilvusUpserter`，在写入后补 `flush`，保证 `row_count` 能正确反映入库数量。
  - 新增 `data/seed/demo_knowledge.jsonl`，提供最小测试知识库数据。
  - 重写 `LLMClient`：
    - 当未配置可用 LLM 时，直接返回检索片段
    - 当 LLM 调用失败时，不再返回 500，而是降级返回检索片段
- 涉及文件：
  - `app/indexing/embedding_worker.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/indexing/milvus_upsert.py`
  - `app/generation/llm_client.py`
  - `data/seed/demo_knowledge.jsonl`
- 当前结果：
  - 已成功执行 `python scripts/reindex.py data/seed --drop-old`
  - 种子知识库成功写入 Milvus
  - `rag_docs` 当前 `row_count = 5`
  - 非 FAQ 问题已能走到 Milvus 检索
  - 即使 OpenAI 调用失败，`/query` 也会以 200 正常返回检索片段，不再直接报 500
- 验证方式：
  - `python scripts/reindex.py data/seed --drop-old`
  - 检查 `GET /admin/status` 中 `milvus.stats.row_count == 5`
  - 检查 `GET /admin/milvus/sample`
  - 使用非 FAQ 问题请求 `/query`，确认返回 `source = "rag"` 且带 `retrieved_docs`
- 验证结果：
  - 重建输出：
    - `加载文档数: 5`
    - `切分后 chunk 数: 5`
    - `已写入 Milvus chunk 数: 5`
  - Milvus 状态：
    - `collection_exists = true`
    - `row_count = 5`
    - `doc_count = 5`
  - `/query` 非 FAQ 验证：
    - 请求：`RAG为什么要先检索再生成答案`
    - 返回：HTTP `200`
    - 路由：`rag`
    - 结果：成功返回检索片段 fallback
- 下一步：
  - 用真实业务文档替换 `data/seed/demo_knowledge.jsonl`
  - 再做一次正式 reindex
  - 然后开始优化 FAQ 路由规则和检索效果

### [P1-5] 为后续优化点补充 TODO 注释

- 时间：2026-05-05
- 目标：把已经识别出的后续优化方向直接标在代码里，方便后续按模块逐步学习和逐步优化，避免遗忘。
- 变更内容：
  - 在 `MysqlFAQRetriever` 中补充 TODO：
    - 后续评估接入 MySQL 连接池
    - 后续把 FAQ 精确匹配升级为模糊匹配、全文检索或 FAQ 向量检索
  - 在 `scripts/reindex.py` 中补充 TODO：
    - 后续将 `batch_size` 做成参数或配置项
    - 后续增加 `tqdm / logging` 提升重建过程可观测性
  - 在 `MilvusUpserter` 中补充 TODO：
    - 当前每批写入后立即 `flush`
    - 后续可改为全部写完后统一 `flush` 提升性能
  - 在 `HybridRetriever` 中补充 TODO：
    - 后续补 BM25 / RRF / rerank，真正升级为 Hybrid Retrieval
  - 在 `LLMClient` 中补充 TODO：
    - 后续把 prompt 构造拆到 `prompt_builder`
    - 后续补更细的错误分类、重试和超时控制
  - 在 `IntentRouter` 中补充 TODO：
    - 当前仅按长度路由
    - 后续升级为关键词规则、FAQ 分数或小模型分类
- 涉及文件：
  - `app/retrieval/mysql_faq_retriever.py`
  - `scripts/reindex.py`
  - `app/indexing/milvus_upsert.py`
  - `app/retrieval/hybrid_retriever.py`
  - `app/generation/llm_client.py`
  - `app/router/intent_router.py`
- 当前结果：
  - 代码中已经明确标出后续优化切入点。
  - 后续可以按模块逐个学习，而不用一次记住全部优化方向。
- 验证方式：
  - 直接查看上述文件中的 `TODO` 注释
  - 执行基础语法检查，确认仅补注释未引入新问题
- 下一步：
  - 按模块逐个消化 TODO
  - 优先从 `scripts/reindex.py` 和 `app/indexing/milvus_upsert.py` 开始学习离线入库链路

### [P1-6] 修正 Milvus 查询层职责边界，移除自动建空集合行为

- 时间：2026-05-05
- 目标：避免在线查询模块在 collection 缺失时悄悄创建空集合，导致“索引缺失”被伪装成“检索无结果”。
- 变更内容：
  - 移除 `MilvusRetriever.__init__()` 中的自动建集合逻辑。
  - 删除查询层中的 `_ensure_collection()` 行为。
  - 新增 `_require_collection()`，在查询前强制检查 collection 是否存在。
  - 当 collection 不存在时，直接抛出明确错误：
    - `Milvus collection '<name>' 不存在，请先执行 reindex 初始化知识库。`
- 涉及文件：
  - `app/retrieval/milvus_retriever.py`
- 当前结果：
  - 查询模块不再具备“创建空集合”的能力。
  - collection 丢失时，问题会被立即暴露，而不是继续返回空结果。
  - Milvus 的职责边界更清晰：
    - 查询层只负责查
    - 建集合仍由离线入库链路负责
- 验证方式：
  - 查看 `app/retrieval/milvus_retriever.py`
  - 语法检查：
    - `python -m py_compile app/retrieval/milvus_retriever.py`
- 下一步：
  - 后续继续学习离线入库链路与查询链路的职责边界
  - 保持“在线查询不做初始化、离线链路负责准备资源”的原则

### [P1-7] 拆分 generation 层职责：prompt / postprocess / client

- 时间：2026-05-05
- 目标：把 `LLMClient` 中混在一起的 prompt 构造、答案包装、模型调用职责拆开，按 `generation/` 目录结构落地。
- 变更内容：
  - 实现 `app/generation/prompt_builder.py`
    - 新增 `build_context()`
    - 新增 `build_prompt()`
    - 负责把 `query + docs` 组装成 `instructions` 和 `input`
  - 实现 `app/generation/answer_postprocess.py`
    - 新增 `build_citations()`
    - 新增无上下文、无 LLM、LLM 成功、LLM 失败四类标准答案构造函数
  - 重写 `app/generation/llm_client.py`
    - `LLMClient` 只负责 client 初始化与模型调用
    - 调用 `prompt_builder` 构造 prompt
    - 调用 `answer_postprocess` 统一返回 `GeneratedAnswer`
  - 保持 `routes_query.py` 的调用方式不变，仍然使用：
    - `ans = llm.generator(req.query, docs)`
- 涉及文件：
  - `app/generation/prompt_builder.py`
  - `app/generation/answer_postprocess.py`
  - `app/generation/llm_client.py`
- 当前结果：
  - generation 层职责边界更清晰：
    - `prompt_builder` 负责 prompt
    - `llm_client` 负责调用
    - `answer_postprocess` 负责标准化输出
  - 上层查询接口无需改调用方式
  - LLM 失败时仍可正常降级返回检索片段
- 验证方式：
  - 语法检查：
    - `python -m py_compile app/generation/prompt_builder.py app/generation/answer_postprocess.py app/generation/llm_client.py`
  - 最小调用验证：
    - 构造 `RetrievedDoc`
    - 调用 `LLMClient().generator(...)`
    - 确认可返回 `GeneratedAnswer`
- 下一步：
  - 后续继续细化 `prompt_builder`
  - 再按需要补 `answer_postprocess` 的引用整理与输出清洗

### [P1-8] 修正 answer_postprocess 职责，落实为真正的“结果后处理”

- 时间：2026-05-05
- 目标：让 `answer_postprocess.py` 从“答案装配器”回归为真正的后处理模块，负责清洗文本、整理引用、处理空答案和统一 fallback。
- 变更内容：
  - 重写 `app/generation/answer_postprocess.py`
    - 新增 `normalize_citations()`：去空、去重、清理 `doc_id`
    - 新增 `clean_answer_text()`：统一换行、去掉多余空行、清理空白
    - 新增 `postprocess_no_context()`：处理无检索结果场景
    - 新增 `postprocess_no_llm()`：处理无可用 LLM 场景
    - 新增 `postprocess_llm_success()`：处理正常生成结果，并对空答案做二次兜底
    - 新增 `postprocess_llm_error()`：处理 LLM 调用失败场景
  - 调整 `app/generation/llm_client.py`
    - 不再自己构造各种答案对象
    - 统一调用 `answer_postprocess` 返回 `GeneratedAnswer`
  - 微调 `app/generation/prompt_builder.py`
    - 在上下文展示时对 `doc_id` 做 `strip()`，避免 fallback 文本里出现脏引用
- 涉及文件：
  - `app/generation/answer_postprocess.py`
  - `app/generation/llm_client.py`
  - `app/generation/prompt_builder.py`
- 当前结果：
  - `answer_postprocess.py` 的职责更贴合命名本身。
  - generation 层边界进一步清晰：
    - `prompt_builder` 负责组织输入
    - `llm_client` 负责模型调用
    - `answer_postprocess` 负责结果规范化
  - 空答案、脏 citation、LLM 失败 fallback 都有统一落点。
- 验证方式：
  - `python -m py_compile app/generation/answer_postprocess.py app/generation/llm_client.py app/generation/prompt_builder.py`
  - 构造最小 `RetrievedDoc`，调用 `LLMClient().generator(...)`
  - 检查：
    - `citations` 是否去重并去空白
    - fallback 文本中的 `doc_id` 是否已清理
- 下一步：
  - 后续继续增强 `answer_postprocess`
  - 再视需要补输出长度控制、引用展示格式和答案质量校验

```

## File: requirements.txt

- Extension: .txt
- Language: plaintext
- Size: 262 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-29 19:27:06

### Code

```plaintext
﻿# Web Framework
fastapi==0.115.0
uvicorn[standard]==0.30.6
prometheus-client==0.20.0

# Data Validation
pydantic==2.9.0
pydantic-settings==2.5.0

# Config
pyyaml==6.0.2

# Logging
structlog==24.4.0

PyMySQL
pymilvus
numpy

openai
httpx
sentence-transformers

```

## File: roadmap.md

- Extension: .md
- Language: markdown
- Size: 2391 bytes
- Created: 2026-04-29 23:14:31
- Modified: 2026-04-29 23:14:31

### Code

```markdown
rag_project/
├─ app/
│    ├─ main.py  ✅应用入口与装配层    
      初始化日志；注册中间件（请求日志、指标采集）；注册全局异常处理；挂载 /metrics；提供 /health 健康检查。
│    ├─ api/  
│    │  ├─ routes_query.py
│    │  ├─ routes_admin.py
│    │  └─ schemas.py

│    ├─ core/    ✅
│    │  ├─ config.py    #统一配置源
│    │  ├─ logger.py    #统一日志格式与输出通道
         通过 RequestIdFilter 给日志补 request_id；配置 console + file 双输出；格式统一；可接管 uvicorn 日志写入同一文件。
│    │  └─ metrics.py   #指标定义层

│    ├─ middleware/  ✅
│    │  ├─ request_context.py
│    │  ├─ request_logger.py    #请求日志中间件
│    │  └─ metrics_middleware.py    #请求指标中间件

│    ├─ handlers/   ✅
│    │  └─ error_handler.py     #统一异常出口

│    ├─ models/
│    │  ├─ document.py
│    │  ├─ query.py
│    │  └─ response.py

│    ├─ router/
│    │  ├─ intent_router.py
│    │  └─ threshold_policy.py

│    ├─ retrieval/
│    │  ├─ mysql_faq_retriever.py
│    │  ├─ bm25_retriever.py
│    │  ├─ milvus_retriever.py
│    │  ├─ hybrid_retriever.py
│    │  └─ reranker.py

│    ├─ generation/
│    │  ├─ prompt_builder.py
│    │  ├─ llm_client.py
│    │  └─ answer_postprocess.py

│    ├─ indexing/
│    │  ├─ loaders.py
│    │  ├─ splitter.py
│    │  ├─ embedding_worker.py
│    │  └─ milvus_upsert.py

│    ├─ cache/
│    │  ├─ redis_cache.py
│    │  └─ cache_keys.py

│    ├─ eval/
│    │  ├─ dataset.py
│    │  ├─ offline_eval.py
│    │  └─ online_eval.py

│    └─ tests/
│       ├─ test_api.py
│       ├─ test_router.py
│       ├─ test_retrieval.py
│       └─ test_generation.py

├─ scripts/
│  ├─ reindex.py
│  ├─ warmup_cache.py
│  └─ replay_logs.py

├─ configs/
│  ├─ config.dev.yaml
│  ├─ config.prod.yaml
│  └─ prompts.yaml

├─ requirements.txt

└─ README.md

```

## File: test_milvus.py

- Extension: .py
- Language: python
- Size: 3498 bytes
- Created: 2026-04-29 11:51:44
- Modified: 2026-04-29 11:52:27

### Code

```python
#!/usr/bin/env python3
"""
Milvus服务健康性测试脚本
测试Milvus连接、集合创建、文档插入和向量搜索功能
"""

import sys
import time
from pymilvus import MilvusClient, DataType
import numpy as np

def test_milvus_health():
    """测试Milvus服务健康性"""
    print("🔍 开始测试Milvus服务健康性...")

    try:
        # 连接Milvus
        client = MilvusClient(uri="http://127.0.0.1:19530")
        print("✅ 成功连接到Milvus")

        # 测试集合操作
        collection_name = "test_collection"

        # 删除已存在的测试集合
        if client.has_collection(collection_name):
            client.drop_collection(collection_name)
            print(f"🗑️ 删除已存在的测试集合: {collection_name}")

        # 创建测试集合
        schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=100, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=768)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=2000)

        index_params = client.prepare_index_params()
        index_params.add_index(field_name="vector", index_type="FLAT", metric_type="COSINE")

        client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params
        )
        print(f"✅ 成功创建测试集合: {collection_name}")

        # 插入测试数据
        test_docs = [
            {
                "id": "doc1",
                "vector": np.random.rand(768).tolist(),
                "text": "这是一个测试文档，关于人工智能和机器学习。"
            },
            {
                "id": "doc2",
                "vector": np.random.rand(768).tolist(),
                "text": "另一个测试文档，讨论自然语言处理技术。"
            },
            {
                "id": "doc3",
                "vector": np.random.rand(768).tolist(),
                "text": "第三个测试文档，涉及向量数据库和检索系统。"
            }
        ]

        client.insert(collection_name=collection_name, data=test_docs)
        print(f"✅ 成功插入 {len(test_docs)} 条测试文档")

        # 等待索引构建
        time.sleep(2)

        # 测试向量搜索
        query_vector = np.random.rand(768).tolist()
        search_results = client.search(
            collection_name=collection_name,
            data=[query_vector],
            anns_field="vector",
            search_params={"metric_type": "COSINE", "params": {}},
            limit=3,
            output_fields=["text"]
        )

        print(f"✅ 向量搜索成功，返回 {len(search_results[0])} 条结果")
        for i, hit in enumerate(search_results[0]):
            print(f"  结果{i+1}: ID={hit['id']}, 相似度={hit['distance']:.4f}")

        # 清理测试集合
        client.drop_collection(collection_name)
        print(f"🧹 清理测试集合: {collection_name}")

        print("\n🎉 Milvus服务健康性测试全部通过！")
        return True

    except Exception as e:
        print(f"❌ Milvus测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_milvus_health()
    sys.exit(0 if success else 1)
```

## File: test_sql.py

- Extension: .py
- Language: python
- Size: 3474 bytes
- Created: 2026-04-28 22:36:51
- Modified: 2026-05-05 15:09:23

### Code

```python
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

```

## File: verify_milvus_collection_p0.py

- Extension: .py
- Language: python
- Size: 3037 bytes
- Created: 2026-04-29 23:27:29
- Modified: 2026-05-05 15:09:23

### Code

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pymilvus import MilvusClient  # noqa: E402
from app.core.config import settings  # noqa: E402

SUSPECT_GARBLED_PATTERNS = [
    "浣", "鎴", "绯", "鍚", "妫", "璇", "鐨", "銆", "锛", "锟", "�"
]


def has_garbled_text(text: str) -> bool:
    if not text:
        return False
    return any(token in text for token in SUSPECT_GARBLED_PATTERNS)


def short_text(text: str, limit: int = 160) -> str:
    text = (text or "").replace("\n", "\\n")
    return text if len(text) <= limit else text[:limit] + "..."


def main():
    print("=" * 80)
    print("P0-3 Milvus 集合核验")
    print("=" * 80)

    client = MilvusClient(
        uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
        user=settings.milvus_user or None,
        password=settings.milvus_password or None,
    )

    collection_name = settings.milvus_collection
    print(f"目标集合: {collection_name}")

    exists = client.has_collection(collection_name)
    print(f"集合存在: {exists}")

    if not exists:
        print("结论: 业务集合还没准备好，当前 RAG 检索不成立。")
        return

    try:
        stats = client.get_collection_stats(collection_name=collection_name)
        print(f"集合统计: {stats}")
    except Exception as e:
        print(f"读取集合统计失败: {e}")

    print("\n尝试抽样查询 text 字段...")
    try:
        rows = client.query(
            collection_name=collection_name,
            filter="id != ''",
            output_fields=["id", "text"],
            limit=10,
        )
    except Exception as e:
        print(f"抽样查询失败: {e}")
        return

    if not rows:
        print("集合存在，但没有可读样本，基本等于没数据。")
        return

    normal_count = 0
    garbled_count = 0
    empty_count = 0

    for idx, row in enumerate(rows, start=1):
        doc_id = row.get("id", "")
        text = row.get("text", "")

        if not text:
            empty_count += 1
            flag = "空文本"
        elif has_garbled_text(text):
            garbled_count += 1
            flag = "疑似乱码"
        else:
            normal_count += 1
            flag = "正常"

        print(f"[{idx}] id={doc_id} | {flag} | text={short_text(text)}")

    print("\n统计:")
    print(f"正常样本: {normal_count}")
    print(f"疑似乱码样本: {garbled_count}")
    print(f"空文本样本: {empty_count}")

    if garbled_count > 0:
        print("结论: Milvus 内部 text 字段存在乱码风险。")
    elif normal_count > 0:
        print("结论: Milvus 至少有部分文本样本是正常的。")
    else:
        print("结论: 当前集合数据质量可疑。")


if __name__ == "__main__":
    main()

```

## File: verify_mysql_faq_p0.py

- Extension: .py
- Language: python
- Size: 2655 bytes
- Created: 2026-04-29 23:27:29
- Modified: 2026-05-05 15:09:23

### Code

```python
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

```

## File: 项目问题清单.md

- Extension: .md
- Language: markdown
- Size: 5129 bytes
- Created: 2026-05-05 15:49:53
- Modified: 2026-05-05 15:49:53

### Code

```markdown
# 项目问题清单

## 当前结论

当前项目已经有基础骨架，但本质上还是一个 **最小可用原型**：

- 在线问答主链路已具备雏形
- FAQ / 向量检索 / LLM 生成已经串起来了
- 但还不是完整的 Hybrid RAG
- 当前最重要目标不是“继续加功能”，而是 **先把整体稳定跑通**

---

## P0：必须先解决的问题

### 1. Embedding 模型在线加载不稳定

现象：

- `EmbeddingWorker` 在请求时动态加载 `SentenceTransformer`
- 如果本地没有缓存好，会在查询时触发模型下载
- 现有日志里已经出现加载失败，导致 `/query` 直接报错

影响：

- 主链路不稳定
- 用户第一次调用就可能失败

建议：

- 先保证 embedding 模型本地可用
- 不要把“首次下载模型”放在在线请求里
- 最好改成“启动前准备好”或“reindex 前准备好”

---

### 2. `HybridRetriever` 名字和真实能力不一致

现状：

- 当前只有 Milvus 向量检索
- 没有 BM25
- 没有 RRF
- 没有 rerank

影响：

- 容易误判项目完成度
- 后续排查问题时会混淆真实瓶颈

建议：

- 短期先承认事实：当前就是“向量检索版 RAG”
- 等主链路稳定后，再逐步补 BM25 / RRF / rerank

---

### 3. README 与代码真实状态不一致

现状：

- README 写了 Redis
- README 写了已实现 RRF 混合重排
- 但代码里没有对应实现

影响：

- 容易误导自己和后续维护者

建议：

- 后续统一文档口径
- 文档只写“已经落地”的能力

---

### 4. FAQ 检索能力过弱

现状：

- MySQL FAQ 走的是 `question = %s` 精确匹配

影响：

- 只有完全一样的问题才能命中
- 稍微换种问法就失败

建议：

- 短期先保留精确匹配，先保证能跑
- 跑通后再升级成模糊匹配 / 全文检索 / FAQ embedding 检索

---

### 5. 在线查询承担了过多初始化责任

现状：

- 查询时才初始化 embedding 模型
- 查询时才初始化 MilvusRetriever
- MilvusRetriever 内部还会检查/创建 collection

影响：

- 首次请求慢
- 请求期行为不稳定
- 排查困难

建议：

- 在线查询只做“查询”
- 初始化、建 collection、建索引，尽量放到离线阶段

---

## P1：跑通后优先优化的问题

### 6. IntentRouter 规则过于粗糙

现状：

- 仅按 `query` 长度判断 FAQ / RAG

影响：

- 路由误判概率高

建议：

- 先保持简单规则
- 后续再增加关键词规则、置信度规则，或者小模型分类

---

### 7. 文本切分过于原始

现状：

- 当前是固定长度字符切分

影响：

- 容易切断语义
- 影响召回质量

建议：

- 跑通后再升级为按段落 / 标题 / 语义边界切分

---

### 8. 检索结果元数据不足

现状：

- 当前只保留 `doc_id / score / snippet`

影响：

- citation 弱
- 不利于定位来源

建议：

- 后续补 `source / title / section / page / chunk_index`

---

### 9. MySQL 每次请求新建连接

现状：

- FAQ 查询每次都直接 `pymysql.connect`

影响：

- 延迟增加
- 并发能力差

建议：

- 跑通后再改连接池

---

### 10. generation 层职责还没拆干净

现状：

- `prompt_builder.py` 还是空壳
- `answer_postprocess.py` 还是占位
- `LLMClient` 同时承担 prompt / 调用 / fallback

影响：

- 不利于后续替换模型和调 prompt

建议：

- 后续拆成：
  - prompt 构造
  - LLM 调用
  - 回答后处理

---

## P2：后续增强项

### 11. 增加 BM25 检索

目标：

- 补上关键词召回

---

### 12. 增加 RRF 融合

目标：

- 融合 FAQ / BM25 / 向量结果

---

### 13. 增加 rerank

目标：

- 对 topN 候选做二次排序

---

### 14. 增加缓存层

目标：

- 如果后续确实需要 Redis，再引入
- 不建议现在为了“架构完整”提前上 Redis

---

### 15. 增加管理与运维能力

目标：

- reindex 管理入口
- collection 状态检查
- FAQ 数据管理

---

## 建议推进顺序

### 阶段 1：先把整体跑通

目标：

- `/health` 正常
- `/query` 至少能稳定返回
- FAQ 可查
- Milvus 可查
- LLM 未配置时也能 fallback

先做：

1. 固定 embedding 模型加载方式
2. 确保 MySQL / Milvus / FastAPI 配置正确
3. 准备一小批真实测试文档
4. 跑通 `scripts/reindex.py`
5. 跑通 `/query`

---

### 阶段 2：把链路做稳定

目标：

- 首次请求不炸
- 检索失败可控
- 错误更容易定位

再做：

1. 减少在线初始化
2. 补更清晰的启动检查
3. 清理 README 与真实状态不一致问题

---

### 阶段 3：开始做效果优化

目标：

- 提升召回质量
- 提升回答质量

再做：

1. FAQ 检索增强
2. 文本切分优化
3. 补元数据
4. prompt_builder 落地

---

### 阶段 4：再升级成真正的 Hybrid RAG

目标：

- 关键词召回 + 向量召回 + 融合重排

最后做：

1. BM25
2. RRF
3. rerank
4. 缓存层

---

## 最终原则

先做：

- 能跑
- 稳定
- 可排查

再做：

- 更准
- 更快
- 更完整

不要一开始就把系统做复杂。

```

## File: app\main.py

- Extension: .py
- Language: python
- Size: 1400 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-05-05 15:56:32

### Code

```python
from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.core.config import settings
from app.core.logger import setup_logger

from app.handlers.error_handler import register_exception_handlers
from app.middleware.metrics_middleware import MetricsMiddleware
from app.middleware.request_logger import RequestLoggerMiddleware
from app.api.routes_admin import router as admin_router
from app.api.routes_query import router as query_router

# 注册了哪些中间件？挂了哪些路由？异常处理在哪接入？

def create_app() -> FastAPI:

    setup_logger()

    app = FastAPI(title=settings.app_name,debug=settings.debug)
    @app.middleware("http")
    async def ensure_utf8_json(request, call_next):
        resp = await call_next(request)
        ct = resp.headers.get("content-type", "")
        if ct.startswith("application/json") and "charset" not in ct:
            resp.headers["content-type"] = "application/json; charset=utf-8"
        return resp

    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(MetricsMiddleware)

    register_exception_handlers(app)
    app.mount("/metrics", make_asgi_app())

    @app.get("/health")
    def health():
        return {"status": "ok", "env": settings.app_env}

    return app

app = create_app()
app.include_router(admin_router)
app.include_router(query_router)

```

## File: app\__init__.py

- Extension: .py
- Language: python
- Size: 0 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

```

## File: app\api\routes_admin.py

- Extension: .py
- Language: python
- Size: 1174 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-05-05 15:56:24

### Code

```python
from fastapi import APIRouter

from app.core.config import settings
from app.retrieval.milvus_retriever import MilvusRetriever
from app.retrieval.mysql_faq_retriever import MysqlFAQRetriever

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status")
def admin_status():
    result = {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "embedding_model": settings.embedding_model,
        "mysql": {"ok": False},
        "milvus": {"ok": False},
    }

    try:
        result["mysql"] = MysqlFAQRetriever().health_status()
    except Exception as e:
        result["mysql"] = {
            "ok": False,
            "error": str(e),
        }

    try:
        result["milvus"] = MilvusRetriever().health_status()
    except Exception as e:
        result["milvus"] = {
            "ok": False,
            "error": str(e),
        }

    return result


@router.get("/milvus/sample")
def milvus_sample(limit: int = 5):
    retriever = MilvusRetriever()
    return {
        "collection": settings.milvus_collection,
        "limit": limit,
        "items": retriever.sample_documents(limit=max(1, min(limit, 20))),
    }

```

## File: app\api\routes_query.py

- Extension: .py
- Language: python
- Size: 1981 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-05-05 15:10:53

### Code

```python
from fastapi import APIRouter, Request

from app.api.schemas import QueryRequest, QueryResponse, DocItem
from app.router.intent_router import IntentRouter
from app.models.query import RetrievalStrategy
from app.retrieval.hybrid_retriever import HybridRetriever
from app.generation.llm_client import LLMClient
from app.retrieval.mysql_faq_retriever import MysqlFAQRetriever
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["query"])

intent_router = IntentRouter()
faq_retriever = MysqlFAQRetriever()
llm = LLMClient()

retriever = HybridRetriever()


@router.post("/query", response_model=QueryResponse)
def query_api(req: QueryRequest, request: Request):
    
    trace_id = getattr(request.state, "request_id", "-")
    decision = intent_router.route(req.query)

    logger.info(f"[{trace_id}] Query: {req.query} | Route Strategy: {decision.strategy}")

    if decision.strategy == RetrievalStrategy.DIRECT_FAQ:
        faq_hit = faq_retriever.retrieve(req.query)
        if faq_hit:
            return QueryResponse(
                trace_id=trace_id,
                query=req.query,
                answer=faq_hit.answer,
                source="faq",
                route=decision.strategy.value,
                confidence=faq_hit.score,
                citations=[faq_hit.faq_id],
                retrieved_docs=[],
            )

    docs = retriever.retrieve(req.query, req.top_k)

    ans = llm.generator(req.query, docs)

    return QueryResponse(
        trace_id=trace_id,
        query=req.query,
        answer=ans.text,
        source="rag",
        route=RetrievalStrategy.RAG.value,
        confidence=decision.confidence,
        citations=ans.citations,
        retrieved_docs=[
            DocItem(
                doc_id=d.doc_id, 
                score=float(d.score), 
                snippet=d.snippet
            )for d in docs 
        ],
    )

```

## File: app\api\schemas.py

- Extension: .py
- Language: python
- Size: 525 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(3, ge=1, le=10)


class DocItem(BaseModel):
    doc_id: str
    score: float
    snippet: str


class QueryResponse(BaseModel):
    trace_id: str
    query: str
    answer: str
    source: str
    route: str
    confidence: float
    citations: list[str] = Field(default_factory=list)
    retrieved_docs: list[DocItem] = Field(default_factory=list)

```

## File: app\api\__init__.py

- Extension: .py
- Language: python
- Size: 0 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

```

## File: app\core\config.py

- Extension: .py
- Language: python
- Size: 2121 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-05-05 15:09:23

### Code

```python
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = Field(default="rag-project", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=False, alias="DEBUG")

    mysql_host: str = Field(..., alias="MYSQL_HOST")
    mysql_port: int = Field(..., alias="MYSQL_PORT")
    mysql_user: str = Field(..., alias="MYSQL_USER")
    mysql_password: str = Field(..., alias="MYSQL_PASSWORD")
    mysql_database: str = Field(..., alias="MYSQL_DATABASE")
    mysql_faq_table: str = Field(default="faq", alias="MYSQL_FAQ_TABLE")

    milvus_host: str = Field(default="127.0.0.1", alias="MILVUS_HOST")
    milvus_port: int = Field(default=19530, alias="MILVUS_PORT")
    milvus_collection: str = Field(default="rag_docs", alias="MILVUS_COLLECTION")
    milvus_user: str = Field(default="", alias="MILVUS_USER")
    milvus_password: str = Field(default="", alias="MILVUS_PASSWORD")

    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        alias="EMBEDDING_MODEL",
    )
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")
    chunk_size: int = Field(default=500, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=80, alias="CHUNK_OVERLAP")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    openai_max_output_tokens: int = Field(default=800, alias="OPENAI_MAX_OUTPUT_TOKENS")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


settings = Settings()

```

## File: app\core\logger.py

- Extension: .py
- Language: python
- Size: 2057 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
import logging
from logging.config import dictConfig
from pathlib import Path
from app.core.config import settings


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def setup_logger() -> None:
    log_dir = getattr(settings, "log_dir", "logs")
    log_file = getattr(settings, "log_file", "app.log")
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_id_filter": {"()": RequestIdFilter}
            },
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(request_id)s | %(name)s | %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "filters": ["request_id_filter"],
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": str(Path(log_dir) / log_file),
                    "maxBytes": 10 * 1024 * 1024,
                    "backupCount": 5,
                    "formatter": "standard",
                    "filters": ["request_id_filter"],
                    "encoding": "utf-8",
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": settings.log_level.upper(),
            },
        }
    )

    # 让 uvicorn 日志走 root，统一进入文件
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

```

## File: app\core\metrics.py

- Extension: .py
- Language: python
- Size: 673 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from prometheus_client import Counter,Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "HTTP 请求总数",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP 请求耗时(秒)",
    ["method", "path"],
)

def record_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        path=path,
        status_code=str(status_code),
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method,
        path=path,
    ).observe(duration_seconds)
```

## File: app\generation\answer_postprocess.py

- Extension: .py
- Language: python
- Size: 2395 bytes
- Created: 2026-05-05 17:38:31
- Modified: 2026-05-05 17:38:31

### Code

```python
from app.models.response import GeneratedAnswer, RetrievedDoc


def normalize_citations(docs: list[RetrievedDoc]) -> list[str]:
    citations: list[str] = []
    seen: set[str] = set()

    for doc in docs:
        doc_id = doc.doc_id.strip()
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        citations.append(doc_id)

    return citations


def clean_answer_text(text: str | None) -> str:
    raw = (text or "").replace("\r\n", "\n").strip()
    if not raw:
        return ""

    lines = [line.strip() for line in raw.split("\n")]
    cleaned_lines: list[str] = []
    prev_blank = False

    for line in lines:
        if not line:
            if prev_blank:
                continue
            cleaned_lines.append("")
            prev_blank = True
            continue

        cleaned_lines.append(line)
        prev_blank = False

    return "\n".join(cleaned_lines).strip()


def postprocess_no_context(docs: list[RetrievedDoc]) -> GeneratedAnswer:
    return GeneratedAnswer(
        text="未检索到相关资料，暂时无法基于知识库回答这个问题。",
        citations=normalize_citations(docs),
        model="no-context",
    )


def postprocess_no_llm(docs: list[RetrievedDoc], context: str) -> GeneratedAnswer:
    return GeneratedAnswer(
        text="未配置可用的 LLM，当前返回检索到的资料片段：\n\n" + clean_answer_text(context),
        citations=normalize_citations(docs),
        model="fallback-no-openai",
    )


def postprocess_llm_success(
    docs: list[RetrievedDoc],
    raw_text: str | None,
    model: str,
    context: str,
) -> GeneratedAnswer:
    text = clean_answer_text(raw_text)
    if not text:
        return GeneratedAnswer(
            text="LLM 返回空答案，当前返回检索到的资料片段：\n\n" + clean_answer_text(context),
            citations=normalize_citations(docs),
            model="fallback-empty-answer",
        )

    return GeneratedAnswer(
        text=text,
        citations=normalize_citations(docs),
        model=model,
    )


def postprocess_llm_error(docs: list[RetrievedDoc], context: str) -> GeneratedAnswer:
    return GeneratedAnswer(
        text="LLM 调用失败，当前返回检索到的资料片段：\n\n" + clean_answer_text(context),
        citations=normalize_citations(docs),
        model="fallback-llm-error",
    )

```

## File: app\generation\llm_client.py

- Extension: .py
- Language: python
- Size: 1990 bytes
- Created: 2026-05-05 17:39:00
- Modified: 2026-05-05 17:39:00

### Code

```python
from typing import List

from openai import OpenAI

from app.core.config import settings
from app.core.logger import get_logger
from app.generation.answer_postprocess import (
    postprocess_llm_error,
    postprocess_llm_success,
    postprocess_no_context,
    postprocess_no_llm,
)
from app.generation.prompt_builder import build_context, build_prompt
from app.models.response import GeneratedAnswer, RetrievedDoc

logger = get_logger(__name__)


class LLMClient:
    def __init__(self):
        self.api_key = settings.openai_api_key.strip()
        self.base_url = settings.openai_base_url.strip()
        self.model = settings.openai_model
        self.max_output_tokens = settings.openai_max_output_tokens
        self.client = None

        if self.api_key:
            kwargs = {"api_key": self.api_key}
            if self.base_url and (
                self.base_url.startswith("http://") or self.base_url.startswith("https://")
            ):
                kwargs["base_url"] = self.base_url
            self.client = OpenAI(**kwargs)

    def generator(self, query: str, docs: List[RetrievedDoc]) -> GeneratedAnswer:
        if not docs:
            return postprocess_no_context(docs)

        context = build_context(query, docs)
        if not self.client:
            return postprocess_no_llm(docs, context)

        instructions, user_input = build_prompt(query, docs)

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=user_input,
                max_output_tokens=self.max_output_tokens,
            )
            return postprocess_llm_success(docs, response.output_text, self.model, context)
        except Exception as e:
            # TODO: 后续补更细的错误分类、重试策略和超时控制。
            logger.warning(f"LLM generation failed, fallback to retrieved docs: {e}")
            return postprocess_llm_error(docs, context)

```

## File: app\generation\prompt_builder.py

- Extension: .py
- Language: python
- Size: 792 bytes
- Created: 2026-05-05 17:40:04
- Modified: 2026-05-05 17:40:04

### Code

```python
from __future__ import annotations

from app.models.response import RetrievedDoc


def build_context(query: str, docs: list[RetrievedDoc]) -> str:
    del query  # 当前上下文仅由检索结果构成，先保留签名便于后续扩展。
    return "\n\n".join([f"[文档 {doc.doc_id.strip()}]\n{doc.snippet}" for doc in docs])


def build_prompt(query: str, docs: list[RetrievedDoc]) -> tuple[str, str]:
    context = build_context(query, docs)
    instructions = (
        "你是一个 RAG 问答助手。"
        "只能基于提供的检索资料回答。"
        "如果资料不足，就明确说不知道，不要编造。"
        "回答尽量简洁直接。"
    )
    user_input = f"用户问题：{query}\n\n检索资料：\n{context}"
    return instructions, user_input

```

## File: app\handlers\error_handler.py

- Extension: .py
- Language: python
- Size: 1424 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.logger import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", "-")
        logger.warning(
            "http_exception status=%s detail=%s",
            exc.status_code,
            exc.detail,
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": str(exc.detail),
                "request_id": request_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "-")
        logger.exception(
            "unhandled_exception: %s",
            str(exc),
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "Internal Server Error",
                "request_id": request_id,
            },
        )

```

## File: app\indexing\embedding_worker.py

- Extension: .py
- Language: python
- Size: 3119 bytes
- Created: 2026-05-05 16:07:57
- Modified: 2026-05-05 16:13:43

### Code

```python
from __future__ import annotations

import hashlib
import math

from app.core.config import settings

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


class EmbeddingWorker:
    _model_cache: dict[str, object] = {}
    _model_load_failed: set[str] = set()

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self.dimension = settings.embedding_dimension

    @property
    def model(self):
        if self.model_name in self._model_cache:
            return self._model_cache[self.model_name]

        if self.model_name in self._model_load_failed:
            return None

        if SentenceTransformer is None:
            self._model_load_failed.add(self.model_name)
            return None

        try:
            model = SentenceTransformer(self.model_name, local_files_only=True)
            self._model_cache[self.model_name] = model
            return model
        except Exception:
            self._model_load_failed.add(self.model_name)
            return None

    def embed_query(self, query: str) -> list[float]:
        return self._embed_one(query)

    def embed_texts(self, texts: list[str], batch_size: int | None = None) -> list[list[float]]:
        if not texts:
            return []

        model = self.model
        if model is not None:
            vectors = model.encode(
                texts,
                batch_size=batch_size or settings.embedding_batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return vectors.tolist()

        return [self._fallback_embed(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        model = self.model
        if model is not None:
            vector = model.encode(text, normalize_embeddings=True)
            return vector.tolist()
        return self._fallback_embed(text)

    def _fallback_embed(self, text: str) -> list[float]:
        text = (text or "").strip().lower()
        if not text:
            return [0.0] * self.dimension

        vector = [0.0] * self.dimension
        units = self._split_units(text)

        for idx, unit in enumerate(units):
            bucket = self._hash_to_bucket(unit)
            weight = 1.0 + min(idx, 8) * 0.03
            vector[bucket] += weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]

    def _split_units(self, text: str) -> list[str]:
        units: list[str] = []
        for token in text.split():
            units.append(token)

        chars = [char for char in text if not char.isspace()]
        units.extend(chars)

        for i in range(len(chars) - 1):
            units.append(chars[i] + chars[i + 1])

        return units or [text]

    def _hash_to_bucket(self, text: str) -> int:
        digest = hashlib.md5(text.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % self.dimension

```

## File: app\indexing\loaders.py

- Extension: .py
- Language: python
- Size: 1848 bytes
- Created: 2026-04-29 19:27:06
- Modified: 2026-05-05 17:49:02

### Code

```python
from pathlib import Path
import json

from app.models.document import SourceDocument


SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".markdown"}


class DocumentLoader:
    
    def load(self, input_path: str) -> list[SourceDocument]:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"输入路径不存在: {input_path}")

        if path.is_file():
            return self._load_file(path)

        documents: list[SourceDocument] = []
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_TEXT_SUFFIXES | {".jsonl"}:
                documents.extend(self._load_file(file_path))
        return documents

    def _load_file(self, file_path: Path) -> list[SourceDocument]:
        if file_path.suffix.lower() == ".jsonl":
            return self._load_jsonl(file_path)

        text = file_path.read_text(encoding="utf-8")
        return [
            SourceDocument(
                doc_id=file_path.stem,
                text=text,
                source=str(file_path),
            )
        ]

    def _load_jsonl(self, file_path: Path) -> list[SourceDocument]:
        documents: list[SourceDocument] = []
        with file_path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                text = (record.get("text") or "").strip()
                if not text:
                    continue
                doc_id = str(record.get("id") or f"{file_path.stem}-{idx}")
                source = str(record.get("source") or file_path)
                documents.append(SourceDocument(doc_id=doc_id, text=text, source=source))
        return documents

```

## File: app\indexing\milvus_upsert.py

- Extension: .py
- Language: python
- Size: 2720 bytes
- Created: 2026-05-05 16:11:42
- Modified: 2026-05-05 16:49:57

### Code

```python
from pymilvus import DataType, MilvusClient

from app.core.config import settings
from app.core.logger import get_logger
from app.models.document import DocumentChunk

logger = get_logger(__name__)


class MilvusUpserter:
    def __init__(self):
        self.client = MilvusClient(
            uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
            user=settings.milvus_user or None,
            password=settings.milvus_password or None,
        )
        self.collection_name = settings.milvus_collection

    def ensure_collection(self, drop_old: bool = False) -> None:
        if drop_old and self.client.has_collection(self.collection_name):
            self.client.drop_collection(self.collection_name)
            logger.info(f"Dropped Milvus collection: {self.collection_name}")

        if self.client.has_collection(self.collection_name):
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=100, is_primary=True)
        schema.add_field(
            field_name="vector",
            datatype=DataType.FLOAT_VECTOR,
            dim=settings.embedding_dimension,
        )
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=4000)
        schema.add_field(field_name="source", datatype=DataType.VARCHAR, max_length=500)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="FLAT",
            metric_type="COSINE",
        )

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        logger.info(f"Created Milvus collection: {self.collection_name}")

    def upsert_chunks(self, chunks: list[DocumentChunk], vectors: list[list[float]]) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("chunks 与 vectors 数量不一致")

        if not chunks:
            return 0

        rows = [
            {
                "id": chunk.chunk_id,
                "vector": vector,
                "text": chunk.text,
                "source": chunk.source,
            }
            for chunk, vector in zip(chunks, vectors)
        ]
        # TODO: 当前每批写入后立即 flush，优先保证数据可见；后续可改为全部写完后统一 flush 提升性能。
        self.client.insert(collection_name=self.collection_name, data=rows)
        self.client.flush(collection_name=self.collection_name)
        logger.info(f"Inserted {len(rows)} chunks into Milvus")
        return len(rows)

```

## File: app\indexing\splitter.py

- Extension: .py
- Language: python
- Size: 1591 bytes
- Created: 2026-04-29 19:27:06
- Modified: 2026-05-05 15:09:23

### Code

```python
from app.models.document import DocumentChunk, SourceDocument


class TextSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        if chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap 不能小于 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents: list[SourceDocument]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for doc in documents:
            chunks.extend(self._split_one(doc))
        return chunks

    def _split_one(self, document: SourceDocument) -> list[DocumentChunk]:
        text = document.text.strip()
        if not text:
            return []

        chunks: list[DocumentChunk] = []
        start = 0
        index = 0
        step = self.chunk_size - self.chunk_overlap

        while start < len(text):
            end = min(len(text), start + self.chunk_size)
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document.doc_id}#chunk-{index}",
                        text=chunk_text,
                        source=document.source,
                    )
                )
                index += 1
            if end >= len(text):
                break
            start += step

        return chunks

```

## File: app\indexing\__init__.py

- Extension: .py
- Language: python
- Size: 35 bytes
- Created: 2026-04-29 19:27:06
- Modified: 2026-05-05 15:09:23

### Code

```python
"""索引链路相关模块。"""

```

## File: app\middleware\metrics_middleware.py

- Extension: .py
- Language: python
- Size: 634 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.metrics import record_http_request


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        record_http_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration,
        )
        return response

```

## File: app\middleware\request_logger.py

- Extension: .py
- Language: python
- Size: 933 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logger import get_logger

logger = get_logger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={"request_id": request_id},
        )

        response.headers["X-Request-ID"] = request_id
        return response

```

## File: app\models\document.py

- Extension: .py
- Language: python
- Size: 441 bytes
- Created: 2026-04-29 20:36:51
- Modified: 2026-05-05 15:09:23

### Code

```python
from dataclasses import dataclass
"""
  #### 索引文档模型

  - SourceDocument
  - DocumentChunk
"""


@dataclass
class SourceDocument:
    """
    - title
    - metadata
    - tags
    - section
    - source_type
    """
    doc_id: str
    text: str
    source: str


@dataclass
class DocumentChunk:
    """
    - title
    - metadata
    - tags
    - section
    - source_type
    """
    chunk_id: str
    text: str
    source: str

```

## File: app\models\query.py

- Extension: .py
- Language: python
- Size: 919 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-29 21:24:18

### Code

```python
from dataclasses import dataclass
from enum import Enum

"""
  #### 查询决策模型

  - Intent
  - RetrievalStrategy
  - RouteDecision
"""



# TODO 将其升级为 Pydantic 的 BaseModel

class Intent(str,Enum): 
    FAQ = 'faq'                # FAQ: Frequently Asked Questions
    KNOWLEDGE = 'knowledge'

class RetrievalStrategy(str,Enum): #当你继承 Enum 时，Python 自动把你定义里的所有类属性（如 RAG）都转换成了一个对象（Instance）
    DIRECT_FAQ = "direct_faq"      #若不继承str，则输出: <enum 'MyEnum'> (它不是字符串，它是 MyEnum 这个枚举类的一个实例)
    RAG = "rag"

@dataclass  
class RouteDecision:    # if decision.confidence > 0.95: ...
    intent:Intent        # Python 的 “委托” (Delegation) 和 “混入” (Mixin)
    strategy:RetrievalStrategy
    confidence:float  
    direct_answer:str | None = None
```

## File: app\models\response.py

- Extension: .py
- Language: python
- Size: 613 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-29 21:24:29

### Code

```python
from dataclasses import dataclass

"""
  #### 查询结果模型

  - RetrievedDoc
  - GeneratedAnswer
"""

# TODO 将其升级为 Pydantic 的 BaseModel

@dataclass
class  RetrievedDoc:

    # TODO 后续扩充 metadata: dict 字段,把页码、章节、文件来源 URL 塞进去
    
    doc_id: str
    score: float
    snippet: str
    # matadata: json
     
@dataclass
class GeneratedAnswer:
    text: str
    citations: list[str]
    model: str # 不同模型间进行 A/B 测试或者平滑迁移时，这个字段能帮你追踪到：这条答案到底是哪个模型生成的。
```

## File: app\retrieval\bm25_retriever.py

- Extension: .py
- Language: python
- Size: 2 bytes
- Created: 2026-04-29 22:11:25
- Modified: 2026-05-05 15:09:23

### Code

```python


```

## File: app\retrieval\hybrid_retriever.py

- Extension: .py
- Language: python
- Size: 1634 bytes
- Created: 2026-05-05 16:08:44
- Modified: 2026-05-05 16:50:19

### Code

```python
from typing import List

from app.core.logger import get_logger
from app.indexing.embedding_worker import EmbeddingWorker
from app.models.response import RetrievedDoc
from app.retrieval.milvus_retriever import MilvusRetriever

logger = get_logger(__name__)


class HybridRetriever:
    def __init__(self):
        self.embedder = EmbeddingWorker()
        self._milvus_retriever: MilvusRetriever | None = None

    def _get_milvus_retriever(self) -> MilvusRetriever | None:
        if self._milvus_retriever is not None:
            return self._milvus_retriever

        try:
            self._milvus_retriever = MilvusRetriever()
            return self._milvus_retriever
        except Exception as e:
            logger.warning(f"Milvus 初始化失败: {e}")
            return None

    def retrieve(self, query: str, top_k: int = 3) -> List[RetrievedDoc]:
        query = query.strip()
        if not query:
            return []

        milvus_retriever = self._get_milvus_retriever()
        if not milvus_retriever:
            return []

        try:
            query_vector = self.embedder.embed_query(query)
        except Exception as e:
            logger.error(f"Embedding query failed: {e}")
            return []

        # TODO: 当前只有向量检索；后续补 BM25 / RRF / rerank，真正升级为 Hybrid Retrieval。
        logger.info(f"Searching Milvus for query: {query}")
        docs: List[RetrievedDoc] = milvus_retriever.search(query_vector, top_k)

        if not docs:
            logger.warning("No documents found in Milvus, returning empty results")
            return []

        return docs

```

## File: app\retrieval\milvus_retriever.py

- Extension: .py
- Language: python
- Size: 3482 bytes
- Created: 2026-05-05 17:09:47
- Modified: 2026-05-05 17:09:47

### Code

```python
from typing import List

from pymilvus import MilvusClient

from app.core.config import settings
from app.core.logger import get_logger
from app.models.response import RetrievedDoc

logger = get_logger(__name__)


class MilvusRetriever:
    def __init__(self):
        self.client = MilvusClient(
            uri=f"http://{settings.milvus_host}:{settings.milvus_port}",
            user=settings.milvus_user or None,
            password=settings.milvus_password or None,
        )
        self.collection_name = settings.milvus_collection

    def _require_collection(self) -> None:
        if not self.client.has_collection(self.collection_name):
            raise RuntimeError(
                f"Milvus collection '{self.collection_name}' 不存在，请先执行 reindex 初始化知识库。"
            )

    def search(self, query_vector: List[float], top_k: int = 3) -> List[RetrievedDoc]:
        self._require_collection()

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                anns_field="vector",
                search_params={"metric_type": "COSINE", "params": {}},
                limit=top_k,
                output_fields=["text"],
            )

            docs: list[RetrievedDoc] = []
            for hits in results:
                for hit in hits:
                    entity = hit.get("entity", {})
                    docs.append(
                        RetrievedDoc(
                            doc_id=str(hit["id"]),
                            score=float(hit["distance"]),
                            snippet=entity.get("text", ""),
                        )
                    )
            return docs
        except Exception as e:
            logger.error(f"Milvus search failed: {e}")
            raise

    def insert_documents(self, documents: List[dict]):
        try:
            self.client.insert(collection_name=self.collection_name, data=documents)
            logger.info(f"Inserted {len(documents)} documents to Milvus")
        except Exception as e:
            logger.error(f"Failed to insert documents: {e}")

    def health_status(self) -> dict:
        exists = self.client.has_collection(self.collection_name)
        info = {
            "ok": True,
            "host": settings.milvus_host,
            "port": settings.milvus_port,
            "collection": self.collection_name,
            "collection_exists": exists,
        }

        if not exists:
            info["doc_count"] = 0
            return info

        try:
            stats = self.client.get_collection_stats(collection_name=self.collection_name)
            info["stats"] = stats
            info["doc_count"] = int(stats.get("row_count", 0))
        except Exception as e:
            info["stats_error"] = str(e)
            info["doc_count"] = None

        return info

    def sample_documents(self, limit: int = 5) -> list[dict]:
        if not self.client.has_collection(self.collection_name):
            return []

        rows = self.client.query(
            collection_name=self.collection_name,
            filter="id != ''",
            output_fields=["id", "text", "source"],
            limit=limit,
        )
        return [
            {
                "id": row.get("id", ""),
                "text": row.get("text", ""),
                "source": row.get("source", ""),
            }
            for row in rows
        ]

```

## File: app\retrieval\mysql_faq_retriever.py

- Extension: .py
- Language: python
- Size: 3534 bytes
- Created: 2026-05-05 15:55:39
- Modified: 2026-05-05 16:49:28

### Code

```python
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

```

## File: app\router\intent_router.py

- Extension: .py
- Language: python
- Size: 708 bytes
- Created: 2026-05-05 16:52:21
- Modified: 2026-05-05 16:52:21

### Code

```python
from app.models.query import Intent, RetrievalStrategy, RouteDecision


class IntentRouter:
    def route(self, query: str) -> RouteDecision:
        q = query.strip()
        # TODO: 当前仅按长度做最小路由；后续可升级为关键词规则、FAQ 召回分数或小模型分类。
        if len(q) <= 20:
            return RouteDecision(
                intent=Intent.FAQ,
                strategy=RetrievalStrategy.DIRECT_FAQ,
                confidence=0.80,
                direct_answer=None,
            )
        return RouteDecision(
            intent=Intent.KNOWLEDGE,
            strategy=RetrievalStrategy.RAG,
            confidence=0.60,
            direct_answer=None,
        )

```

## File: data\seed\demo_knowledge.jsonl

- Extension: .jsonl
- Language: unknown
- Size: 1540 bytes
- Created: 2026-05-05 16:09:00
- Modified: 2026-05-05 16:09:00

### Code

```unknown
{"id":"rag-intro","source":"seed/rag-intro","text":"RAG 是 Retrieval-Augmented Generation，即检索增强生成。它的基本流程是先根据用户问题从知识库中检索相关片段，再把检索结果交给大模型生成答案。这样可以降低模型幻觉，并让回答更贴近企业私有知识。"}
{"id":"faq-vs-rag","source":"seed/faq-vs-rag","text":"FAQ 更适合固定问题和固定答案，通常使用精确匹配、模糊匹配或规则命中。RAG 更适合开放问题，需要从文档中检索上下文后再生成回答。FAQ 和 RAG 可以组合：先查 FAQ，FAQ 未命中时再回退到 RAG。"}
{"id":"milvus-role","source":"seed/milvus-role","text":"Milvus 是向量数据库，适合存储文档切片的 embedding，并支持相似度检索。在一个最小 RAG 项目里，文档先被切分成 chunk，再经过 embedding 编码写入 Milvus，查询时再用 query embedding 去搜索最相关的 chunk。"}
{"id":"reindex-flow","source":"seed/reindex-flow","text":"最小离线索引流程通常包括四步：加载原始文档、文本切分、生成 embedding、写入向量库。只有完成这条 reindex 链路，在线查询阶段的向量检索才有真实数据可查。"}
{"id":"fallback-answer","source":"seed/fallback-answer","text":"如果系统没有配置真实大模型接口，最小可用做法是返回检索到的文档片段作为 fallback。这样虽然还没有自然语言生成能力，但可以先验证检索链路、召回质量和上下文组织是否正常。"}

```

## File: docker\mysql\init\001_init_faq.sql

- Extension: .sql
- Language: sql
- Size: 816 bytes
- Created: 2026-04-28 17:26:45
- Modified: 2026-04-29 17:58:19

### Code

```sql
﻿SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

USE rag;

CREATE TABLE IF NOT EXISTS faq (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    question VARCHAR(255) NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO faq (question, answer) VALUES
('你是谁', '我是你的 RAG 助手。'),
('系统健康吗', '系统当前健康。'),
('联系方式', '请通过项目仓库提交问题或建议。'),
('你能做什么', '我可以回答问题、提供信息，并结合检索结果生成答案。'),
('什么是RAG', 'RAG（Retrieval-Augmented Generation）是一种结合检索和生成的 AI 技术。'),
('如何使用', '直接输入问题，我会先检索相关信息，再给出回答。');

```

## File: scripts\reindex.py

- Extension: .py
- Language: python
- Size: 2318 bytes
- Created: 2026-04-29 19:27:06
- Modified: 2026-05-05 16:49:42

### Code

```python
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.indexing.embedding_worker import EmbeddingWorker
from app.indexing.loaders import DocumentLoader
from app.indexing.milvus_upsert import MilvusUpserter
from app.indexing.splitter import TextSplitter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="重建 Milvus 文档索引")
    parser.add_argument("input_path", help="输入文件或目录，支持 txt/md/jsonl")
    parser.add_argument("--drop-old", action="store_true", help="重建前删除旧集合")
    parser.add_argument("--chunk-size", type=int, default=settings.chunk_size)
    parser.add_argument("--chunk-overlap", type=int, default=settings.chunk_overlap)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    embedder = EmbeddingWorker()
    loader = DocumentLoader()
    splitter = TextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    upserter = MilvusUpserter()

    documents = loader.load(args.input_path)
    if not documents:
        print("Error: 未找到任何文档。")
        return

    chunks = splitter.split_documents(documents)
    if not chunks:
        print("Error: 文档切分后没有可入库的 chunk。")
        return

    print(f"待处理 Chunks 总数: {len(chunks)}")

    upserter.ensure_collection(drop_old=args.drop_old)

    # TODO: 后续可将 batch_size 提升为命令行参数或配置项，便于按机器资源调优。
    batch_size = 64
    total_inserted = 0

    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        batch_texts = [c.text for c in batch_chunks]

        # TODO: 后续可补充 tqdm / logging，增强大规模重建时的进度可观测性。
        batch_vectors = embedder.embed_texts(batch_texts)
        inserted = upserter.upsert_chunks(batch_chunks, batch_vectors)
        total_inserted += inserted

    print("\n重建完成！")
    print(f"- 原始文档数: {len(documents)}")
    print(f"- 成功写入 Chunk 数: {total_inserted}")
    print(f"- Collection: {settings.milvus_collection}")


if __name__ == "__main__":
    main()

```

## File: scripts\trace_log.py

- Extension: .py
- Language: python
- Size: 1439 bytes
- Created: 2026-04-28 15:25:13
- Modified: 2026-04-28 15:25:13

### Code

```python
import argparse
import sys
from pathlib import Path

def trace_request(log_path: str, request_id: str):
    """
    按 request_id 筛选日志行
    """
    log_file = Path(log_path)
    if not log_file.exists():
        print(f"❌ 错误: 日志文件未找到: {log_path}")
        return

    print(f"🔍 正在追踪 Request ID: [{request_id}] ...\n" + "-"*50)
    
    found_count = 0
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # 假设日志格式中包含了 request_id
                if request_id in line:
                    print(line.strip())
                    found_count += 1
        
        if found_count == 0:
            print(f"⚠️ 未找到关联该 ID 的日志条目，请确认 ID 是否正确或日志路径是否匹配。")
        else:
            print("-"*50 + f"\n✅ 扫描结束，共找到 {found_count} 条相关日志。")
            
    except Exception as e:
        print(f"❌ 读取日志时发生错误: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="根据 Request ID 快速定位日志")
    parser.add_argument("req_id", help="需要查询的 request_id")
    parser.add_argument("--file", default="logs/app.log", help="日志文件路径 (默认: logs/app.log)")
    
    args = parser.parse_args()
    trace_request(args.file, args.req_id)
```

