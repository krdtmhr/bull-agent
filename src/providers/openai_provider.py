from openai import OpenAI
from src.providers.base import AIProvider
import config


class OpenAIProvider(AIProvider):
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

    def analyze(self, market_data: dict, news_context: str = "") -> str:
        system_prompt = (
            "あなたは投資初心者にもわかりやすく説明するファイナンシャルアドバイザーです。"
            "「楽天日本株式4.3倍ブル」という投資信託の売買タイミングをアドバイスします。"
            "この商品は日経平均が1%上がると約4.3%上がり、1%下がると約4.3%下がる高リターン・高リスクな商品です。"
            "専門用語はできるだけ使わず、中学生でもわかる言葉で説明してください。"
        )

        user_prompt = f"""以下の市場データとニュースを分析してください。

【昨夜の市場データ】
- 日経225（日本の株価指標）: {market_data['nikkei_close']:.0f}円 (前日比: {market_data['nikkei_change']:+.0f}円)
- S&P500（アメリカの株価指標）: {market_data['sp500_close']:.2f} (前日比: {market_data['sp500_change']:+.2f})
- NASDAQ（アメリカIT企業の株価指標）: {market_data['nasdaq_close']:.2f} (前日比: {market_data['nasdaq_change']:+.2f})
- ダウ平均（アメリカ大企業30社の株価）: {market_data['dow_close']:.2f} (前日比: {market_data['dow_change']:+.2f})
- ドル円（1ドル何円か）: {market_data['usdjpy_rate']:.2f}円 (前日比: {market_data['usdjpy_change']:+.2f})
- シカゴ先物（アメリカ市場での日経の予測値）: {market_data['cme_nikkei_close']:.0f} (前日比: {market_data['cme_nikkei_change']:+.0f})

【最新ニュース】
{news_context}

以下の形式で回答してください：

■ 今日の世界の株式市場の流れ（3〜4行で初心者向けにわかりやすく）

■ 楽天日本株式4.3倍ブルへの判断
- 判断：購入 / 売却 / 様子見
- 理由：（2〜3行で具体的に）
- 注意すべきリスク：（1〜2行で）

※専門用語は使わず、誰でもわかる言葉で書いてください。"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content
