"""
売買実行後の報告・コンテンツ配信スクリプト
使用法: python -m src.report

実行タイミング:
  1. 楽天証券で売買を実行する
  2. 約定画面のスクショを撮る
  3. 件名「BUY」「SELL」「HOLD」でスクショをメール送信
  4. このスクリプトを実行する

スクリプトが行うこと:
  - 受信メールからスクショと売買内容を取得
  - ポートフォリオ状態を更新（口数・金額はシステムが自動計算）
  - 売買結果を織り込んだコンテンツを生成
  - メール・LINEに配信
"""
import sys
import io
import traceback
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def main():
    from src.mail_receiver import fetch_trade_screenshot
    from src.portfolio import Portfolio
    from src.market_data import fetch_market_data
    from src.notifier import EmailNotifier

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 売買報告処理開始")

    # ① スクショメールを受信
    print("スクショメールを確認中...")
    result = fetch_trade_screenshot()

    if result is None:
        print("本日の売買メールが見つかりませんでした。")
        print("件名「BUY」「SELL」「HOLD」でスクショをメール送信後、再実行してください。")
        sys.exit(1)

    action   = result["action"]
    shot     = result["screenshot"]
    received = result["received_at"]

    print(f"売買内容: {action}")
    print(f"スクショ: {shot or '添付なし'}")
    print(f"受信時刻: {received}")

    # ② ポートフォリオ更新
    portfolio = Portfolio().load()
    lot = portfolio.lot_size()

    if action == "BUY":
        if portfolio.at_max_parts():
            action = "HOLD"
            trade_summary = f"⚠️ 最大口数（{config.MAX_PARTS}口）に達しているため買い注文できませんでした"
        elif not portfolio.can_buy(lot):
            action = "HOLD"
            trade_summary = f"⚠️ 資金不足のため買い注文できませんでした（必要：¥{lot:,} / 空き：¥{portfolio.available_capital:,}）"
        else:
            portfolio.record_trade("BUY", lot)
            trade_summary = f"¥{lot:,} 買い注文を実行しました（1口）"
    elif action == "SELL":
        if portfolio.parts_used() == 0:
            action = "HOLD"
            trade_summary = "⚠️ 保有口数がないため解約できませんでした"
        else:
            specified = result.get("sell_parts", 0)
            sell_parts = specified if specified > 0 else (portfolio.last_sell_parts or portfolio.parts_used())
            sell_parts = min(sell_parts, portfolio.parts_used())
            sell_amount = sell_parts * lot
            portfolio.record_trade("SELL", sell_amount)
            trade_summary = f"{sell_parts}口（¥{sell_amount:,}）解約を実行しました"
    else:
        trade_summary = "本日は様子見（売買なし）"

    print(f"ポートフォリオ更新: {trade_summary}")

    # ③ 市場データ取得
    print("市場データ取得中...")
    data = fetch_market_data()

    # ④ コンテンツ配信
    notifier = EmailNotifier()
    print("報告メール送信中...")
    notifier.send_report_email(action, trade_summary, shot, data, portfolio)
    print("報告メール送信完了")

    print("LINE通知送信中...")
    notifier.send_report_line(action, trade_summary, data, portfolio, shot)
    print("LINE通知送信完了")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 完了")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
