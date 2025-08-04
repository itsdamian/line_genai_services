import os
import hashlib
import io
import logging
from fastapi import UploadFile
from PIL import Image

# 配置日誌
logger = logging.getLogger(__name__)

async def save_temp_image(upload_file: UploadFile) -> tuple:
    """
    保存上傳的圖片到臨時目錄
    
    返回: (圖片資料, 圖片雜湊值)
    """
    try:
        # 讀取圖片數據
        image_data = await upload_file.read()
        
        # 計算圖片雜湊值用於緩存
        image_hash = hashlib.md5(image_data).hexdigest()
        
        return image_data, image_hash
    except Exception as e:
        logger.error(f"保存臨時圖片錯誤: {e}")
        raise

def get_image_info(image_data: bytes) -> dict:
    """
    獲取圖片信息
    
    返回: 包含圖片信息的字典
    """
    try:
        image = Image.open(io.BytesIO(image_data))
        return {
            "format": image.format,
            "size": image.size,
            "mode": image.mode
        }
    except Exception as e:
        logger.error(f"獲取圖片信息錯誤: {e}")
        return {
            "error": str(e)
        } 