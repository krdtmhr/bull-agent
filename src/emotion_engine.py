"""キャラクターの感情状態を自動判定するモジュール。"""


def determine_emotion(
    daily_pnl: float,
    total_value: float,
    recent_pnl_list: list,
    signal: str,
    action: str,
    vix: float,
    position_size: int,
    rule_break: bool = False,
) -> dict:
    """感情状態を判定して返す。

    Returns:
        {
            "bullmin": {"mood": str, "intensity": int, "reason": str},
            "beardon": {"mood": str, "intensity": int, "reason": str},
        }
    """
    # 連勝・連敗カウント
    streak_win = 0
    streak_loss = 0
    for p in reversed(recent_pnl_list):
        if p > 0:
            if streak_loss > 0:
                break
            streak_win += 1
        elif p < 0:
            if streak_win > 0:
                break
            streak_loss += 1
        else:
            break

    pnl_pct = (daily_pnl / total_value * 100) if total_value > 0 else 0.0
    big_win = pnl_pct >= 3.0
    big_loss = pnl_pct <= -3.0

    hold_streak = 0
    if action == "HOLD":
        for p in reversed(recent_pnl_list[-5:]):
            if p == 0:
                hold_streak += 1
            else:
                break

    # ─── ブルみん感情 ───────────────────────────────────────
    if rule_break:
        bm_mood = "defensive"
        bm_intensity = 3
        bm_reason = "シグナルと異なる行動を取ったため言い訳気味になっている"
    elif big_win:
        bm_mood = "excited"
        bm_intensity = 5
        bm_reason = "大きな利益が出てテンションが最高潮"
    elif big_loss:
        bm_mood = "regretful"
        bm_intensity = 4
        bm_reason = "大きな損失が出て後悔している"
    elif streak_win >= 3:
        bm_mood = "excited" if streak_win >= 5 else "confident"
        bm_intensity = min(5, streak_win)
        bm_reason = f"{streak_win}連勝中で自信がついている"
    elif streak_loss >= 5:
        bm_mood = "anxious"
        bm_intensity = 4
        bm_reason = f"{streak_loss}連敗中で内心かなり不安になっている"
    elif streak_loss >= 3:
        bm_mood = "stubborn"
        bm_intensity = 3
        bm_reason = f"{streak_loss}連敗中だが強がっている"
    elif hold_streak >= 3:
        bm_mood = "frustrated"
        bm_intensity = 3
        bm_reason = "HOLDが続いて動けずに焦れている"
    elif streak_loss >= 1 and daily_pnl > 0:
        bm_mood = "fired_up"
        bm_intensity = 3
        bm_reason = "ドローダウン後に少し回復して取り返す気になっている"
    elif daily_pnl > 0:
        bm_mood = "confident"
        bm_intensity = 2
        bm_reason = "利益が出ていて落ち着いた自信がある"
    else:
        bm_mood = "anxious"
        bm_intensity = 2
        bm_reason = "損失があり内心少し不安"

    # ─── ベアドン感情 ───────────────────────────────────────
    if rule_break:
        bd_mood = "annoyed"
        bd_intensity = 4
        bd_reason = "ルール通りに行動しなかったことを呆れている"
    elif big_loss:
        bd_mood = "protective"
        bd_intensity = 4
        bd_reason = "大きな損失を受けて守ろうとしている"
    elif big_win:
        bd_mood = "cautious"
        bd_intensity = 3
        bd_reason = "利益は出ているが浮かれないよう注意している"
    elif vix >= 30:
        bd_mood = "worried"
        bd_intensity = 4
        bd_reason = f"VIX {vix:.1f}と危険水準で強く心配している"
    elif vix >= 25:
        bd_mood = "cautious"
        bd_intensity = 3
        bd_reason = f"VIX {vix:.1f}と警戒水準で冷静に構えている"
    elif streak_loss >= 5:
        bd_mood = "worried"
        bd_intensity = 4
        bd_reason = f"{streak_loss}連敗が続いていて本気で心配している"
    elif streak_loss >= 3:
        bd_mood = "annoyed"
        bd_intensity = 3
        bd_reason = f"{streak_loss}連敗中でブルみんに呆れている"
    elif streak_win >= 3:
        bd_mood = "cautious"
        bd_intensity = 2
        bd_reason = "連勝中だが調子に乗らないよう牽制している"
    elif hold_streak >= 3:
        bd_mood = "calm"
        bd_intensity = 1
        bd_reason = "様子見が続いており冷静に待っている"
    elif streak_loss >= 1 and daily_pnl > 0:
        bd_mood = "encouraging"
        bd_intensity = 2
        bd_reason = "ドローダウン後の回復局面で静かに励ます"
    elif daily_pnl >= 0:
        bd_mood = "calm"
        bd_intensity = 1
        bd_reason = "特に問題ない状況で冷静"
    else:
        bd_mood = "cautious"
        bd_intensity = 2
        bd_reason = "損失を受けて警戒している"

    return {
        "bullmin": {"mood": bm_mood, "intensity": bm_intensity, "reason": bm_reason},
        "beardon": {"mood": bd_mood, "intensity": bd_intensity, "reason": bd_reason},
    }
