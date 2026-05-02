# 日経4.3倍ブル 自動売買エージェント 進捗メモ

## 完成済み

- [x] 市場データ自動取得（日経・S&P500・CME先物・NASDAQ・USD/JPY）
- [x] ルールベースシグナル生成（通常¥10,000 / 大変動¥30,000〜50,000）
- [x] ChatGPT（gpt-4o-mini）によるAI市場分析
- [x] ブルみんキャラクター（初心者向け、売買指示なし、stance形式）
- [x] ニュース収集（AlphaVantage + Reuters/CNBC/NHK/Reddit/SeekingAlpha）
- [x] 英語ニュースを日本語に自動翻訳
- [x] メール通知（krdtmhr@gmail.com）
- [x] LINE通知（bull43-agent → Kuroda Tomohiro）
- [x] 毎朝8:00 JST 自動実行（GitHub Actions）
- [x] GitHubリポジトリ: github.com/krdtmhr/bull-agent（Private）
- [x] LINEチャットボット（判断/残高/履歴/買い/売り コマンド）
- [x] Webダッシュボード（ポートフォリオ・シグナル・取引履歴）
- [x] ポートフォリオ状態の永続化（GitHub APIで保存）

## デプロイ手順（Render.com）

### 1. Render.comアカウント作成・デプロイ
1. https://render.com でサインアップ（GitHubアカウントで連携OK）
2. "New +" → "Web Service"
3. リポジトリ `krdtmhr/bull-agent` を選択
4. 設定は自動（render.yamlから読み込まれる）

### 2. 環境変数をRender.comで設定
Render.comのダッシュボード → サービス → Environment から設定：

| 変数名 | 値 |
|---|---|
| LINE_CHANNEL_ACCESS_TOKEN | LINEのチャンネルアクセストークン |
| LINE_CHANNEL_SECRET | LINEのチャンネルシークレット |
| GITHUB_TOKEN | GitHubのPersonal Access Token（repo権限） |

### 3. GitHub Personal Access Token（PAT）の発行
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token" → repo にチェック → 生成
3. 発行されたトークンをRender.comの GITHUB_TOKEN に設定

### 4. LINE Webhook URLを設定
1. LINE Developers → Messaging API → Webhook URL に設定：
   `https://<render-app-name>.onrender.com/webhook`
2. "Webhook利用する" をオンにして「検証」

### 5. LINEチャンネルシークレットの取得
LINE Developers → Messaging API → チャンネルシークレット をコピー

## LINEコマンド一覧

| コマンド | 内容 |
|---|---|
| 判断 | 今日のシグナルを表示 |
| 残高 | 現在の資金状況 |
| 履歴 | 最近の取引履歴（最大5件） |
| 買い 10000 | ¥10,000の購入を記録 |
| 売り 10000 | ¥10,000の売却を記録 |

## 環境情報

| 項目 | 内容 |
|---|---|
| コード場所 | C:\Users\kurod\bull\bull_v2 |
| GitHub | github.com/krdtmhr/bull-agent |
| LINE Bot | bull43-agent（@025cnwns）|
| 運用資金 | ¥100,000（10分割） |
| 通知先 | krdtmhr@gmail.com / LINE |
| AI | OpenAI gpt-4o-mini |
| 実行 | 毎朝8:00 JST（平日） |
| サーバー | Render.com（無料プラン） |

## 続きを始めるときのClaudeへの伝え方

「bull_v2の続きをやりたい。PROGRESS.mdを見て。」
