import os
import openai
import json
import logging
import redis
from dotenv import load_dotenv

# 加載環境變數
load_dotenv()

# 配置日誌
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# OpenAI配置
openai.api_key = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "500"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))

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

class OpenAIService:
    @staticmethod
    def get_chat_history(line_user_id, limit=5):
        """從Redis獲取用戶的聊天歷史"""
        if not redis_client:
            return []
        
        history_key = f"chat_history:{line_user_id}"
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
        
        history_key = f"chat_history:{line_user_id}"
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
        """使用OpenAI生成回應"""
        try:
            # 獲取聊天歷史
            chat_history = OpenAIService.get_chat_history(line_user_id)
            
            # 創建消息列表
            messages = [{"role": "system", "content": "你是一個友善的聊天機器人助手，請用繁體中文回應用戶問題。"}]
            
            # 添加聊天歷史
            for entry in chat_history:
                messages.append({"role": "user", "content": entry["user"]})
                messages.append({"role": "assistant", "content": entry["assistant"]})
            
            # 添加當前消息
            messages.append({"role": "user", "content": message})
            
            # 調用OpenAI API
            response = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                n=1,
                stop=None
            )
            
            # 獲取生成的回應
            generated_text = response.choices[0].message["content"].strip()
            
            # 保存到歷史記錄
            OpenAIService.save_chat_history(line_user_id, message, generated_text)
            
            return generated_text
            
        except Exception as e:
            logger.error(f"OpenAI API錯誤: {e}")
            return "很抱歉，我現在無法處理您的請求，請稍後再試。" 