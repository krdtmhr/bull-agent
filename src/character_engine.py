"""キャラ会話生成の統合オーケストレーター。

使用法:
    from src.character_engine import generate_character_report
    report = generate_character_report(market_data, trade_result, portfolio)
"""
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 総資産の節目（円）
_MILESTONES = [110_000, 120_000, 130_000, 150_000, 200_000]


def generate_character_report(
    market_data,
    trade_result: dict,
    portfolio,
    screenshot_url: str | None = None,
) -> dict:
    """キャラ会話・投稿文・記憶更新をまとめて実行する。

    Args:
        market_data: MarketData オブジェクト または dict
        trade_result: {"action": str, "trade_summary": str, "signal": str,
                       "lot": int, "realized_pnl": float, "sell_parts": int}
        portfolio: Portfolio オブジェクト または dict
        screenshot_url: 約定スクショのURL（任意）

    Returns:
        LLMが生成した会話・投稿文を含む dict（エラー時はフォールバック値）
    """
    from src.sheets_logger import (
        append_character_memory,
        append_post_log,
        append_trade_log,
        fetch_recent_character_memory,
        fetch_recent_trade_logs,
    )
    from src.memory_loader import build_memory_context
    from src.emotion_engine import determine_emotion
    from src.prompt_builder import build_character_prompt

    today = datetime.now().strftime("%Y-%m-%d")

    # ─── 1. MarketData / Portfolio を dict に正規化 ─────────────────────
    md = _normalize_market_data(market_data)
    pf = _normalize_portfolio(portfolio)

    action = trade_result.get("action", "HOLD")
    signal = trade_result.get("signal", pf.get("last_signal_action", "HOLD"))
    realized_pnl = float(trade_result.get("realized_pnl", 0))
    day_number = pf.get("trade_count", 0)

    # ─── 2. トレードログを Sheets に保存 ────────────────────────────────
    cme_direction = "↓" if md.get("cme_nikkei_change", 0) < 0 else ("↑" if md.get("cme_nikkei_change", 0) > 0 else "flat")
    sp500_direction = "↓" if md.get("sp500_change", 0) < 0 else ("↑" if md.get("sp500_change", 0) > 0 else "flat")

    trade_log_row = {
        "date": today,
        "day": day_number,
        "signal": signal,
        "action": action,
        "price": "",
        "quantity": trade_result.get("sell_parts", 1) if action == "SELL" else (1 if action == "BUY" else 0),
        "realized_pnl": realized_pnl,
        "unrealized_pnl": pf.get("total_capital", 0) - pf.get("total_deposited", 0),
        "total_value": pf.get("total_capital", 0),
        "cash": pf.get("available_capital", 0),
        "position_size": pf.get("current_position_value", 0),
        "vix": md.get("vix_close", 0),
        "nikkei": md.get("nikkei_close", 0),
        "cme_direction": cme_direction,
        "sp500_direction": sp500_direction,
        "confidence": pf.get("last_signal_confidence", 0.5),
        "screenshot_url": screenshot_url or "",
        "memo": trade_result.get("trade_summary", ""),
    }
    append_trade_log(trade_log_row)

    # ─── 3. 直近ログを取得 ───────────────────────────────────────────────
    recent_trades = fetch_recent_trade_logs(30)
    recent_memories = fetch_recent_character_memory(20)

    # ─── 4. 記憶コンテキスト生成 ─────────────────────────────────────────
    memory_context = build_memory_context(recent_trades, recent_memories)

    # ─── 5. 感情状態生成 ─────────────────────────────────────────────────
    recent_pnl_list = [float(t.get("realized_pnl", 0)) for t in recent_trades[-10:]]
    rule_break = (signal != action and action != "HOLD" and signal != "HOLD")
    total_value = float(pf.get("total_capital", 100_000))

    emotion_state = determine_emotion(
        daily_pnl=realized_pnl,
        total_value=total_value,
        recent_pnl_list=recent_pnl_list,
        signal=signal,
        action=action,
        vix=float(md.get("vix_close", 20)),
        position_size=int(pf.get("current_position_value", 0)),
        rule_break=rule_break,
    )

    # ─── 6. プロンプト生成 ────────────────────────────────────────────────
    prompt = build_character_prompt(
        market_data=md,
        trade_result=trade_result,
        portfolio_state=pf,
        emotion_state=emotion_state,
        memory_context=memory_context,
    )

    # ─── 7. OpenAI API 呼び出し ──────────────────────────────────────────
    llm_result = _call_openai(prompt)

    # ─── 8. 投稿ログに保存 ───────────────────────────────────────────────
    post_log_row = {
        "date": today,
        "day": day_number,
        "title": llm_result.get("title", ""),
        "x_post": llm_result.get("x_post", ""),
        "short_dialogue": llm_result.get("short_dialogue", ""),
        "note_body": llm_result.get("note_body", ""),
        "youtube_script": llm_result.get("youtube_script", ""),
        "next_hook": llm_result.get("next_hook", ""),
        "posted_x": "FALSE",
        "posted_note": "FALSE",
        "posted_youtube": "FALSE",
    }
    append_post_log(post_log_row)

    # ─── 9. 重要イベントをキャラ記憶に保存 ──────────────────────────────
    mem_suggestion = llm_result.get("memory_event_suggestion", {})
    event_type = mem_suggestion.get("event_type", "none")

    # 自動判定による補完
    if event_type == "none":
        event_type = _detect_important_event(
            realized_pnl=realized_pnl,
            total_value=total_value,
            action=action,
            vix=float(md.get("vix_close", 20)),
            rule_break=rule_break,
            recent_trades=recent_trades,
        )

    if event_type != "none":
        memory_row = {
            "date": today,
            "day": day_number,
            "event_type": event_type,
            "summary": mem_suggestion.get("summary", trade_result.get("trade_summary", "")),
            "bullmin_emotion": emotion_state["bullmin"]["mood"],
            "bullmin_intensity": emotion_state["bullmin"]["intensity"],
            "beardon_emotion": emotion_state["beardon"]["mood"],
            "beardon_intensity": emotion_state["beardon"]["intensity"],
            "running_joke": mem_suggestion.get("running_joke", ""),
            "lesson": mem_suggestion.get("lesson", ""),
            "future_reference": "TRUE",
        }
        append_character_memory(memory_row)

    # ─── 10. 結果を返す ──────────────────────────────────────────────────
    return {
        **llm_result,
        "emotion_state": emotion_state,
        "memory_context": memory_context,
    }


def _detect_important_event(
    realized_pnl: float,
    total_value: float,
    action: str,
    vix: float,
    rule_break: bool,
    recent_trades: list,
) -> str:
    """自動で重要イベントを判定する。"""
    if rule_break:
        return "rule_break"

    pnl_pct = (realized_pnl / total_value * 100) if total_value > 0 else 0.0
    if pnl_pct >= 3.0:
        return "big_win"
    if pnl_pct <= -3.0:
        return "big_loss"

    # 節目チェック
    for milestone in _MILESTONES:
        if total_value >= milestone:
            prev_values = [float(t.get("total_value", 0)) for t in recent_trades[:-1]]
            if prev_values and all(v < milestone for v in prev_values):
                return "milestone"

    # 連勝・連敗（現在の結果を含む）
    streak = _count_streak(recent_trades)
    if streak >= 3 and realized_pnl > 0:
        return "streak_win"
    if streak >= 3 and realized_pnl < 0:
        return "streak_loss"

    # VIX 高水準での売買
    if vix >= 25 and action in ("BUY", "SELL"):
        return "drawdown"

    # HOLD 3回連続
    if action == "HOLD":
        hold_count = sum(1 for t in recent_trades[-3:] if t.get("action") == "HOLD")
        if hold_count >= 3:
            return "quiet_day"

    return "none"


def _count_streak(trades: list) -> int:
    """直近のpnlから連続数を返す。"""
    if not trades:
        return 0
    streak = 0
    last_sign = None
    for t in reversed(trades):
        pnl = float(t.get("realized_pnl", 0))
        if pnl == 0:
            break
        sign = 1 if pnl > 0 else -1
        if last_sign is None:
            last_sign = sign
        if sign == last_sign:
            streak += 1
        else:
            break
    return streak


def _call_openai(prompt: str) -> dict:
    """OpenAI API を呼び出してJSONを返す。失敗時はフォールバックを返す。"""
    try:
        import config
        from openai import OpenAI

        client = OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()

        # コードブロック記号を除去してパース
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            raw = raw.rsplit("```", 1)[0]

        return json.loads(raw)

    except json.JSONDecodeError as e:
        logger.error(f"OpenAI レスポンスのJSONパース失敗: {e}")
        return _fallback_result()
    except Exception as e:
        logger.error(f"OpenAI API 呼び出し失敗: {e}")
        return _fallback_result()


def _fallback_result() -> dict:
    """API失敗時のフォールバック。"""
    return {
        "title": "本日の運用記録",
        "x_post": "🐂×🧊 今日もブルみん×ベアドンが相場と向き合いました。\n夢は推せ。でも、ちゃんと考えて推せ。🌟\n#楽天4倍ブル #投資日記 #ブルみん",
        "short_dialogue": (
            "ブルみん「今日も相場と向き合ったよ。」\n"
            "ベアドン「記録することが大事だ。」"
        ),
        "note_body": "本日の売買結果をお届けします。これは個人の運用記録です。",
        "youtube_script": "本日の運用記録です。ブルみんとベアドンが一緒に振り返ります。",
        "next_hook": "明日も一緒に相場を見ていきましょう。",
        "memory_event_suggestion": {
            "event_type": "none",
            "summary": "",
            "running_joke": "",
            "lesson": "記録を続けることが大切。",
            "future_reference": False,
        },
    }


def _normalize_market_data(md) -> dict:
    """MarketData オブジェクトまたは dict を dict に変換する。"""
    if isinstance(md, dict):
        return md
    return {
        "nikkei_close": getattr(md, "nikkei_close", 0),
        "nikkei_change": getattr(md, "nikkei_change", 0),
        "sp500_close": getattr(md, "sp500_close", 0),
        "sp500_change": getattr(md, "sp500_change", 0),
        "cme_nikkei_close": getattr(md, "cme_nikkei_close", 0),
        "cme_nikkei_change": getattr(md, "cme_nikkei_change", 0),
        "usdjpy_rate": getattr(md, "usdjpy_rate", 0),
        "vix_close": getattr(md, "vix_close", 0),
        "vix_change": getattr(md, "vix_change", 0),
        "us10y_rate": getattr(md, "us10y_rate", 0),
        "us10y_change": getattr(md, "us10y_change", 0),
    }


def _normalize_portfolio(pf) -> dict:
    """Portfolio オブジェクトまたは dict を dict に変換する。"""
    if isinstance(pf, dict):
        return pf
    return {
        "total_capital": getattr(pf, "total_capital", 0),
        "available_capital": getattr(pf, "available_capital", 0),
        "current_position_value": getattr(pf, "current_position_value", 0),
        "total_deposited": getattr(pf, "total_deposited", 0),
        "trade_count": getattr(pf, "trade_count", 0),
        "last_signal_action": getattr(pf, "last_signal_action", "HOLD"),
        "last_signal_confidence": getattr(pf, "last_signal_confidence", 0.5),
        "last_sell_parts": getattr(pf, "last_sell_parts", 0),
    }
