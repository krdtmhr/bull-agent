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
            "BUY": f"【📈 強気寄り】ブルみん×ベアドン 朝ナビ ({today})",
            "SELL": f"【📉 慎重寄り】ブルみん×ベアドン 朝ナビ ({today})",
            "HOLD": f"【⏸️ 様子見】ブルみん×ベアドン 朝ナビ ({today})",
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
            "BUY": "下落局面での押し目。\n  今日は買い注文を入れます。",
            "SELL": "上昇局面での利益確定。\n  今日は解約注文を入れます。",
            "HOLD": "今日は方向感がなし。\n  「動かない」も立派な投資判断です。",
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

        # X（Twitter）投稿文
        cme_dir = "↓" if data.cme_nikkei_change < 0 else "↑"
        vix_short = "🚨危険" if data.vix_close >= 30 else ("⚠️警戒" if data.vix_close >= 25 else "😌安定")
        if rule_signal.action == "SELL" and sell_parts > 0:
            _sell_label = "全部" if sell_parts >= held_parts else f"{sell_parts}口"
            sns_sell_text = f"{_sell_label}解約します！（¥{sell_amount:,}）"
        else:
            sns_sell_text = "保有なし（今日は様子見）"
        sns_action = {
            "BUY": f"¥{rule_signal.amount:,} 買い注文を入れます！",
            "SELL": sns_sell_text,
            "HOLD": "今日は様子見。何もしません。",
        }
        sns_post = (
            f"🐂×🧊 今日の朝ナビ（{today}）\n"
            f"{'📈' if rule_signal.action == 'BUY' else '📉' if rule_signal.action == 'SELL' else '⏸️'} "
            f"{sns_action[rule_signal.action]}\n\n"
            f"CME先物: {data.cme_nikkei_close:,.0f}円 {cme_dir}({data.cme_nikkei_change:+.0f})\n"
            f"VIX: {data.vix_close:.1f} {vix_short}\n"
            f"ドル円: {data.usdjpy_rate:.2f}円\n\n"
            f"夢は推せ。でも、ちゃんと考えて推せ。🌟\n"
            f"#楽天4倍ブル #投資日記 #ブルみん"
        )

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

📌 VIX（恐怖指数・市場の不安度）
   {data.vix_close:.2f}  {vix_label}（前日比 {data.vix_change:+.2f}）
   ※ 20以下：安定、25超：警戒、30超：大荒れ注意（4.3倍ブルに直撃）

📌 米国10年債利回り（金利）
   {data.us10y_rate:.2f}%  {us10y_note}（前日比 {data.us10y_change:+.2f}%）
   ※ 金利が上がると株が下がりやすい傾向がある

{"=" * 46}
{news_section}{"=" * 46}
【今日の操作】
{action_instructions[rule_signal.action]}

{"=" * 46}
【📱 X（Twitter）投稿文 ─ そのままコピペでOK】

{sns_post}

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

    def send_line(self, rule_signal: RuleSignal, market_data: MarketData, portfolio: Portfolio, news_items: "list[NewsItem] | None" = None, sell_parts: int = 0):
        if not config.LINE_CHANNEL_ACCESS_TOKEN or not config.LINE_USER_ID:
            return
        if news_items is None:
            news_items = []
        today = datetime.now().strftime("%Y-%m-%d")
        stance_map = {"BUY": "📈 強気寄り（攻めの日）", "SELL": "📉 慎重寄り（守りの日）", "HOLD": "⏸️ 様子見（待ちの日）"}
        stance = stance_map.get(rule_signal.action, "⏸️ 様子見")

        nikkei_arrow = "↑" if market_data.nikkei_change >= 0 else "↓"
        cme_arrow = "↑" if market_data.cme_nikkei_change >= 0 else "↓"

        if rule_signal.action == "BUY":
            action_line = f"→ ¥{rule_signal.amount:,} 買い注文を入れよう！"
        elif rule_signal.action == "SELL" and sell_parts > 0:
            action_line = f"→ {sell_parts}口（¥{sell_parts * portfolio.lot_size():,}）解約しよう！"
        else:
            action_line = "→ 今日は何もしない"

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
            f"{stance}\n"
            f"{action_line}\n\n"
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

    def send_deposit_email(self, amount: int, portfolio: Portfolio, before_capital: int):
        today = datetime.now().strftime("%Y-%m-%d")
        subject = f"【💰 入金完了】ブルみん×ベアドン ({today})"
        new_lot = portfolio.lot_size()
        body = f"""💰 入金完了のお知らせ - {today}
{"=" * 46}

ブルみん: やった～！¥{amount:,} 入金されたね！
         お金が増えると、作戦の幅が広がるよ💪

ベアドン: ふん、浮かれるな。
         でも…1口の金額が変わったから確認しておけ。

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

    def _chara_dialogue(self, signal: str, action: str) -> tuple[str, str, str]:
        """
        シグナルと実際の行動の組み合わせから台本を生成する。
        Returns: (subject_label, burumin_line, beardon_line)
        """
        key = (signal, action)
        scripts = {
            ("BUY",  "BUY"):  ("📈 天の声通り！買いました",
                               "ブルみん: よっしゃ！天の声に従ったぞ！これが俺の本領発揮や！💪",
                               "ベアドン: …ふん。まあシグナル通りに動いたのは認める。だが油断するな。"),
            ("BUY",  "HOLD"): ("⏸️ BUYシグナルだったけど…見送りました",
                               "ブルみん: う〜ん、天の声はBUYって言ってるんだけど…なんか今日はちょっと怖くて。見送りました。",
                               "ベアドン: 珍しく冷静じゃないか。悪くない判断だ。勇気ある撤退もある。"),
            ("BUY",  "SELL"): ("📉 BUYシグナルだったのに利確しました",
                               "ブルみん: 天の声はBUYって言ってたけど…怖くなって売っちゃった。ごめんなさい。",
                               "ベアドン: ふむ。ルールを破ったのは褒められんが、利確は利確だ。次は根拠を持って動け。"),
            ("SELL", "SELL"): ("📉 ベアドンの言う通り！売りました",
                               "ブルみん: 今回はベアドン、お前が正しかった。素直に認めます。売りました。",
                               "ベアドン: …珍しく賢い選択だ。私の言う通りにすれば間違いない。"),
            ("SELL", "HOLD"): ("⏸️ SELLシグナルだったけど…ホールドしました",
                               "ブルみん: ベアドンは売れって言ってるけど、まだいけると思って持ちました！",
                               "ベアドン: …やれやれ。まあいい。ただし次の動きをよく見ておけ。"),
            ("SELL", "BUY"):  ("📈 SELLシグナルなのに逆張り！買いました",
                               "ブルみん: 待って待って！ベアドンは売れって言ってるけど、俺はここが底だと思う！買う！",
                               "ベアドン: …馬鹿者。後で泣いても知らんぞ。結果で証明してみせろ。"),
            ("HOLD", "BUY"):  ("📈 HOLDシグナルだったけど自分の判断で買いました",
                               "ブルみん: 天の声はHOLDって言ってるけど、俺の直感がここは買いって言ってる！",
                               "ベアドン: …ルールを破るな。だがお前の直感がどこまで通じるか見せてもらおう。"),
            ("HOLD", "SELL"): ("📉 HOLDシグナルだったけど利確しました",
                               "ブルみん: なんか不安になってきて…HOLDって言われてるけどちょっと利確しておきます。",
                               "ベアドン: 弱気め。だが利確は悪くない選択だ。感情で動くな、次は根拠を持て。"),
            ("HOLD", "HOLD"): ("⏸️ 今日は様子見。静かな一日でした",
                               "ブルみん: 今日は天の声もHOLD、俺もHOLD。静かな一日でした。",
                               "ベアドン: 動かない日こそ大事だ。次の波に備えておけ。"),
        }
        default = ("⏸️ 本日の結果",
                   "ブルみん: 今日も相場と向き合いました。",
                   "ベアドン: 結果はどうあれ、考えて動くことが大事だ。")
        return scripts.get(key, default)

    def send_report_email(
        self,
        signal_action: str,
        action: str,
        trade_summary: str,
        screenshot_path: "str | None",
        market_data: MarketData,
        portfolio: Portfolio,
    ):
        today = datetime.now().strftime("%Y-%m-%d")
        label, burumin, beardon = self._chara_dialogue(signal_action, action)
        subject = f"【{label}】ブルみん×ベアドン ({today})"

        action_icon = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️"}.get(action, "⏸️")
        signal_icon = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️"}.get(signal_action, "⏸️")

        # X（Twitter）投稿文
        sns_post = (
            f"🐂×🧊 今日の結果（{today}）\n"
            f"{action_icon} {trade_summary}\n\n"
            f"{burumin}\n"
            f"{beardon}\n\n"
            f"日経: {market_data.nikkei_close:,.0f}円 / VIX: {market_data.vix_close:.1f}\n\n"
            f"夢は推せ。でも、ちゃんと考えて推せ。🌟\n"
            f"#楽天4倍ブル #投資日記 #ブルみん"
        )

        body = f"""🐂×🧊 ブルみん×ベアドン 本日の売買結果 - {today}
{"=" * 46}

{burumin}
{beardon}

{"=" * 46}
【本日の売買】

  シグナル（天の声）: {signal_icon} {signal_action}
  実際の行動:         {action_icon} {action}

  {trade_summary}

{"=" * 46}
【資金状況】

  総資本：      ¥{portfolio.total_capital:,}
  使える資金：  ¥{portfolio.available_capital:,}
  投資中：      ¥{portfolio.current_position_value:,}
  投資枠：      {portfolio.parts_used()}/{config.MAX_PARTS}口
  1口サイズ：   ¥{portfolio.lot_size():,}
  累計入金額：  ¥{portfolio.total_deposited:,}

{"=" * 46}
【市場データ】

  日経225:    {market_data.nikkei_close:,.0f}円 ({market_data.nikkei_change:+,.0f})
  S&P500:     {market_data.sp500_close:,.2f} ({market_data.sp500_change:+,.2f})
  CME先物:    {market_data.cme_nikkei_close:,.0f}円 ({market_data.cme_nikkei_change:+,.0f})
  VIX:        {market_data.vix_close:.2f}
  ドル円:     {market_data.usdjpy_rate:.2f}円

{"=" * 46}
【📱 X（Twitter）投稿文 ─ そのままコピペでOK】

{sns_post}

{"=" * 46}
{"※ 約定スクリーンショットを添付しています。" if screenshot_path else "※ スクリーンショットの添付はありませんでした。"}
"""
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

    def send_report_line(
        self,
        signal_action: str,
        action: str,
        trade_summary: str,
        market_data: MarketData,
        portfolio: Portfolio,
    ):
        if not config.LINE_CHANNEL_ACCESS_TOKEN or not config.LINE_USER_ID:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        action_icon = {"BUY": "📈", "SELL": "📉", "HOLD": "⏸️"}.get(action, "⏸️")
        _, burumin, beardon = self._chara_dialogue(signal_action, action)
        text = (
            f"{action_icon} 売買完了！ブルみん×ベアドン\n\n"
            f"{burumin}\n"
            f"{beardon}\n\n"
            f"【{today} 本日の結果】\n"
            f"{trade_summary}\n\n"
            f"総資本：¥{portfolio.total_capital:,}\n"
            f"投資枠：{portfolio.parts_used()}/{config.MAX_PARTS}口\n\n"
            f"詳細と約定スクショはメールをチェックしてね！\n"
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
