import os
from dotenv import load_dotenv

load_dotenv()

CAPITAL = 100000
MAX_PARTS = 5
LOT_MIN = 10_000
LOT_PCT = 0.20  # 1口あたり総資本の20%（シミュ比較で10%→20%に変更）

AI_PROVIDER = "openai"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

X_API_KEY            = os.getenv("X_API_KEY")
X_API_KEY_SECRET     = os.getenv("X_API_KEY_SECRET")
X_ACCESS_TOKEN       = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

