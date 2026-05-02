import os
from dotenv import load_dotenv

load_dotenv()

CAPITAL = 100000
NORMAL_TRADE = 10000
LARGE_TRADE_MIN = 30000
LARGE_TRADE_MAX = 50000
NIKKEI_LARGE_MOVE_THRESHOLD = 1000

AI_PROVIDER = "openai"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
