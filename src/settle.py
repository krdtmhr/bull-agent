"""
SELL翌日に楽天証券から約定金額を自動取得してポートフォリオを更新する。
使用法: python -m src.settle
"""
import sys
import io
import traceback
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def main():
    from src.settle_scraper import fetch_settlement_amount
    from src.portfolio import Portfolio
    from src.notifier import EmailNotifier

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 約定金額取得開始")

    amount = fetch_settlement_amount()

    if amount is None:
        print("約定金額を取得できませんでした。手動で確認してください。")
        sys.exit(1)

    print(f"約定金額: ¥{amount:,}")

    # ポートフォリオを更新（受取金額で available_capital を補正）
    portfolio = Portfolio().load()
    before = portfolio.total_capital

    # 解約で戻ってくる金額を反映（record_trade で引いた簿価と差し替え）
    # current_position_value はすでに record_trade("SELL") で減らしてある
    # available_capital を実際の受取額に合わせる
    diff = amount - (portfolio.available_capital - (before - portfolio.current_position_value - portfolio.available_capital))
    portfolio.available_capital = portfolio.available_capital + diff if diff else portfolio.available_capital
    portfolio.total_capital = portfolio.available_capital + portfolio.current_position_value
    portfolio.save()

    print(f"ポートフォリオ更新完了")
    print(f"  総資本: ¥{portfolio.total_capital:,}")
    print(f"  空き資金: ¥{portfolio.available_capital:,}")

    # 通知
    notifier = EmailNotifier()
    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"💰 約定金額確定 ¥{amount:,} ({today})"
    body = f"""約定金額が確定しました。

約定金額：¥{amount:,}
総資本（更新後）：¥{portfolio.total_capital:,}
空き資金：¥{portfolio.available_capital:,}
投資中：¥{portfolio.current_position_value:,}
"""
    import smtplib, ssl
    import config
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_FROM
    msg["To"] = config.EMAIL_TO
    msg.attach(MIMEText(body, "plain", "utf-8"))
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, context=ctx) as s:
        s.login(config.EMAIL_FROM, config.EMAIL_PASSWORD)
        s.sendmail(config.EMAIL_FROM, config.EMAIL_TO, msg.as_string())
    print("通知メール送信完了")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
