# 日経4.3倍ブル 自動売買エージェント 進捗メモ

## 完成済み

- [x] 市場データ自動取得（日経・S&P500・CME先物・NASDAQ・USD/JPY）
- [x] ルールベースシグナル生成（通常¥10,000 / 大変動¥30,000〜50,000）
- [x] ChatGPT（gpt-4o-mini）によるAI市場分析
- [x] メール通知（krdtmhr@gmail.com）
- [x] LINE通知（bull43-agent → Kuroda Tomohiro）
- [x] 毎朝8:00 JST 自動実行（GitHub Actions）
- [x] GitHubリポジトリ: github.com/krdtmhr/bull-agent（Private）

## 次のステップ

- [ ] LINEチャットボット（売買記録・残高確認・手動分析トリガー）
  - `判断` → 今日のシグナルを返す
  - `買い 10000` → ¥10,000の購入を記録
  - `売り 10000` → ¥10,000の売却を記録
  - `残高` → ポジション・資金状況
  - `履歴` → 直近の取引履歴
  - 実装にはRender.com（無料）でサーバーが必要

- [ ] Webダッシュボード
  - 取引履歴・ポジション・損益をブラウザで確認
  - Render.comで同じサーバーに同居させる

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

## 続きを始めるときのClaudeへの伝え方

「bull_v2の続きをやりたい。PROGRESS.mdを見て。次はLINEチャットボットから。」
