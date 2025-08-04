import os
import io
import json
import logging
import redis
import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

# 加載環境變數
load_dotenv()

# 配置日誌
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Gemini配置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro-vision")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "500"))
IMAGE_SIZE = int(os.getenv("IMAGE_SIZE", "512"))
ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,gif").split(",")

# Redis配置
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_CACHE_EXPIRY = int(os.getenv("REDIS_CACHE_EXPIRY", "3600"))  # 1小時

# 初始化Redis連接
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()  # 測試連接
    logger.info("Redis連接成功")
except redis.ConnectionError as e:
    logger.warning(f"Redis連接失敗: {e}")
    redis_client = None

# 配置Gemini
genai.configure(api_key=GEMINI_API_KEY)

class GeminiService:
    @staticmethod
    def is_valid_image(file_extension):
        """檢查圖片副檔名是否有效"""
        return file_extension.lower().lstrip('.') in ALLOWED_EXTENSIONS
    
    @staticmethod
    def preprocess_image(image_data):
        """預處理圖片"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # 調整圖片大小
            image.thumbnail((IMAGE_SIZE, IMAGE_SIZE))
            
            return image
        except Exception as e:
            logger.error(f"圖片預處理錯誤: {e}")
            raise ValueError("無法處理此圖片")

    @staticmethod
    def cache_result(line_user_id, image_hash, result):
        """緩存圖片分析結果"""
        if not redis_client:
            return
        
        try:
            cache_key = f"image_analysis:{line_user_id}:{image_hash}"
            redis_client.set(
                cache_key, 
                json.dumps(result), 
                ex=REDIS_CACHE_EXPIRY
            )
            logger.info(f"已緩存圖片分析結果: {cache_key}")
        except Exception as e:
            logger.error(f"緩存結果時出錯: {e}")
    
    @staticmethod
    def get_cached_result(line_user_id, image_hash):
        """獲取緩存的分析結果"""
        if not redis_client:
            return None
        
        try:
            cache_key = f"image_analysis:{line_user_id}:{image_hash}"
            cached = redis_client.get(cache_key)
            if cached:
                logger.info(f"從緩存獲取分析結果: {cache_key}")
                return json.loads(cached)
            return None
        except Exception as e:
            logger.error(f"從緩存獲取結果時出錯: {e}")
            return None
    
    @staticmethod
    async def analyze_image(image_data, description=None):
        """使用Gemini分析圖片"""
        try:
            # 預處理圖片
            image = GeminiService.preprocess_image(image_data)
            
            # 設定提示詞
            if description:
                prompt = f"請分析這張圖片並回答用戶的問題: {description}\n請使用繁體中文回答。"
            else:
                prompt = "請詳細描述這張圖片中的內容。請使用繁體中文描述。"
            
            # 獲取Gemini模型
            model = genai.GenerativeModel(GEMINI_MODEL)
            
            # 發送請求
            response = model.generate_content([
                prompt,
                image,
            ])
            
            analysis = response.text
            
            return {
                "analysis": analysis,
                "model": GEMINI_MODEL
            }
            
        except Exception as e:
            logger.error(f"Gemini API錯誤: {e}")
            return {
                "analysis": "很抱歉，我無法分析這張圖片。請確保圖片格式正確並再次嘗試。",
                "error": str(e)
            } 