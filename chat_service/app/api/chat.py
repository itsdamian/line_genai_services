from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal
import logging

from app.models.database import get_db, ChatHistory
from app.services.openai_service import OpenAIService
from app.services.gemini_service import GeminiService

# 配置日誌
logger = logging.getLogger(__name__)

router = APIRouter()

class ChatRequest(BaseModel):
    line_user_id: str
    message: str
    context: Optional[Dict[str, Any]] = None
    model_provider: Optional[Literal["openai", "gemini"]] = "openai"  # 預設使用OpenAI

class ChatResponse(BaseModel):
    response: str
    provider: str

@router.post("/process", response_model=ChatResponse)
async def process_chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """處理用戶聊天請求"""
    try:
        # 根據選擇的服務生成回應
        if request.model_provider == "gemini":
            response_text = await GeminiService.generate_response(request.line_user_id, request.message)
            provider = "gemini"
        else:
            response_text = await OpenAIService.generate_response(request.line_user_id, request.message)
            provider = "openai"
        
        # 在背景保存聊天歷史到數據庫
        background_tasks.add_task(
            save_chat_history,
            db=db,
            line_user_id=request.line_user_id,
            message=request.message,
            response=response_text,
            context=request.context,
            provider=provider
        )
        
        return ChatResponse(response=response_text, provider=provider)
    except Exception as e:
        logger.error(f"處理聊天請求時出錯: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def save_chat_history(
    db: Session,
    line_user_id: str,
    message: str,
    response: str,
    provider: str,
    context: Optional[Dict[str, Any]] = None
):
    """將聊天歷史保存到數據庫"""
    try:
        # 如果context為None，初始化為空字典
        if context is None:
            context = {}
        
        # 添加提供者資訊到context
        context["provider"] = provider
        
        chat_history = ChatHistory(
            line_user_id=line_user_id,
            message=message,
            response=response,
            context=context
        )
        db.add(chat_history)
        db.commit()
        logger.info(f"已保存聊天記錄，用戶ID: {line_user_id}, 使用服務: {provider}")
    except Exception as e:
        db.rollback()
        logger.error(f"保存聊天記錄時出錯: {e}")

@router.get("/history/{line_user_id}")
async def get_chat_history(line_user_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """獲取用戶的聊天歷史"""
    try:
        history = db.query(ChatHistory).filter(
            ChatHistory.line_user_id == line_user_id
        ).order_by(ChatHistory.created_at.desc()).limit(limit).all()
        
        return {
            "line_user_id": line_user_id,
            "history": [
                {
                    "id": item.id,
                    "message": item.message,
                    "response": item.response,
                    "created_at": item.created_at,
                    "provider": item.context.get("provider", "unknown") if item.context else "unknown",
                    "context": item.context
                } for item in history
            ]
        }
    except Exception as e:
        logger.error(f"獲取聊天歷史時出錯: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 