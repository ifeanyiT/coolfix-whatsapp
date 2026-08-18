"""Start the CoolFix WhatsApp AI Chatbot.

    python run.py

Then open http://127.0.0.1:8000  (WhatsApp simulator)
and     http://127.0.0.1:8000/dashboard  (business dashboard).
"""
import uvicorn

from app.config import settings

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=False)
