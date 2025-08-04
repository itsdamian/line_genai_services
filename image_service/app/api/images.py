import os
import logging
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.models.database import get_db, ImageHistory
from app.services.gemini_service import GeminiService
from app.utils.image_utils import save_temp_image, get_image_info

# 配置日誌
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/analyze")
async def analyze_image(
    background_tasks: BackgroundTasks,
    image: UploadFile = File(...),
    line_user_id: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """分析圖片並返回結果"""
    try:
        # 確認圖片副檔名
        file_extension = os.path.splitext(image.filename)[1]
        if not GeminiService.is_valid_image(file_extension):
            raise HTTPException(status_code=400, detail="不支持的圖片格式")
        
        # 保存臨時圖片
        image_data, image_hash = await save_temp_image(image)
        
        # 檢查緩存中是否有分析結果
        cached_result = GeminiService.get_cached_result(line_user_id, image_hash)
        if cached_result:
            # 在背景保存分析歷史
            background_tasks.add_task(
                save_image_history,
                db=db,
                line_user_id=line_user_id,
                image_url=f"local:{image_hash}{file_extension}",
                description=description,
                analysis_result=cached_result
            )
            return cached_result
        
        # 分析圖片
        result = await GeminiService.analyze_image(image_data, description)
        
        # 緩存分析結果
        GeminiService.cache_result(line_user_id, image_hash, result)
        
        # 在背景保存分析歷史
        background_tasks.add_task(
            save_image_history,
            db=db,
            line_user_id=line_user_id,
            image_url=f"local:{image_hash}{file_extension}",
            description=description,
            analysis_result=result
        )
        
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"分析圖片時出錯: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def save_image_history(
    db: Session,
    line_user_id: str,
    image_url: str,
    description: Optional[str],
    analysis_result: dict
):
    """將圖片分析歷史保存到數據庫"""
    try:
        image_history = ImageHistory(
            line_user_id=line_user_id,
            image_url=image_url,
            description=description,
            analysis_result=analysis_result
        )
        db.add(image_history)
        db.commit()
        logger.info(f"已保存圖片分析記錄，用戶ID: {line_user_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"保存圖片分析記錄時出錯: {e}")

@router.get("/history/{line_user_id}")
async def get_image_history(line_user_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """獲取用戶的圖片分析歷史"""
    try:
        history = db.query(ImageHistory).filter(
            ImageHistory.line_user_id == line_user_id
        ).order_by(ImageHistory.created_at.desc()).limit(limit).all()
        
        return {
            "line_user_id": line_user_id,
            "history": [
                {
                    "id": item.id,
                    "image_url": item.image_url,
                    "description": item.description,
                    "analysis": item.analysis_result.get("analysis"),
                    "created_at": item.created_at
                } for item in history
            ]
        }
    except Exception as e:
        logger.error(f"獲取圖片分析歷史時出錯: {e}")
        raise HTTPException(status_code=500, detail=str(e))