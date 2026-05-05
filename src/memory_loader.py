"""過去ログからLLMに渡す記憶コンテキストを生成するモジュール。"""


def build_memory_context(recent_trades: list, recent_memories: list) -> dict:
    """LLMに渡す記憶コンテキストを生成する。"""
    if not recent_trades:
        return {
            "recent_summary": "まだトレードの記録がありません。今日が初日です。",
            "streak": {"type": "none", "count": 0},
            "notable_events": [],
            "running_jokes": [],
            "character_growth": {
                "bullmin": "まだ始まったばかり。勢いだけで動いている。",
                "beardon": "まだ始まったばかり。否定が多い。",
            },
        }

    last5 = recent_trades[-5:]
    wins = sum(1 for t in last5 if _to_float(t.get("realized_pnl", 0)) > 0)
    losses = sum(1 for t in last5 if _to_float(t.get("realized_pnl", 0)) < 0)
    holds = sum(1 for t in last5 if t.get("action") == "HOLD")

    recent_summary = f"直近{len(last5)}日は{wins}勝{losses}敗"
    if holds:
        recent_summary += f"・様子見{holds}回"
    last_action = recent_trades[-1].get("action", "不明")
    recent_summary += f"。前回は{last_action}。"

    first_val = _to_float(recent_trades[0].get("total_value", 0))
    last_val = _to_float(recent_trades[-1].get("total_value", 0))
    if last_val > first_val:
        recent_summary += "総資産は上昇傾向。"
    elif last_val < first_val:
        recent_summary += "総資産はやや減少傾向。"
    else:
        recent_summary += "総資産はほぼ横ばい。"

    streak = _calc_streak(recent_trades)

    notable_events = []
    for m in recent_memories:
        ref = m.get("future_reference", "")
        if str(ref).upper() in ("TRUE", "1", "YES"):
            summary = m.get("summary", "")
            if summary:
                day = m.get("day", "?")
                notable_events.append(f"Day {day}: {summary}")

    seen: set = set()
    running_jokes = []
    for m in recent_memories:
        joke = m.get("running_joke", "")
        if joke and joke not in seen:
            seen.add(joke)
            running_jokes.append(joke)

    total_days = len(recent_trades)
    if total_days < 5:
        bm_growth = "まだ序盤。勢いだけで動いている。"
        bd_growth = "まだ序盤。否定が多い。"
    elif total_days < 15:
        bm_growth = "失敗を少しずつ覚え始めている。"
        bd_growth = "否定しながらも、たまに改善案を出す。"
    else:
        bm_growth = "リスク管理を意識する場面が増えてきた。"
        bd_growth = "否定だけでなく、励ます場面が出てきた。"

    return {
        "recent_summary": recent_summary,
        "streak": streak,
        "notable_events": notable_events[-5:],
        "running_jokes": running_jokes[-3:],
        "character_growth": {
            "bullmin": bm_growth,
            "beardon": bd_growth,
        },
    }


def _to_float(val) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _calc_streak(trades: list) -> dict:
    """直近トレードから連勝・連敗を計算する。"""
    if not trades:
        return {"type": "none", "count": 0}

    streak_type = None
    count = 0
    for t in reversed(trades):
        action = t.get("action", "HOLD")
        if action == "HOLD":
            break
        pnl = _to_float(t.get("realized_pnl", 0))
        current = "win" if pnl > 0 else ("loss" if pnl < 0 else None)
        if current is None:
            break
        if streak_type is None:
            streak_type = current
        if current == streak_type:
            count += 1
        else:
            break

    if streak_type is None:
        return {"type": "none", "count": 0}
    return {"type": streak_type, "count": count}
