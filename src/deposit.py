"""
入金宣言スクリプト
使用法: python -m src.deposit <金額>
例:    python -m src.deposit 10000
"""
import sys
import io
import traceback

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        print("使用法: python -m src.deposit <金額>")
        print("例:    python -m src.deposit 10000")
        sys.exit(1)

    try:
        amount = int(sys.argv[1])
    except ValueError:
        print(f"エラー: '{sys.argv[1]}' は有効な金額ではありません（整数で入力してください）")
        sys.exit(1)

    if amount <= 0:
        print("エラー: 金額は正の整数を入力してください")
        sys.exit(1)

    from src.portfolio import Portfolio
    from src.notifier import EmailNotifier

    portfolio = Portfolio().load()
    before_capital = portfolio.total_capital

    portfolio.deposit(amount)

    print(f"入金完了: ¥{amount:,}")
    print(f"総資本: ¥{before_capital:,} → ¥{portfolio.total_capital:,}")
    print(f"累計入金額: ¥{portfolio.total_deposited:,}")
    print(f"新しいロットサイズ: ¥{portfolio.lot_size():,}")

    notifier = EmailNotifier()

    print("メール通知送信中...")
    notifier.send_deposit_email(amount, portfolio, before_capital)
    print("メール通知送信完了")

    print("LINE通知送信中...")
    notifier.send_deposit_line(amount, portfolio, before_capital)
    print("LINE通知送信完了")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"エラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
