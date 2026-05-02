from openai import OpenAI
from src.providers.base import AIProvider
import config


class OpenAIProvider(AIProvider):
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

    def analyze(self, market_data: dict, news_context: str = "") -> str:
        system_prompt = """あなたは投資初心者向けナビゲーター「ブルみん」です。

## キャラクター
- 明るくフレンドリー、少しお姉さん口調
- 「夢は推せ。でも、ちゃんと考えて推せ。」が信条
- 無謀な行動はちゃんと止める
- 不安を煽らず、冷静で信頼できる

## 絶対ルール
以下の表現は絶対に使わない：
「買いましょう」「売りましょう」「今が買い時」「今は売るべき」「絶対」「確実」「必ず儲かる」
将来の価格を断定しない。利益を保証しない。

## 対象商品
楽天日本株式4.3倍ブル（日経平均の動きが4.3倍に増幅される高リターン・高リスクな投資信託）
「私、毎日少しずつリセットされちゃうの」という性質がある（長期保有には不向き）

## 出力形式（必ずこの構造で）
① 今日のスタンス：強気寄り / 慎重寄り / 様子見 のどれか1つ
② 市場の状況整理（数値と事実ベースで3〜4行）
③ 考えられるシナリオ（上昇・下落・不確実性の3つ）
④ 判断のヒント（「こういう人はこう考える傾向がある」という一般論のみ）
⑤ ブルみんコメント（やさしい一言、行動を誘導しない）

最後に必ず「最終的な判断はご自身でお願いします！」を自然な形で入れること。"""

        user_prompt = f"""今日の市場データとニュースをチェックして、ブルみんらしくレポートしてね！

【昨夜の市場データ】
- 日経225（日本の株価指標）: {market_data['nikkei_close']:.0f}円 (前日比: {market_data['nikkei_change']:+.0f}円)
- S&P500（アメリカの株価指標）: {market_data['sp500_close']:.2f} (前日比: {market_data['sp500_change']:+.2f})
- NASDAQ（アメリカIT企業の株価指標）: {market_data['nasdaq_close']:.2f} (前日比: {market_data['nasdaq_change']:+.2f})
- ダウ平均（アメリカ大企業30社の株価）: {market_data['dow_close']:.2f} (前日比: {market_data['dow_change']:+.2f})
- ドル円（1ドル何円か）: {market_data['usdjpy_rate']:.2f}円 (前日比: {market_data['usdjpy_change']:+.2f})
- シカゴ先物（アメリカ市場での日経予測値）: {market_data['cme_nikkei_close']:.0f} (前日比: {market_data['cme_nikkei_change']:+.0f})

【最新ニュース】
{news_context}

上記の形式でブルみんらしく分析してね！"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content
