# 日経4.3倍ブル 自動売買エージェント 進捗メモ

## 完成済み

- [x] 市場データ自動取得（日経・S&P500・CME先物・NASDAQ・USD/JPY）
- [x] ルールベースシグナル生成（通常¥10,000 / 大変動¥30,000〜50,000）
- [x] ブルみん×ベアドン 掛け合い形式AI分析
- [x] ニュース収集（AlphaVantage + Reuters/CNBC/NHK/Reddit/SeekingAlpha）
- [x] 英語ニュースを日本語に自動翻訳
- [x] メール通知（krdtmhr@gmail.com）
- [x] LINE通知（bull43-agent → Kuroda Tomohiro）
- [x] 毎朝8:00 JST 自動実行 + Twitter自動投稿（GitHub Actions）
- [x] スクショマスキング＋Twitter手動投稿スクリプト（post_screenshot.py）
- [x] GitHubリポジトリ: github.com/krdtmhr/bull-agent（Private）

## Twitter設定手順

### 1. Twitter Developer Portalでアプリ登録
1. https://developer.x.com/en/portal/dashboard にアクセス
2. "Create Project" → アプリ作成
3. "User authentication settings" で OAuth 1.0a を有効化
   - App permissions: **Read and write**
   - Callback URL: https://localhost （ダミーでOK）

### 2. APIキーを取得
"Keys and tokens" タブで以下を取得・コピー：
- API Key → `TWITTER_API_KEY`
- API Key Secret → `TWITTER_API_SECRET`
- Access Token → `TWITTER_ACCESS_TOKEN`
- Access Token Secret → `TWITTER_ACCESS_TOKEN_SECRET`

### 3. GitHub Secretsに登録
https://github.com/krdtmhr/bull-agent/settings/secrets/actions で4つ登録

### 4. ローカル投稿スクリプト用に .env に追記
```
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...
```

## スクショ投稿の使い方

```
python post_screenshot.py          # ファイル選択ダイアログが開く
python post_screenshot.py 画像.png  # ファイル指定
```

- `mask_config.json` でマスクする領域を設定（初期値：上部10%を黒塗り）
- マスク済み画像を確認してからTwitter投稿する確認ステップあり

## mask_config.json の調整

```json
{
  "regions": [
    {
      "name": "ヘッダー（氏名・口座番号）",
      "x1": 0.0, "y1": 0.0,
      "x2": 1.0, "y2": 0.10
    }
  ]
}
```
座標は画像サイズに対する割合（0.0〜1.0）で指定。
実際のスクショを見ながら `y2` などを調整してください。

## 環境情報

| 項目 | 内容 |
|---|---|
| コード場所 | C:\Users\kurod\bull\bull_v2 |
| GitHub | github.com/krdtmhr/bull-agent |
| LINE Bot | bull43-agent（@025cnwns）|
| 運用資金 | ¥100,000（10分割） |
| 通知先 | krdtmhr@gmail.com / LINE / Twitter |
| AI | OpenAI gpt-4o-mini |
| 実行 | 毎朝8:00 JST（平日） |

## 続きを始めるときのClaudeへの伝え方

「bull_v2の続きをやりたい。PROGRESS.mdを見て。」
