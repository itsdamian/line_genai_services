FROM python:3.10-slim

WORKDIR /app

# 安裝系統依賴 (用於處理圖像和健康檢查)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 創建日誌目錄
RUN mkdir -p /app/logs && chmod 777 /app/logs

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"] 