import smtplib
import ssl
import urllib.request
import urllib.parse
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import config
from src.signal_engine import RuleSignal
from src.market_data import MarketData
from src.portfolio import Portfolio


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
    ):
        today = datetime.now().strftime("%Y-%m-%d")
        action_label = rule_signal.action
        amount_str = f"¥{rule_signal.amount:,}" if rule_signal.action != "HOLD" else "-"

        subject = f"【投資シグナル】{action_label} {amount_str} - 日経4.3ブル ({today})"

        body = self._build_body(rule_signal, ai_analysis, market_data, portfolio, today)

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
    ) -> str:
        action_instructions = {
            "BUY": f"楽天証券にログイン → 日経平均ブル4.3倍ETF を検索 → 金額指定で ¥{rule_signal.amount:,} を購入",
            "SELL": f"楽天証券にログイン → 日経平均ブル4.3倍ETF を検索 → 金額指定で ¥{rule_signal.amount:,} を売却",
            "HOLD": "本日は売買なし。市場の動向を引き続き監視してください。",
        }

        return f"""日経4.3倍ブル 自動分析レポート - {today}
{"=" * 50}

【市場データサマリー】
┌─────────────────────────────────────────┐
│ 指標           │ 現値        │ 前日比      │
├─────────────────────────────────────────┤
│ 日経225        │ {data.nikkei_close:>10.0f} │ {data.nikkei_change:>+8.0f} ({data.nikkei_change_pct:>+5.2f}%) │
│ S&P500         │ {data.sp500_close:>10.2f} │ {data.sp500_change:>+8.2f} ({data.sp500_change_pct:>+5.2f}%) │
│ NASDAQ         │ {data.nasdaq_close:>10.2f} │ {data.nasdaq_change:>+8.2f} ({data.nasdaq_change_pct:>+5.2f}%) │
│ USD/JPY        │ {data.usdjpy_rate:>10.2f} │ {data.usdjpy_change:>+8.2f} ({data.usdjpy_change_pct:>+5.2f}%) │
│ CME日経先物    │ {data.cme_nikkei_close:>10.0f} │ {data.cme_nikkei_change:>+8.0f} ({data.cme_nikkei_change_pct:>+5.2f}%) │
└─────────────────────────────────────────┘

{"=" * 50}
【ルールベースシグナル】
アクション: {rule_signal.action}
金額:       {f"¥{rule_signal.amount:,}" if rule_signal.action != "HOLD" else "-"}
確信度:     {rule_signal.confidence * 100:.0f}%
根拠:       {rule_signal.reason}

{"=" * 50}
【AI分析】
{ai_analysis}

{"=" * 50}
【実行手順】
{action_instructions[rule_signal.action]}

{"=" * 50}
【ポートフォリオ状況】
総資本:         ¥{portfolio.total_capital:,}
利用可能資金:   ¥{portfolio.available_capital:,}
保有ポジション: ¥{portfolio.current_position_value:,}
使用枠:         {portfolio.parts_used()}/10
残枠:           {portfolio.parts_available()}/10
累計取引回数:   {portfolio.trade_count}回
最終更新:       {portfolio.last_updated}

{"=" * 50}
※ このメールは自動生成です。最終的な売買判断はご自身の責任で行ってください。
"""

    def send_line(self, rule_signal: RuleSignal, market_data: MarketData):
        if not config.LINE_CHANNEL_ACCESS_TOKEN or not config.LINE_USER_ID:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        action_emoji = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️"}.get(rule_signal.action, "")
        amount_str = f"¥{rule_signal.amount:,}" if rule_signal.action != "HOLD" else "-"
        text = (
            f"{action_emoji}【投資シグナル】{rule_signal.action} {amount_str}\n"
            f"日付: {today}\n"
            f"確信度: {rule_signal.confidence * 100:.0f}%\n\n"
            f"日経225: {market_data.nikkei_close:.0f} ({market_data.nikkei_change:+.0f})\n"
            f"S&P500: {market_data.sp500_close:.2f} ({market_data.sp500_change:+.2f})\n"
            f"CME先物: {market_data.cme_nikkei_close:.0f} ({market_data.cme_nikkei_change:+.0f})\n"
            f"USD/JPY: {market_data.usdjpy_rate:.2f}\n\n"
            f"根拠: {rule_signal.reason}"
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
