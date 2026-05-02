import smtplib
import ssl
import urllib.request
import urllib.parse
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import TYPE_CHECKING

import config
from src.signal_engine import RuleSignal
from src.market_data import MarketData
from src.portfolio import Portfolio

if TYPE_CHECKING:
    from src.news_collector import NewsItem


class EmailNotifier:
    def __init__(self):
        self.smtp_host = config.SMTP_HOST
        self.smtp_port = config.SMTP_PORT
        self.email_from = config.EMAIL_FROM
        self.email_to = config.EMAIL_TO
        self.password = config.EMAIL_PASSWORD

    def send_signal_email(
        self,
        rule_signal: RuleSignal,
        ai_analysis: str,
        market_data: MarketData,
        portfolio: Portfolio,
        news_items: "list[NewsItem] | None" = None,
    ):
        today = datetime.now().strftime("%Y-%m-%d")
        subject_map = {
            "BUY": f"【📈 強気寄り】ブルみん×ベアドン 朝ナビ ({today})",
            "SELL": f"【📉 慎重寄り】ブルみん×ベアドン 朝ナビ ({today})",
            "HOLD": f"【⏸️ 様子見】ブルみん×ベアドン 朝ナビ ({today})",
        }
        subject = subject_map[rule_signal.action]

        body = self._build_body(rule_signal, ai_analysis, market_data, portfolio, today, news_items or [])

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = self.email_to
        msg.attach(MIMEText(body, "plain", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
            server.login(self.email_from, self.password)
            server.sendmail(self.email_from, self.email_to, msg.as_string())

    def _build_body(
        self,
        rule_signal: RuleSignal,
        ai_analysis: str,
        data: MarketData,
        portfolio: Portfolio,
        today: str,
        news_items: "list[NewsItem]" = None,
    ) -> str:
        if news_items is None:
            news_items = []

        action_headers = {
            "BUY": "📈 今日のスタンス：強気寄り",
            "SELL": "📉 今日のスタンス：慎重寄り",
            "HOLD": "⏸️ 今日のスタンス：様子見",
        }
        action_explanations = {
            "BUY": "市場に上昇の方向感が見られます。ただし、相場は必ず上下します。",
            "SELL": "市場に慎重な方向感が見られます。無理に動く必要はありません。",
            "HOLD": "方向感が読みにくい状態です。「何もしない」も立派な判断ですよ。",
        }
        action_instructions = {
            "BUY": f"楽天証券にログイン → 楽天日本株式4.3倍ブル を検索\n参考金額: ¥{rule_signal.amount:,}（最終判断はご自身で）",
            "SELL": f"楽天証券にログイン → 楽天日本株式4.3倍ブル を検索\n参考金額: ¥{rule_signal.amount:,}（最終判断はご自身で）",
            "HOLD": "今日は相場の様子をながめるだけでもOKです。",
        }

        pct = rule_signal.confidence * 100
        filled = round(pct / 20)
        confidence_bar = "●" * filled + "○" * (5 - filled)
        confidence_display = f"AIの確信度: {confidence_bar} {pct:.0f}%"

        news_section = ""
        if news_items:
            news_lines = ["【最新ニュース（トップ5）】"]
            for i, item in enumerate(news_items[:5], 1):
                sentiment_tag = f"[{item.sentiment}] " if item.sentiment != "不明" else ""
                news_lines.append(f"{i}. {sentiment_tag}{item.source}: {item.title}")
                if item.url:
                    news_lines.append(f"   🔗 {item.url}")
            news_section = "\n".join(news_lines) + "\n\n" + "=" * 50 + "\n"

        return f"""🐂×🧊 ブルみん×ベアドン 朝ナビ - {today}
{"=" * 50}
おはよう！今日もチェックしてくれてありがとう。
夢は推せ。でも、ちゃんと考えて推せ。

{action_headers[rule_signal.action]}
{action_explanations[rule_signal.action]}
{confidence_display}
根拠: {rule_signal.reason}

{"=" * 50}
【市場データサマリー】
┌─────────────────────────────────────────┐
│ 指標                   │ 現値        │ 前日比      │
├─────────────────────────────────────────┤
│ 日経225                │ {data.nikkei_close:>10.0f} │ {data.nikkei_change:>+8.0f} ({data.nikkei_change_pct:>+5.2f}%) │
│ S&P500                 │ {data.sp500_close:>10.2f} │ {data.sp500_change:>+8.2f} ({data.sp500_change_pct:>+5.2f}%) │
│ NASDAQ                 │ {data.nasdaq_close:>10.2f} │ {data.nasdaq_change:>+8.2f} ({data.nasdaq_change_pct:>+5.2f}%) │
│ USD/JPY                │ {data.usdjpy_rate:>10.2f} │ {data.usdjpy_change:>+8.2f} ({data.usdjpy_change_pct:>+5.2f}%) │
│ シカゴ先物（アメリカでの日経予測値） │ {data.cme_nikkei_close:>10.0f} │ {data.cme_nikkei_change:>+8.0f} ({data.cme_nikkei_change_pct:>+5.2f}%) │
└─────────────────────────────────────────┘

{"=" * 50}
{news_section}【AI分析】
{ai_analysis}

{"=" * 50}
【実行手順】
{action_instructions[rule_signal.action]}

{"=" * 50}
【あなたの資金状況】
総資本:             ¥{portfolio.total_capital:,}
使える資金:         ¥{portfolio.available_capital:,}
現在持っている金額: ¥{portfolio.current_position_value:,}
投資中の枠:         {portfolio.parts_used()}/10
残枠:               {portfolio.parts_available()}/10
累計取引回数:       {portfolio.trade_count}回
最終更新:           {portfolio.last_updated}

{"=" * 50}
※ 投資は自己責任です。このメールはあくまで参考情報です。
"""

    def send_line(self, rule_signal: RuleSignal, market_data: MarketData, news_items: "list[NewsItem] | None" = None):
        if not config.LINE_CHANNEL_ACCESS_TOKEN or not config.LINE_USER_ID:
            return
        if news_items is None:
            news_items = []
        today = datetime.now().strftime("%Y-%m-%d")
        stance_map = {"BUY": "📈 強気寄り", "SELL": "📉 慎重寄り", "HOLD": "⏸️ 様子見"}
        stance = stance_map.get(rule_signal.action, "⏸️ 様子見")
        news_lines = ""
        if news_items:
            headlines = []
            for i, item in enumerate(news_items[:3], 1):
                headlines.append(f"{i}. {item.title}")
            news_lines = "\n\n📰 気になるニュース\n" + "\n".join(headlines)
        text = (
            f"おはよう！ブルみん×ベアドンだよ🐂🧊\n"
            f"今日もチェックしてくれてありがとう！\n\n"
            f"【{today} の朝ナビ】\n"
            f"今日のスタンス：{stance}\n\n"
            f"📊 マーケット速報\n"
            f"日経225: {market_data.nikkei_close:.0f}円 ({market_data.nikkei_change:+.0f})\n"
            f"S&P500: {market_data.sp500_close:.2f} ({market_data.sp500_change:+.2f})\n"
            f"シカゴ先物: {market_data.cme_nikkei_close:.0f} ({market_data.cme_nikkei_change:+.0f})\n"
            f"ドル円: {market_data.usdjpy_rate:.2f}円"
            f"{news_lines}\n\n"
            f"詳しい分析はメールをチェックしてね！\n"
            f"夢は推せ。でも、ちゃんと考えて推せ。🌟\n"
            f"Twitterでもブルみんのリアル投資を配信中！"
        )
        data = json.dumps({"to": config.LINE_USER_ID, "messages": [{"type": "text", "text": text}]}).encode("utf-8")
        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.LINE_CHANNEL_ACCESS_TOKEN}"},
        )
        urllib.request.urlopen(req)

    def send_error_email(self, error: Exception):
        today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        subject = f"【エラー】日経4.3ブル 分析スクリプト異常終了 ({today})"
        body = f"""分析スクリプトがエラーで終了しました。

日時: {today}
エラー: {type(error).__name__}
詳細: {str(error)}

スクリプトを確認してください。
"""
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = self.email_to
        msg.attach(MIMEText(body, "plain", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
            server.login(self.email_from, self.password)
            server.sendmail(self.email_from, self.email_to, msg.as_string())
