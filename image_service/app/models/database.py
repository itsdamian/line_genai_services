import os
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# 加載環境變數
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# 創建SQLAlchemy引擎
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ImageHistory(Base):
    """圖片處理歷史記錄模型"""
    __tablename__ = "image_history"

    id = Column(Integer, primary_key=True, index=True)
    line_user_id = Column(String(50), nullable=False, index=True)
    image_url = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    analysis_result = Column(JSON, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

# 獲取數據庫會話
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 