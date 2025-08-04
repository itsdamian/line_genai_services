import os
import json
import logging
import redis
import google.generativeai as genai
from dotenv import load_dotenv

# 加載環境變數
load_dotenv()

# 配置日誌
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Gemini配置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")  # 使用文字模型
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "500"))

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
    def get_chat_history(line_user_id, limit=5):
        """從Redis獲取用戶的聊天歷史"""
        if not redis_client:
            return []
        
        history_key = f"gemini_chat_history:{line_user_id}"
        try:
            history_json = redis_client.get(history_key)
            if history_json:
                return json.loads(history_json)[-limit:]
            return []
        except Exception as e:
            logger.error(f"獲取聊天歷史錯誤: {e}")
            return []
    
    @staticmethod
    def save_chat_history(line_user_id, message, response):
        """保存聊天歷史到Redis"""
        if not redis_client:
            return
        
        history_key = f"gemini_chat_history:{line_user_id}"
        try:
            # 獲取現有歷史或創建新的
            history_json = redis_client.get(history_key)
            if history_json:
                history = json.loads(history_json)
            else:
                history = []
            
            # 添加新的對話
            history.append({
                "user": message,
                "assistant": response
            })
            
            # 保存歷史，只保留最近10條
            redis_client.set(
                history_key, 
                json.dumps(history[-10:]), 
                ex=REDIS_CACHE_EXPIRY
            )
        except Exception as e:
            logger.error(f"保存聊天歷史錯誤: {e}")
    
    @staticmethod
    async def generate_response(line_user_id, message):
        """使用Gemini生成回應"""
        try:
            # 獲取聊天歷史
            chat_history = GeminiService.get_chat_history(line_user_id)
            
            # 初始化聊天模型
            model = genai.GenerativeModel(GEMINI_MODEL)
            chat = model.start_chat(history=[])
            
            # 添加歷史對話
            for entry in chat_history:
                chat.history.append({"role": "user", "parts": [entry["user"]]})
                chat.history.append({"role": "model", "parts": [entry["assistant"]]})
            
            # 發送當前消息
            response = chat.send_message(message)
            
            # 獲取生成的回應
            generated_text = response.text
            
            # 保存到歷史記錄
            GeminiService.save_chat_history(line_user_id, message, generated_text)
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Gemini API錯誤: {e}")
            return "很抱歉，我現在無法處理您的請求，請稍後再試。" 