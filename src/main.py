import sys
import traceback
from datetime import datetime

from src.market_data import fetch_market_data
from src.signal_engine import generate_rule_signal
from src.portfolio import Portfolio
from src.notifier import EmailNotifier
from src.news_collector import fetch_news, format_news_for_ai, translate_titles
import config


def get_ai_provider():
    if config.AI_PROVIDER == "openai":
        from src.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    raise ValueError(f"未対応のAIプロバイダー: {config.AI_PROVIDER}")


def combine_confidence(rule_signal, ai_analysis: str) -> float:
    ai_agrees = (
        (rule_signal.action == "BUY" and ("強気" in ai_analysis or "買" in ai_analysis))
        or (rule_signal.action == "SELL" and ("慎重" in ai_analysis or "売" in ai_analysis))
        or (rule_signal.action == "HOLD" and ("様子見" in ai_analysis or "ホールド" in ai_analysis))
    )
    if ai_agrees:
        return min(0.95, rule_signal.confidence + 0.1)
    return max(0.1, rule_signal.confidence - 0.1)


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 分析開始")

    portfolio = Portfolio().load()
    print(f"ポートフォリオ読み込み完了: 利用可能 ¥{portfolio.available_capital:,} / 保有 ¥{portfolio.current_position_value:,}")

    print("市場データ取得中...")
    data = fetch_market_data()
    print(f"日経: {data.nikkei_close:.0f} ({data.nikkei_change:+.0f}) / S&P500: {data.sp500_close:.2f} ({data.sp500_change:+.2f}) / CME先物: {data.cme_nikkei_close:.0f} ({data.cme_nikkei_change:+.0f})")

    rule_signal = generate_rule_signal(data)
    print(f"ルールシグナル: {rule_signal.action} ¥{rule_signal.amount:,} (確信度: {rule_signal.confidence * 100:.0f}%)")

    print("ニュース収集中...")
    news_items = fetch_news()
    news_items = translate_titles(news_items)
    news_context = format_news_for_ai(news_items)
    print(f"ニュース取得完了: {len(news_items)}件")

    print("AI分析実行中...")
    ai_provider = get_ai_provider()
    market_dict = {
        "nikkei_close": data.nikkei_close,
        "nikkei_change": data.nikkei_change,
        "nikkei_change_pct": data.nikkei_change_pct,
        "sp500_close": data.sp500_close,
        "sp500_change": data.sp500_change,
        "sp500_change_pct": data.sp500_change_pct,
        "nasdaq_close": data.nasdaq_close,
        "nasdaq_change": data.nasdaq_change,
        "nasdaq_change_pct": data.nasdaq_change_pct,
        "dow_close": data.dow_close,
        "dow_change": data.dow_change,
        "dow_change_pct": data.dow_change_pct,
        "usdjpy_rate": data.usdjpy_rate,
        "usdjpy_change": data.usdjpy_change,
        "usdjpy_change_pct": data.usdjpy_change_pct,
        "cme_nikkei_close": data.cme_nikkei_close,
        "cme_nikkei_change": data.cme_nikkei_change,
        "cme_nikkei_change_pct": data.cme_nikkei_change_pct,
    }
    stance_label = {"BUY": "強気寄り", "SELL": "慎重寄り", "HOLD": "様子見"}
    market_dict["stance"] = rule_signal.action
    market_dict["stance_label"] = stance_label[rule_signal.action]
    ai_analysis = ai_provider.analyze(market_dict, news_context)

    combined_confidence = combine_confidence(rule_signal, ai_analysis)
    print(f"総合確信度: {combined_confidence * 100:.0f}%")

    portfolio.last_signal_action = rule_signal.action
    portfolio.last_signal_reason = rule_signal.reason
    portfolio.last_signal_date = datetime.now().strftime("%Y-%m-%d")
    portfolio.last_signal_confidence = combined_confidence
    portfolio.save()

    print("メール送信中...")
    notifier = EmailNotifier()
    notifier.send_signal_email(rule_signal, ai_analysis, data, portfolio, news_items[:5])
    print("メール送信完了")

    print("LINE通知送信中...")
    notifier.send_line(rule_signal, data, news_items[:3])
    print("LINE通知送信完了")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 分析完了")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"エラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc()
        try:
            notifier = EmailNotifier()
            notifier.send_error_email(e)
            print("エラーメール送信完了")
        except Exception as mail_err:
            print(f"エラーメール送信失敗: {mail_err}", file=sys.stderr)
        sys.exit(1)
