import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.models.database import get_db, User

# 配置日誌
logger = logging.getLogger(__name__)

router = APIRouter()

class UserCreate(BaseModel):
    line_user_id: str
    username: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class UserUpdate(BaseModel):
    username: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class UserActivityUpdate(BaseModel):
    line_user_id: str

@router.post("/create")
async def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """創建新用戶"""
    try:
        # 檢查用戶是否已存在
        existing_user = db.query(User).filter(User.line_user_id == user_data.line_user_id).first()
        if existing_user:
            return existing_user.to_dict()
        
        # 創建新用戶
        new_user = User(
            line_user_id=user_data.line_user_id,
            username=user_data.username,
            preferences=user_data.preferences or {}
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"已創建新用戶: {user_data.line_user_id}")
        return new_user.to_dict()
    except Exception as e:
        db.rollback()
        logger.error(f"創建用戶時出錯: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{line_user_id}")
async def get_user(line_user_id: str, db: Session = Depends(get_db)):
    """獲取用戶信息"""
    try:
        user = db.query(User).filter(User.line_user_id == line_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用戶不存在")
        
        return user.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取用戶信息時出錯: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{line_user_id}")
async def update_user(line_user_id: str, user_data: UserUpdate, db: Session = Depends(get_db)):
    """更新用戶信息"""
    try:
        user = db.query(User).filter(User.line_user_id == line_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用戶不存在")
        
        # 更新可變欄位
        if user_data.username is not None:
            user.username = user_data.username
        
        if user_data.preferences is not None:
            # 合併現有偏好設定和新的偏好設定
            if user.preferences:
                user.preferences.update(user_data.preferences)
            else:
                user.preferences = user_data.preferences
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"已更新用戶信息: {line_user_id}")
        return user.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新用戶信息時出錯: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update_activity")
async def update_user_activity(activity_data: UserActivityUpdate, db: Session = Depends(get_db)):
    """更新用戶活躍狀態"""
    try:
        line_user_id = activity_data.line_user_id
        
        # 查詢用戶
        user = db.query(User).filter(User.line_user_id == line_user_id).first()
        
        # 如果用戶不存在，則創建
        if not user:
            user = User(line_user_id=line_user_id)
            db.add(user)
        
        # 更新last_active時間
        user.last_active = func.now()
        
        db.commit()
        
        logger.info(f"已更新用戶活躍狀態: {line_user_id}")
        return {"status": "success", "line_user_id": line_user_id}
    except Exception as e:
        db.rollback()
        logger.error(f"更新用戶活躍狀態時出錯: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 