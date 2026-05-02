import smtplib
import ssl
import urllib.request
import urllib.parse
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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

        action_summary = {
            "BUY": "📈 強気寄り  ＝  攻めの日",
            "SELL": "📉 慎重寄り  ＝  守りの日",
            "HOLD": "⏸️ 様子見  ＝  待ちの日",
        }
        action_meaning = {
            "BUY": "相場に上昇の気配があります。\n  小さく動いてみるのも一つの選択肢です。",
            "SELL": "相場に警戒信号が出ています。\n  急いで動かないのが賢明かもしれません。",
            "HOLD": "今日は方向感がはっきりしません。\n  「何もしない」という判断も、立派な投資の技術です。",
        }
        action_instructions = {
            "BUY": f"楽天証券にログイン → 楽天日本株式4.3倍ブル を検索\n参考金額: ¥{rule_signal.amount:,}（最終判断はご自身で）",
            "SELL": f"楽天証券にログイン → 楽天日本株式4.3倍ブル を検索\n参考金額: ¥{rule_signal.amount:,}（最終判断はご自身で）",
            "HOLD": "今日は相場の様子をながめるだけでOKです。\n（「動かない」も立派な投資判断です）",
        }

        pct = rule_signal.confidence * 100
        filled = round(pct / 20)
        confidence_bar = "●" * filled + "○" * (5 - filled)

        # 読みやすいタイムスタンプ
        try:
            dt = datetime.fromisoformat(portfolio.last_updated)
            updated = dt.strftime("%Y年%m月%d日 %H:%M")
        except Exception:
            updated = portfolio.last_updated[:16]

        # 市場データの矢印と説明
        def arrow(val):
            return "↑ 上昇" if val >= 0 else "↓ 下落"

        if data.usdjpy_rate >= 150:
            usdjpy_note = "円安（1ドルが高い＝輸出企業に有利）"
        else:
            usdjpy_note = "円高（1ドルが安い＝輸入企業に有利）"

        cme_warn = "  ⚠️ 日本株の明日の見通しはマイナス" if data.cme_nikkei_change < 0 else "  ✅ 日本株の明日の見通しはプラス"

        # ニュース（タイトルのみ・URLなし）
        news_section = ""
        if news_items:
            news_lines = ["【気になるニュース（世界の動き）】"]
            for i, item in enumerate(news_items[:5], 1):
                news_lines.append(f"  {i}. {item.title}")
            news_section = "\n".join(news_lines) + "\n\n"

        return f"""🐂×🧊 ブルみん×ベアドン 朝ナビ - {today}
{"=" * 46}
おはよう！今日もチェックしてくれてありがとう。
夢は推せ。でも、ちゃんと考えて推せ。

{"=" * 46}
  ▼ 今日の結論

  {action_summary[rule_signal.action]}

  {action_meaning[rule_signal.action]}

  AIの確信度：{confidence_bar} {pct:.0f}%
  （●が多いほど、この判断への自信が高い）

{"=" * 46}
【ブルみん×ベアドンの分析】

{ai_analysis}

{"=" * 46}
【今日の数字を1分で理解しよう】

📌 日本の株価（日経225）
   {data.nikkei_close:,.0f}円  {arrow(data.nikkei_change)}（前日比 {data.nikkei_change:+,.0f}円）

📌 アメリカの株価（S&P500）
   {data.sp500_close:,.2f}  {arrow(data.sp500_change)}（前日比 {data.sp500_change:+,.2f}）

📌 明日の日本株の見通し（シカゴ先物）
   {data.cme_nikkei_close:,.0f}円  {arrow(data.cme_nikkei_change)}（前日比 {data.cme_nikkei_change:+,.0f}円）{cme_warn}
   ※ アメリカ市場で夜間に取引される「明日の日本株の予測値」

📌 ドル・円（為替）
   1ドル = {data.usdjpy_rate:.2f}円  {usdjpy_note}

{"=" * 46}
{news_section}{"=" * 46}
【実行手順】
{action_instructions[rule_signal.action]}

{"=" * 46}
【あなたの資金状況】
総資本：        ¥{portfolio.total_capital:,}
使える資金：    ¥{portfolio.available_capital:,}
投資中の金額：  ¥{portfolio.current_position_value:,}
投資枠：        {portfolio.parts_used()}/10（残り{portfolio.parts_available()}枠）
累計取引回数：  {portfolio.trade_count}回
最終更新：      {updated}

{"=" * 46}
※ 投資は自己責任です。このメールはあくまで参考情報です。
"""

    def send_line(self, rule_signal: RuleSignal, market_data: MarketData, news_items: "list[NewsItem] | None" = None):
        if not config.LINE_CHANNEL_ACCESS_TOKEN or not config.LINE_USER_ID:
            return
        if news_items is None:
            news_items = []
        today = datetime.now().strftime("%Y-%m-%d")
        stance_map = {"BUY": "📈 強気寄り（攻めの日）", "SELL": "📉 慎重寄り（守りの日）", "HOLD": "⏸️ 様子見（待ちの日）"}
        stance = stance_map.get(rule_signal.action, "⏸️ 様子見")

        nikkei_arrow = "↑" if market_data.nikkei_change >= 0 else "↓"
        cme_arrow = "↑" if market_data.cme_nikkei_change >= 0 else "↓"

        news_lines = ""
        if news_items:
            headlines = []
            for i, item in enumerate(news_items[:3], 1):
                headlines.append(f"{i}. {item.title}")
            news_lines = "\n\n📰 気になるニュース\n" + "\n".join(headlines)

        text = (
            f"おはよう！ブルみん×ベアドンだよ🐂🧊\n"
            f"今日もチェックしてくれてありがとう！\n\n"
            f"【{today} の結論】\n"
            f"{stance}\n\n"
            f"📊 マーケット速報\n"
            f"日本株（日経225）: {market_data.nikkei_close:,.0f}円 {nikkei_arrow}({market_data.nikkei_change:+.0f})\n"
            f"アメリカ株（S&P500）: {market_data.sp500_close:,.2f} ({market_data.sp500_change:+.2f})\n"
            f"明日の日本株予測: {market_data.cme_nikkei_close:,.0f}円 {cme_arrow}({market_data.cme_nikkei_change:+.0f})\n"
            f"ドル円: {market_data.usdjpy_rate:.2f}円"
            f"{news_lines}\n\n"
            f"詳しい分析はメールをチェックしてね！\n"
            f"夢は推せ。でも、ちゃんと考えて推せ。🌟"
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
