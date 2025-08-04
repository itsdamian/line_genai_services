import os
import json
from sqlalchemy import Column, Integer, String, DateTime, JSON, create_engine, func
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

class User(Base):
    """使用者模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    line_user_id = Column(String(50), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    last_active = Column(DateTime, server_default=func.now(), onupdate=func.now())
    preferences = Column(JSON, default={})

    def to_dict(self):
        """將模型轉換為字典"""
        return {
            "id": self.id,
            "line_user_id": self.line_user_id,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "preferences": self.preferences
        }

# 獲取數據庫會話
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 