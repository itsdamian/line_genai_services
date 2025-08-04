import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api import chat
from app.models.database import engine, Base

# 加載環境變數
load_dotenv()

# 配置日誌
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "/app/logs/chat_service.log")

# 確保日誌目錄存在
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# 設置日誌格式和處理器
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # 文件處理器
        logging.StreamHandler()         # 控制台處理器
    ]
)
logger = logging.getLogger(__name__)

# 創建表格
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chat Service")

# 設置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生產環境中應該設置為特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(chat.router, prefix="/chat", tags=["chat"])

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "chat_service"}

@app.on_event("startup")
async def startup_event():
    logger.info("Chat Service starting up")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Chat Service shutting down") 