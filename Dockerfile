# CoolFix WhatsApp AI Chatbot - container image (portable: Render, Railway, VPS)
FROM python:3.12-slim

WORKDIR /app

# Install deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Defaults (override in your host's env / dashboard)
ENV HOST=0.0.0.0 \
    PORT=8000 \
    DB_PATH=/data/coolfix.db \
    AI_PROVIDER=mock \
    WHATSAPP_PROVIDER=mock

EXPOSE 8000

# Honour the platform-provided $PORT (Render/Railway set this)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
