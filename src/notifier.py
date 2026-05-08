import os
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
        sell_parts: int = 0,
    ):
        today = datetime.now().strftime("%Y-%m-%d")
        subject_map = {
            "BUY": f"【📈 本日のシグナル：強気寄り】操作指示 ({today})",
            "SELL": f"【📉 本日のシグナル：慎重寄り】操作指示 ({today})",
            "HOLD": f"【⏸️ 本日のシグナル：様子見】操作指示 ({today})",
        }
        subject = subject_map[rule_signal.action]
        body = self._build_body(rule_signal, ai_analysis, market_data, portfolio, today, news_items or [], sell_parts)

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
        sell_parts: int = 0,
    ) -> str:
        if news_items is None:
            news_items = []

        action_summary = {
            "BUY": "📈 強気寄り  ＝  攻めの日",
            "SELL": "📉 慎重寄り  ＝  守りの日",
            "HOLD": "⏸️ 様子見  ＝  待ちの日",
        }
        action_meaning = {
            "BUY": "下落局面での押し目。\n  今日は買い注文を入れたよ！。",
            "SELL": "上昇局面での利益確定。\n  今日は解約注文を入れたよ！。",
            "HOLD": "今日は方向感がなし。\n  「動かない」も立派な投資判断！",
        }
        # SELL操作の文言を口数に応じて動的生成
        sell_amount = sell_parts * portfolio.lot_size()
        held_parts = portfolio.parts_used()
        if sell_parts == 0:
            sell_instruction = (
                "⏸️ 保有なし（解約対象なし）\n\n"
                "  現在4.3倍ブルの保有がありません。"
            )
        elif sell_parts >= held_parts:
            sell_instruction = (
                f"✅ 今日の操作：全部解約 {sell_parts}口（¥{sell_amount:,}）\n\n"
                f"  ① 楽天証券にログイン\n"
                f"  ② 投資信託 →「楽天日本株式4.3倍ブル」を選択\n"
                f"  ③「解約」→ 全額指定\n"
                f"  ④ 注文確定"
            )
        else:
            sell_instruction = (
                f"✅ 今日の操作：一部解約 {sell_parts}口（¥{sell_amount:,}）\n\n"
                f"  ① 楽天証券にログイン\n"
                f"  ② 投資信託 →「楽天日本株式4.3倍ブル」を選択\n"
                f"  ③「解約」→ 口数指定：{sell_parts}口\n"
                f"  ④ 注文確定\n"
                f"  ※ 残り{held_parts - sell_parts}口は引き続き保有"
            )

        action_instructions = {
            "BUY": (
                f"✅ 今日の操作：買い注文 ¥{rule_signal.amount:,}\n\n"
                f"  ① 楽天証券にログイン\n"
                f"  ② 投資信託 →「楽天日本株式4.3倍ブル」を検索\n"
                f"  ③ 「買付」→ 金額指定：¥{rule_signal.amount:,}\n"
                f"  ④ 注文確定"
            ),
            "SELL": sell_instruction,
            "HOLD": (
                "⏸️ 今日の操作：なし\n\n"
                "  今日は相場の様子を見るだけでOK。\n"
                "  何もしないのが今日の正解です。"
            ),
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

        def icon(val):
            return "⬆️" if val >= 0 else "⬇️"

        if data.usdjpy_rate >= 150:
            usdjpy_note = "円安（1ドルが高い＝輸出企業に有利）"
        else:
            usdjpy_note = "円高（1ドルが安い＝輸入企業に有利）"

        cme_warn = "  ⚠️ 日本株の明日の見通しはマイナス" if data.cme_nikkei_change < 0 else "  ✅ 日本株の明日の見通しはプラス"

        vix = data.vix_close
        if vix >= 30:
            vix_label = "🚨 危険水準（大荒れに注意）"
        elif vix >= 25:
            vix_label = "⚠️ 警戒水準（荒れやすい）"
        elif vix >= 20:
            vix_label = "😟 やや不安定"
        else:
            vix_label = "😌 落ち着いている"

        us10y_note = "金利上昇中（株の下押し要因）" if data.us10y_change > 0 else "金利低下中（株の支援要因）"

        # ニュース（タイトルのみ・URLなし）
        news_section = ""
        if news_items:
            news_lines = ["【気になるニュース（世界の動き）】"]
            for i, item in enumerate(news_items[:5], 1):
                news_lines.append(f"  {i}. {item.title}")
            news_section = "\n".join(news_lines) + "\n\n"

        data_label = f"  ※ データ基準日：{data.data_as_of}（終値）\n" if data.data_as_of else ""

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
{data_label}
{icon(data.nikkei_change)} 日本の株価（日経225）
   {data.nikkei_close:,.0f}円  {arrow(data.nikkei_change)}（前日比 {data.nikkei_change:+,.0f}円）

{icon(data.sp500_change)} アメリカの株価（S&P500）
   {data.sp500_close:,.2f}  {arrow(data.sp500_change)}（前日比 {data.sp500_change:+,.2f}）

{icon(data.cme_nikkei_change)} 明日の日本株の見通し（シカゴ先物）
   {data.cme_nikkei_close:,.0f}円  {arrow(data.cme_nikkei_change)}（前日比 {data.cme_nikkei_change:+,.0f}円）{cme_warn}
   ※ アメリカ市場で夜間に取引される「明日の日本株の予測値」

{icon(data.usdjpy_change)} ドル・円（為替）
   1ドル = {data.usdjpy_rate:.2f}円  {usdjpy_note}

{icon(data.vix_change)} VIX（恐怖指数・市場の不安度）
   {data.vix_close:.2f}  {vix_label}（前日比 {data.vix_change:+.2f}）
   ※ 20以下：安定、25超：警戒、30超：大荒れ注意（4.3倍ブルに直撃）

{icon(data.us10y_change)} 米国10年債利回り（金利）
   {data.us10y_rate:.2f}%  {us10y_note}（前日比 {data.us10y_change:+.2f}%）
   ※ 金利が上がると株が下がりやすい傾向がある

{"=" * 46}
{news_section}{"=" * 46}
【今日の操作】
{action_instructions[rule_signal.action]}

{"=" * 46}
【あなたの資金状況】
総資本：        ¥{portfolio.total_capital:,}
使える資金：    ¥{portfolio.available_capital:,}
投資中の金額：  ¥{portfolio.current_position_value:,}
投資枠：        {portfolio.parts_used()}/{config.MAX_PARTS}口（残り{portfolio.parts_available()}枠）
1口サイズ：     ¥{portfolio.lot_size():,}（複利ロット）
累計入金額：    ¥{portfolio.total_deposited:,}
累計取引回数：  {portfolio.trade_count}回
最終更新：      {updated}

{"=" * 46}
※ 投資は自己責任です。このメールはあくまで参考情報です。
"""

    def send_deposit_email(self, amount: int, portfolio: Portfolio, before_capital: int):
        today = datetime.now().strftime("%Y-%m-%d")
        subject = f"【💰 入金完了】ブルみん×ベアドン ({today})"
        new_lot = portfolio.lot_size()
        body = f"""💰 入金完了のお知らせ - {today}
{"=" * 46}

ブルみん: やった〜！¥{amount:,} 入金されたよ！
         お金が増えると、作戦の幅が広がるね💪

ベアドン: 浮かれるな。
         1口の金額が変わったから確認しておけ。

{"=" * 46}
【入金内容】

  入金額：        ¥{amount:,}
  入金前の総資本：¥{before_capital:,}
  入金後の総資本：¥{portfolio.total_capital:,}
  累計入金額：    ¥{portfolio.total_deposited:,}

{"=" * 46}
【新しいロットサイズ（複利ロット）】

  1口あたり：¥{new_lot:,}
  （総資本×10%、¥10,000〜¥15,000の範囲）

  ブルみん: 明日からこのサイズで買い注文を入れてね！
  ベアドン: 算式: max(¥10,000, min(¥15,000, 総資本×10%))

{"=" * 46}
【資金状況】

  総資本：      ¥{portfolio.total_capital:,}
  使える資金：  ¥{portfolio.available_capital:,}
  投資中：      ¥{portfolio.current_position_value:,}
  投資枠：      {portfolio.parts_used()}/{5}口（残り{portfolio.parts_available()}枠）

{"=" * 46}
※ 投資は自己責任です。このメールはあくまで参考情報です。
"""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = self.email_to
        msg.attach(MIMEText(body, "plain", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
            server.login(self.email_from, self.password)
            server.sendmail(self.email_from, self.email_to, msg.as_string())

    def send_deposit_line(self, amount: int, portfolio: Portfolio, before_capital: int):
        if not config.LINE_CHANNEL_ACCESS_TOKEN or not config.LINE_USER_ID:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        new_lot = portfolio.lot_size()
        text = (
            f"💰 入金完了！ブルみん×ベアドン\n\n"
            f"ブルみん: ¥{amount:,} 入金されたね！\n"
            f"ベアドン: 1口サイズが ¥{new_lot:,} になったぞ。\n\n"
            f"【{today} 入金内容】\n"
            f"入金額：¥{amount:,}\n"
            f"総資本：¥{before_capital:,} → ¥{portfolio.total_capital:,}\n"
            f"累計入金：¥{portfolio.total_deposited:,}\n\n"
            f"次の買い注文は ¥{new_lot:,} で入れてね！\n"
            f"夢は推せ。でも、ちゃんと考えて推せ。🌟"
        )
        data = json.dumps({"to": config.LINE_USER_ID, "messages": [{"type": "text", "text": text}]}).encode("utf-8")
        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.LINE_CHANNEL_ACCESS_TOKEN}"},
        )
        urllib.request.urlopen(req)

    def _chara_dialogue(self, action: str) -> tuple[str, str]:
        scripts = {
            "BUY":  ("ブルみん: よし！今日は買ったよ！これが私の選択！💪",
                     "ベアドン: …まあ、筋は通ってる。結果を見せてもらおう。"),
            "SELL": ("ブルみん: 利確できたよ〜！ありがとうございました！🙏",
                     "ベアドン: 売り時を見極めた。悪くない。"),
            "HOLD": ("ブルみん: 今日は待ちだね。動かないのも立派な判断！",
                     "ベアドン: 正解。焦って動く方が損をする。"),
        }
        return scripts.get(action, ("ブルみん: 今日も相場と向き合ったよ。",
                                    "ベアドン: 考えて動くことが大事だ。"))

    def send_report_email(
        self,
        action: str,
        trade_summary: str,
        screenshot_path: "str | None",
        market_data: MarketData,
        portfolio: Portfolio,
        character_report: "dict | None" = None,
    ):
        today = datetime.now().strftime("%Y-%m-%d")
        if character_report and character_report.get("short_dialogue"):
            # AIが生成した会話をそのまま使う
            dialogue_text = character_report["short_dialogue"]
            burumin = dialogue_text
            beardon = ""
        else:
            burumin, beardon = self._chara_dialogue(action)
        ai_title = character_report.get("title", "") if character_report else ""
        if ai_title:
            action_icon_prefix = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️"}.get(action, "🐂")
            subject = f"{action_icon_prefix} {ai_title} ブルみん×ベアドン ({today})"
        else:
            subject_map = {
                "BUY":  f"📈 今日は強気に買ったよ！ブルみん×ベアドン ({today})",
                "SELL": f"📉 今日は利確したよ！ブルみん×ベアドン ({today})",
                "HOLD": f"⏸️ 今日は静かに様子見。ブルみん×ベアドン ({today})",
            }
            subject = subject_map.get(action, f"🐂 本日の結果！ブルみん×ベアドン ({today})")

        action_icon = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️"}.get(action, "⏸️")

        body = self._build_report_body(
            action=action,
            trade_summary=trade_summary,
            screenshot_path=screenshot_path,
            market_data=market_data,
            portfolio=portfolio,
            burumin=burumin,
            beardon=beardon,
            action_icon=action_icon,
        )
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = self.email_to
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if screenshot_path and os.path.exists(screenshot_path):
            with open(screenshot_path, "rb") as f:
                img_data = f.read()
            ext = os.path.splitext(screenshot_path)[1].lower().lstrip(".")
            mime_type = "png" if ext == "png" else "jpeg"
            from email.mime.image import MIMEImage
            img = MIMEImage(img_data, _subtype=mime_type)
            img.add_header("Content-Disposition", "attachment",
                           filename=os.path.basename(screenshot_path))
            msg.attach(img)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
            server.login(self.email_from, self.password)
            server.sendmail(self.email_from, self.email_to, msg.as_string())

    def _build_report_body(
        self,
        action: str,
        trade_summary: str,
        screenshot_path: "str | None",
        market_data: MarketData,
        portfolio: Portfolio,
        burumin: str,
        beardon: str,
        action_icon: str,
    ) -> str:
        today = datetime.now().strftime("%Y-%m-%d")

        def arrow(val): return "↑ 上昇" if val >= 0 else "↓ 下落"
        vix = market_data.vix_close
        if vix >= 30:   vix_label = "🚨 危険水準（大荒れ注意）"
        elif vix >= 25: vix_label = "⚠️ 警戒水準（荒れやすい）"
        elif vix >= 20: vix_label = "😟 やや不安定"
        else:           vix_label = "😌 落ち着いている"
        cme_note = "  ⚠️ 明日の日本株は下落見通し" if market_data.cme_nikkei_change < 0 else "  ✅ 明日の日本株は上昇見通し"
        usdjpy_note = "円安（輸出に有利）" if market_data.usdjpy_rate >= 150 else "円高（輸入に有利）"
        pnl = portfolio.total_capital - portfolio.total_deposited
        pnl_sign = "+" if pnl >= 0 else ""
        pnl_pct = (pnl / portfolio.total_deposited * 100) if portfolio.total_deposited > 0 else 0.0

        def icon(val): return "⬆️" if val >= 0 else "⬇️"

        data_label = f"  ※ データ基準日：{market_data.data_as_of}（終値）\n" if market_data.data_as_of else ""

        return f"""🐂×🧊 ブルみん×ベアドン 本日の売買結果 - {today}
{"=" * 46}
おつかれさま！今日もブルみんの一日を届けるよ。
夢は推せ。でも、ちゃんと考えて推せ。

{"=" * 46}
【今日のブルみん】

{burumin}
{beardon}

{"=" * 46}
【本日の売買】

  {action_icon} {trade_summary}

{"=" * 46}
【今日の相場環境】
{data_label}
{icon(market_data.nikkei_change)} 日本株（日経225）
   {market_data.nikkei_close:,.0f}円  {arrow(market_data.nikkei_change)}（前日比 {market_data.nikkei_change:+,.0f}円）

{icon(market_data.sp500_change)} アメリカ株（S&P500）
   {market_data.sp500_close:,.2f}  {arrow(market_data.sp500_change)}（前日比 {market_data.sp500_change:+,.2f}）

{icon(market_data.cme_nikkei_change)} 明日の日本株見通し（CME先物）
   {market_data.cme_nikkei_close:,.0f}円  {arrow(market_data.cme_nikkei_change)}（前日比 {market_data.cme_nikkei_change:+,.0f}円）
{cme_note}

{icon(market_data.usdjpy_change)} ドル円
   1ドル = {market_data.usdjpy_rate:.2f}円  {usdjpy_note}

{icon(market_data.vix_change)} VIX（恐怖指数）
   {market_data.vix_close:.2f}  {vix_label}（前日比 {market_data.vix_change:+.2f}）
   ※ 20以下：安定、25超：警戒、30超：大荒れ注意

{icon(market_data.us10y_change)} 米国10年債利回り
   {market_data.us10y_rate:.2f}%（前日比 {market_data.us10y_change:+.2f}%）
   {"金利上昇中（株の下押し要因）" if market_data.us10y_change > 0 else "金利低下中（株の支援要因）"}

{"=" * 46}
【ブルみんの資金状況】

  総資本：        ¥{portfolio.total_capital:,}
  投資中：        ¥{portfolio.current_position_value:,}
  使える資金：    ¥{portfolio.available_capital:,}
  投資枠：        {portfolio.parts_used()}/{config.MAX_PARTS}口（残り{portfolio.parts_available()}枠）
  1口サイズ：     ¥{portfolio.lot_size():,}（複利ロット）

{"=" * 46}
【累計パフォーマンス】

  累計入金額：    ¥{portfolio.total_deposited:,}
  現在の総資本：  ¥{portfolio.total_capital:,}
  損益：          {pnl_sign}¥{pnl:,}（{pnl_sign}{pnl_pct:.1f}%）
  取引回数：      {portfolio.trade_count}回

{"=" * 46}
{"※ 約定スクリーンショットを添付しています。" if screenshot_path else "※ スクリーンショットの添付はありませんでした。"}
※ 投資は自己責任です。このメールはあくまで記録と物語の共有です。
"""

    def send_report_line(
        self,
        action: str,
        trade_summary: str,
        market_data: MarketData,
        portfolio: Portfolio,
        screenshot_path: "str | None" = None,
        character_report: "dict | None" = None,
    ):
        if not config.LINE_CHANNEL_ACCESS_TOKEN or not config.LINE_USER_ID:
            return

        if character_report and character_report.get("short_dialogue"):
            burumin = character_report["short_dialogue"]
            beardon = ""
        else:
            burumin, beardon = self._chara_dialogue(action)
        action_icon = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️"}.get(action, "⏸️")

        body = self._build_report_body(
            action=action,
            trade_summary=trade_summary,
            screenshot_path=screenshot_path,
            market_data=market_data,
            portfolio=portfolio,
            burumin=burumin,
            beardon=beardon,
            action_icon=action_icon,
        )
        text = body[:4800] if len(body) > 4800 else body

        messages = [{"type": "text", "text": text}]

        # スクショがあればLINEにも画像送信
        if screenshot_path and os.path.exists(screenshot_path):
            img_url = self._upload_screenshot_to_github(screenshot_path)
            if img_url:
                messages.append({
                    "type": "image",
                    "originalContentUrl": img_url,
                    "previewImageUrl": img_url,
                })

        data = json.dumps({"to": config.LINE_USER_ID, "messages": messages}).encode("utf-8")
        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.LINE_CHANNEL_ACCESS_TOKEN}"},
        )
        urllib.request.urlopen(req)

    def send_tweet_text_line(self, action: str, trade_summary: str, market_data: MarketData):
        """X投稿用テキストをLINEに送る（コピペして手動投稿用）。"""
        if not config.LINE_CHANNEL_ACCESS_TOKEN or not config.LINE_USER_ID:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        action_icon = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️"}.get(action, "⏸️")
        burumin, beardon = self._chara_dialogue(action)
        tweet_text = (
            f"🐂×🧊 今日の結果（{today}）\n"
            f"{action_icon} {trade_summary}\n\n"
            f"{burumin}\n"
            f"{beardon}\n\n"
            f"日経: {market_data.nikkei_close:,.0f}円 / VIX: {market_data.vix_close:.1f}\n\n"
            f"夢は推せ。でも、ちゃんと考えて推せ。🌟\n"
            f"#楽天4倍ブル #投資日記 #ブルみん"
        )
        text = f"📋 X投稿用（コピペしてね）\n─────────────\n{tweet_text}"
        data = json.dumps({"to": config.LINE_USER_ID, "messages": [{"type": "text", "text": text}]}).encode("utf-8")
        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.LINE_CHANNEL_ACCESS_TOKEN}"},
        )
        urllib.request.urlopen(req)

    def send_tweet(self, action: str, trade_summary: str, market_data: MarketData, character_report: "dict | None" = None) -> bool:
        """X（Twitter）に投稿する。"""
        if not config.X_API_KEY or not config.X_ACCESS_TOKEN:
            print("X APIキー未設定のためスキップ")
            return False
        try:
            import tweepy
            client = tweepy.Client(
                consumer_key=config.X_API_KEY,
                consumer_secret=config.X_API_KEY_SECRET,
                access_token=config.X_ACCESS_TOKEN,
                access_token_secret=config.X_ACCESS_TOKEN_SECRET,
            )
            # AI生成テキストがあればそれを使う、なければフォールバック
            if character_report and character_report.get("x_post"):
                text = character_report["x_post"]
            else:
                today = datetime.now().strftime("%Y-%m-%d")
                action_icon = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️"}.get(action, "⏸️")
                burumin, beardon = self._chara_dialogue(action)
                text = (
                    f"🐂×🧊 今日の結果（{today}）\n"
                    f"{action_icon} {trade_summary}\n\n"
                    f"{burumin}\n"
                    f"{beardon}\n\n"
                    f"日経: {market_data.nikkei_close:,.0f}円 / VIX: {market_data.vix_close:.1f}\n\n"
                    f"夢は推せ。でも、ちゃんと考えて推せ。🌟\n"
                    f"#楽天4倍ブル #投資日記 #ブルみん"
                )
            if len(text) > 2000:
                text = text[:1997] + "..."
            client.create_tweet(text=text)
            print(f"X投稿完了: {len(text)}文字")
            return True
        except Exception as e:
            print(f"X投稿失敗: {e}")
            return False

    def _upload_screenshot_to_github(self, screenshot_path: str) -> "str | None":
        """スクショをGitHubリポジトリにpushして公開URLを返す。"""
        try:
            import base64
            token = os.environ.get("GITHUB_TOKEN", "")
            repo = "krdtmhr/bull-agent"
            filename = os.path.basename(screenshot_path)
            api_url = f"https://api.github.com/repos/{repo}/contents/screenshots/{filename}"

            with open(screenshot_path, "rb") as f:
                content = base64.b64encode(f.read()).decode()

            # 既存ファイルのSHAを取得（上書き用）
            sha = None
            try:
                check = urllib.request.Request(
                    api_url,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                )
                res = urllib.request.urlopen(check)
                sha = json.loads(res.read())["sha"]
            except Exception:
                pass

            body = {"message": f"スクショ追加: {filename}", "content": content}
            if sha:
                body["sha"] = sha

            put_req = urllib.request.Request(
                api_url,
                data=json.dumps(body).encode(),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "Content-Type": "application/json",
                },
                method="PUT",
            )
            urllib.request.urlopen(put_req)

            ext = os.path.splitext(filename)[1].lower()
            # GitHub raw URLはLINEがHTTPSで取得できる形式
            return f"https://raw.githubusercontent.com/{repo}/master/screenshots/{filename}"
        except Exception as e:
            print(f"スクショアップロード失敗: {e}")
            return None

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
