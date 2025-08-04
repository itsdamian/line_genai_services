-- 創建資料庫
CREATE DATABASE user_db;
CREATE DATABASE chat_db;
CREATE DATABASE image_db;

-- 連接到使用者資料庫
\c user_db;

-- 建立使用者表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    line_user_id VARCHAR(50) UNIQUE NOT NULL,
    username VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    preferences JSONB DEFAULT '{}'::jsonb
);

-- 連接到對話資料庫
\c chat_db;

-- 建立對話歷史表
CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    line_user_id VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    context JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX chat_history_user_id_idx ON chat_history(line_user_id);

-- 連接到圖片資料庫
\c image_db;

-- 建立圖片處理歷史表
CREATE TABLE image_history (
    id SERIAL PRIMARY KEY,
    line_user_id VARCHAR(50) NOT NULL,
    image_url TEXT NOT NULL,
    description TEXT,
    analysis_result JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX image_history_user_id_idx ON image_history(line_user_id); 