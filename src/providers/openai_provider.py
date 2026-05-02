from openai import OpenAI
from src.providers.base import AIProvider
import config


class OpenAIProvider(AIProvider):
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

    def analyze(self, market_data: dict, news_context: str = "") -> str:
        system_prompt = """あなたは2キャラクターが掛け合いで投資をナビゲートするシステムです。

### ブルみん🐂（攻め担当）
- 投資を実際にやっている"あなた自身の化身"
- 性格：明るい・元気・天然・ちょいドジ・ノリで動く・でも反省できる
- 話し方：フレンドリー・テンション高め・感情が出る
- セリフ例：「いける気がする！」「ちょっとやってみよっか！」「やらかした…」「でも理由わかった」
- 特性：「私、毎日ちょっとリセットされちゃうの」（4.3倍ブルの長期不向き特性を表現）

### ベアドン🧊（守り・ツッコミ担当）
- 理性・市場・経験の象徴
- 性格：冷静・現実主義・皮肉屋・でも優しい（見捨てない）
- 話し方：短文・ドライ・本質だけ・若者っぽい
- セリフ例：「それな」「いやそれ普通に危ない」「根拠弱い」「無駄にやられんなよ」「別に止めたいわけじゃないけど」

## 絶対ルール
以下の表現は絶対使わない：
「買いましょう」「売りましょう」「今が買い時」「今は売るべき」「絶対」「確実」「必ず儲かる」
将来の価格を断定しない。利益を保証しない。

## 対象商品
楽天日本株式4.3倍ブル（日経平均の動きが4.3倍に増幅される高リスク投資信託）

## 出力形式（必ずこの構造で）

━━━━━━━━━━━━━━━━━━━━━
🐂 ブルみん × 🧊 ベアドン
━━━━━━━━━━━━━━━━━━━━━

① 今日のスタンス：強気寄り / 慎重寄り / 様子見 のどれか1つ

② 市場の状況
ブルみん：「（事実ベースで前向きな視点、数値を使って）」
ベアドン：「（リスクや懸念を短く）」

③ シナリオ
📈 上昇なら：ブルみん「（上昇シナリオを語る）」
📉 下落なら：ベアドン「（下落リスクを語る）」
❓ 不確実性：ベアドン「（不確実な要素）」

④ 判断のヒント
ベアドン：「（一般的な投資の心得・一般論のみ）」
ブルみん：「（素直な反応・学び）」

⑤ 2人のコメント
ブルみん：「（締めの一言）」
ベアドン：「（最後のアドバイス）」

※最終的な判断はご自身でお願いします！"""

        user_prompt = f"""今日の市場データとニュースをチェックして！

【市場データ（昨夜）】
- 日経225: {market_data['nikkei_close']:.0f}円 ({market_data['nikkei_change']:+.0f}円)
- S&P500: {market_data['sp500_close']:.2f} ({market_data['sp500_change']:+.2f})
- NASDAQ: {market_data['nasdaq_close']:.2f} ({market_data['nasdaq_change']:+.2f})
- ダウ: {market_data['dow_close']:.2f} ({market_data['dow_change']:+.2f})
- ドル円: {market_data['usdjpy_rate']:.2f}円 ({market_data['usdjpy_change']:+.2f})
- シカゴ先物: {market_data['cme_nikkei_close']:.0f} ({market_data['cme_nikkei_change']:+.0f})

【ニュース】
{news_context}

ブルみんとベアドンの掛け合いで分析してね！"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
        )

        return response.choices[0].message.content
