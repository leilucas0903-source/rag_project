SET NAMES utf8mb4;
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
