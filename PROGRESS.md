# 日経4.3倍ブル 自動売買エージェント 進捗メモ

## 完成済み

- [x] 市場データ自動取得（日経・S&P500・CME先物・NASDAQ・USD/JPY）
- [x] ルールベースシグナル生成（通常¥10,000 / 大変動¥30,000〜50,000）
- [x] ブルみん×ベアドン 掛け合い形式AI分析
  - キャラ設定シートに基づいた語り口・セリフ例を反映
  - 池上彰スタイル：専門用語には必ず括弧で説明を付ける
  - ターゲット：投資完全初心者
  - ルールエンジンのスタンス（BUY/SELL/HOLD）をAIに渡し、AI独自のスタンス出力を禁止
  - シナリオは「上がったら / 下がったら」の2つのみ
- [x] ニュース収集（AlphaVantage + Reuters/CNBC/NHK/Reddit/SeekingAlpha）
- [x] 英語ニュースを日本語に自動翻訳
- [x] メール通知（krdtmhr@gmail.com）
  - 構成：結論 → AI分析 → 数字の解説 → ニュース → 実行手順 → 資金状況
  - 市場データに矢印と日本語説明を付与
  - ニュースはタイトルのみ（URLなし）
  - タイムスタンプを「2026年05月02日 16:57」形式に修正
- [x] LINE通知（bull43-agent → Kuroda Tomohiro）
- [x] 毎朝8:00 JST 自動実行（GitHub Actions）
- [x] GitHubリポジトリ: github.com/krdtmhr/bull-agent（Private）

## 次のステップ（検討中）

### Twitter自動投稿
- 毎朝の分析結果をTwitterにポスト
- 想定内容：今日のスタンス + 日経・S&P500の数字 + ブルみんorベアドンのひとこと
- 取引スクショを撮ってマスキング処理してから投稿する案もあり
- 実装方法：Tweepy（Twitter API v2）+ GitHub Actions secrets に API キーを追加

## キャラクター設定

| キャラ | 役割 | 語り口 |
|---|---|---|
| ブルみん🐂 | 攻め担当・あなた自身の化身 | 明るい・テンション高め・ちょいドジ・感情が出る |
| ベアドン🧊 | 守り・ツッコミ担当 | 短文・ドライ・本質だけ・でも見捨てない |

キャラ設定シート: `chara/■_キャラクター設定シート（ブルみん_ベアドン）.txt`

## 環境情報

| 項目 | 内容 |
|---|---|
| コード場所 | C:\Users\kurod\bull\bull_v2 |
| GitHub | github.com/krdtmhr/bull-agent（Private） |
| LINE Bot | bull43-agent（@025cnwns）|
| 運用資金 | ¥100,000（10分割） |
| 通知先 | krdtmhr@gmail.com / LINE |
| AI | OpenAI gpt-4o-mini |
| 実行 | 毎朝8:00 JST（平日） |

## GitHub Actions 手動トリガー手順

1. GitHub → Actions タブ
2. 左サイドバーの「朝の市場分析」をクリック
3. 右側の「Run workflow」ボタン → Branch: master → 「Run workflow」

## 続きを始めるときのClaudeへの伝え方

「bull_v2の続きをやりたい。PROGRESS.mdを見て。」
