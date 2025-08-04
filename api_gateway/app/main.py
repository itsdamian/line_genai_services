import os
import logging
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
import httpx
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage, TextSendMessage
)

# 配置日誌
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "/app/logs/api_gateway.log")

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

# 環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user_service:8001")
CHAT_SERVICE_URL = os.getenv("CHAT_SERVICE_URL", "http://chat_service:8002")
IMAGE_SERVICE_URL = os.getenv("IMAGE_SERVICE_URL", "http://image_service:8003")

# LINE SDK初始化
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

app = FastAPI(title="Line Bot API Gateway")

# HTTP客戶端
http_client = httpx.AsyncClient(timeout=30.0)

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "api_gateway"}

@app.post("/webhook")
async def line_webhook(request: Request, x_line_signature: str = Header(None)):
    # 獲取請求體
    body = await request.body()
    body_decode = body.decode("utf-8")
    
    # 驗證LINE請求簽名
    try:
        handler.handle(body_decode, x_line_signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    return JSONResponse(content={"status": "ok"})

@handler.add(MessageEvent, message=TextMessage)
async def handle_text_message(event):
    """處理文本消息"""
    user_id = event.source.user_id
    text = event.message.text
    
    try:
        # 1. 更新用戶活躍狀態
        await http_client.post(
            f"{USER_SERVICE_URL}/users/update_activity",
            json={"line_user_id": user_id}
        )
        
        # 判斷是否要使用特定AI提供者
        model_provider = "openai"  # 預設使用OpenAI
        
        # 簡單的命令解析，用戶可以通過特定命令指定AI模型
        if text.startswith("/gemini "):
            model_provider = "gemini"
            text = text[8:].strip()  # 去除命令前綴
        elif text.startswith("/openai "):
            model_provider = "openai"
            text = text[8:].strip()  # 去除命令前綴
        
        # 2. 發送文本到對話服務
        response = await http_client.post(
            f"{CHAT_SERVICE_URL}/chat/process",
            json={
                "line_user_id": user_id, 
                "message": text,
                "model_provider": model_provider
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            # 構建回覆訊息，包含提供者資訊
            reply_text = f"{result['response']}\n\n[由 {result['provider']} 提供]"
            
            # 發送回覆到LINE
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
        else:
            logger.error(f"Error from chat service: {response.status_code} - {response.text}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="很抱歉，處理訊息時發生錯誤。")
            )
            
    except Exception as e:
        logger.error(f"Error processing text message: {str(e)}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="很抱歉，處理訊息時發生錯誤。")
        )

@handler.add(MessageEvent, message=ImageMessage)
async def handle_image_message(event):
    """處理圖像消息"""
    user_id = event.source.user_id
    message_id = event.message.id
    
    try:
        # 1. 從LINE獲取圖像內容
        message_content = line_bot_api.get_message_content(message_id)
        image_data = b''
        for chunk in message_content.iter_content():
            image_data += chunk
        
        # 2. 發送圖像到圖像處理服務
        files = {"image": ("image.jpg", image_data, "image/jpeg")}
        data = {"line_user_id": user_id}
        
        response = await http_client.post(
            f"{IMAGE_SERVICE_URL}/images/analyze",
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            result = response.json()
            # 發送回覆到LINE
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=result["analysis"])
            )
        else:
            logger.error(f"Error from image service: {response.status_code} - {response.text}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="很抱歉，處理圖片時發生錯誤。")
            )
            
    except Exception as e:
        logger.error(f"Error processing image message: {str(e)}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="很抱歉，處理圖片時發生錯誤。")
        )

@app.on_event("startup")
async def startup_event():
    logger.info("API Gateway starting up")

@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()
    logger.info("API Gateway shutting down") 