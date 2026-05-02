import base64
import hashlib
import hmac
import json
import os
import urllib.request

from flask import Flask, abort, jsonify, render_template, request

import config
from src.github_storage import GithubStorage
from src.trade_history import TradeHistory

app = Flask(__name__)


def _storage() -> GithubStorage:
    return GithubStorage(config.GITHUB_TOKEN, config.GITHUB_REPO)


def _verify_signature(body: bytes, signature: str) -> bool:
    if not config.LINE_CHANNEL_SECRET:
        return True
    digest = hmac.new(
        config.LINE_CHANNEL_SECRET.encode("utf-8"), body, hashlib.sha256
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def _reply(reply_token: str, text: str) -> None:
    payload = json.dumps({
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/reply",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.LINE_CHANNEL_ACCESS_TOKEN}",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"LINE reply error: {e}")


def _handle_command(text: str, storage: GithubStorage) -> str:
    text = text.strip()

    if text == "判断":
        state, _ = storage.read("portfolio_state.json")
        if not state:
            return "まだポートフォリオ情報がないよ。朝のレポートを待ってね🐂"
        action = state.get("last_signal_action", "HOLD")
        date = state.get("last_signal_date", "")
        reason = state.get("last_signal_reason", "")
        conf = state.get("last_signal_confidence", 0.5)
        stance_map = {"BUY": "📈 強気寄り", "SELL": "📉 慎重寄り", "HOLD": "⏸️ 様子見"}
        stance = stance_map.get(action, "⏸️ 様子見")
        if not date:
            return "まだ今日の分析が届いていないよ！毎朝8時に送るね🐂"
        pct = round(conf * 100)
        return (
            f"🐂 ブルみんの判断（{date}）\n\n"
            f"今日のスタンス：{stance}\n"
            f"確信度：{pct}%\n\n"
            f"根拠：{reason}\n\n"
            f"詳しい分析はメールをチェックしてね！"
        )

    if text == "残高":
        state, _ = storage.read("portfolio_state.json")
        if not state:
            return "ポートフォリオ情報が読み込めないよ。"
        total = state.get("total_capital", 0)
        avail = state.get("available_capital", 0)
        pos = state.get("current_position_value", 0)
        count = state.get("trade_count", 0)
        updated = state.get("last_updated", "")[:16]
        parts_used = int(pos / (total / 10)) if total > 0 else 0
        return (
            f"💰 現在の資金状況\n\n"
            f"総資本：¥{total:,}\n"
            f"使える資金：¥{avail:,}\n"
            f"投資中：¥{pos:,}\n\n"
            f"投資枠：{parts_used}/10\n"
            f"取引回数：{count}回\n"
            f"最終更新：{updated}"
        )

    if text == "履歴":
        hist_data, _ = storage.read("trade_history.json")
        history = TradeHistory().from_dict(hist_data)
        records = history.recent(5)
        if not records:
            return "まだ取引履歴がないよ！\n買い/売りを記録すると表示されるよ🐂"
        lines = ["📋 最近の取引（最大5件）\n"]
        for i, r in enumerate(records, 1):
            label = "📈 購入" if r.action == "BUY" else "📉 売却"
            lines.append(f"{i}. {r.date}\n   {label} ¥{r.amount:,}")
        return "\n".join(lines)

    if text.startswith("買い"):
        return _record_trade("BUY", text[2:].strip(), storage)

    if text.startswith("売り"):
        return _record_trade("SELL", text[2:].strip(), storage)

    return (
        "🐂 ブルみんコマンド一覧\n\n"
        "📊 判断 → 今日のスタンス確認\n"
        "💰 残高 → 資金状況確認\n"
        "📋 履歴 → 取引履歴\n"
        "📈 買い [金額] → 購入を記録\n"
        "   例：買い 10000\n"
        "📉 売り [金額] → 売却を記録\n"
        "   例：売り 10000"
    )


def _record_trade(action: str, amount_str: str, storage: GithubStorage) -> str:
    try:
        amount = int(amount_str.replace(",", "").replace("円", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        return "金額を正しく入力してね！\n例：買い 10000"

    state, state_sha = storage.read("portfolio_state.json")
    if not state:
        return "ポートフォリオ情報が読み込めないよ。"

    if action == "BUY":
        avail = state.get("available_capital", 0)
        if avail < amount:
            return f"使える資金が足りないよ！\n現在の使える資金：¥{avail:,}"
        state["available_capital"] = avail - amount
        state["current_position_value"] = state.get("current_position_value", 0) + amount
    else:
        pos = state.get("current_position_value", 0)
        if pos < amount:
            return f"投資中の金額が足りないよ！\n現在の投資中：¥{pos:,}"
        state["current_position_value"] = pos - amount
        state["available_capital"] = state.get("available_capital", 0) + amount

    state["trade_count"] = state.get("trade_count", 0) + 1
    from datetime import datetime
    state["last_updated"] = datetime.now().isoformat()

    storage.write(
        "portfolio_state.json", state, state_sha,
        f"trade: {action} ¥{amount}"
    )

    hist_data, hist_sha = storage.read("trade_history.json")
    history = TradeHistory().from_dict(hist_data)
    history.add(action, amount)
    storage.write(
        "trade_history.json", history.to_dict(), hist_sha,
        f"trade history: {action} ¥{amount}"
    )

    label = "購入" if action == "BUY" else "売却"
    new_avail = state["available_capital"]
    new_pos = state["current_position_value"]
    return (
        f"✅ 記録したよ！\n\n"
        f"行動：{label}\n"
        f"金額：¥{amount:,}\n\n"
        f"💰 使える資金：¥{new_avail:,}\n"
        f"📊 投資中：¥{new_pos:,}"
    )


@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_data()
    signature = request.headers.get("X-Line-Signature", "")
    if not _verify_signature(body, signature):
        abort(400)

    events = request.json.get("events", [])
    storage = _storage()
    for event in events:
        if event.get("type") != "message":
            continue
        if event.get("message", {}).get("type") != "text":
            continue
        reply_token = event.get("replyToken")
        text = event.get("message", {}).get("text", "")
        if reply_token and text:
            response = _handle_command(text, storage)
            _reply(reply_token, response)

    return "OK"


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/")
def dashboard():
    storage = _storage()
    state, _ = storage.read("portfolio_state.json")
    hist_data, _ = storage.read("trade_history.json")
    history = TradeHistory().from_dict(hist_data)

    total = state.get("total_capital", 100000)
    pos = state.get("current_position_value", 0)
    portfolio = {
        "total_capital": total,
        "available_capital": state.get("available_capital", total),
        "current_position_value": pos,
        "trade_count": state.get("trade_count", 0),
        "last_updated": state.get("last_updated", ""),
        "last_signal_action": state.get("last_signal_action", "HOLD"),
        "last_signal_reason": state.get("last_signal_reason", ""),
        "last_signal_date": state.get("last_signal_date", ""),
        "last_signal_confidence": state.get("last_signal_confidence", 0.5),
        "parts_used": int(pos / (total / 10)) if total > 0 else 0,
    }

    return render_template("dashboard.html", portfolio=portfolio, trades=history.recent(20))


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
