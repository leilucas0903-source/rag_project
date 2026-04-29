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