from openai import OpenAI
from src.providers.base import AIProvider
import config


class OpenAIProvider(AIProvider):
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

    def analyze(self, market_data: dict) -> str:
        system_prompt = (
            "あなたは日本株の短期トレーダーのアシスタントです。"
            "市場データを分析して、日経4.3倍ブル投資信託の売買判断を行います。"
        )

        user_prompt = f"""以下の市場データを分析してください。

【市場データ】
- 日経225: {market_data['nikkei_close']:.0f}円 (前日比: {market_data['nikkei_change']:+.0f}円 / {market_data['nikkei_change_pct']:+.2f}%)
- S&P500: {market_data['sp500_close']:.2f} (前日比: {market_data['sp500_change']:+.2f} / {market_data['sp500_change_pct']:+.2f}%)
- NASDAQ: {market_data['nasdaq_close']:.2f} (前日比: {market_data['nasdaq_change']:+.2f} / {market_data['nasdaq_change_pct']:+.2f}%)
- ダウ平均: {market_data['dow_close']:.2f} (前日比: {market_data['dow_change']:+.2f} / {market_data['dow_change_pct']:+.2f}%)
- USD/JPY: {market_data['usdjpy_rate']:.2f}円 (前日比: {market_data['usdjpy_change']:+.2f} / {market_data['usdjpy_change_pct']:+.2f}%)
- CME日経先物: {market_data['cme_nikkei_close']:.0f} (前日比: {market_data['cme_nikkei_change']:+.0f} / {market_data['cme_nikkei_change_pct']:+.2f}%)

以下の点を分析してください：
1. 世界の流れの分析（米国市場、為替、先物の動向とその背景）
2. 日経4.3倍ブル投資信託への推奨アクション（BUY / SELL / HOLD）
3. 確信度（0〜100%）
4. 主なリスク要因

回答は日本語で簡潔にまとめてください。"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content
