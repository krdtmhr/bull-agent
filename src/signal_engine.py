from dataclasses import dataclass
from src.market_data import MarketData
import config


@dataclass
class RuleSignal:
    action: str
    amount: int
    reason: str
    confidence: float


def generate_rule_signal(data: MarketData) -> RuleSignal:
    futures_down = data.cme_nikkei_change < 0
    futures_up = data.cme_nikkei_change > 0
    sp500_down = data.sp500_change < 0
    sp500_up = data.sp500_change > 0

    abs_futures_change = abs(data.cme_nikkei_change)
    is_large_move = abs_futures_change >= config.NIKKEI_LARGE_MOVE_THRESHOLD

    if is_large_move:
        amount = config.LARGE_TRADE_MIN if abs_futures_change < 1500 else config.LARGE_TRADE_MAX
    else:
        amount = config.NORMAL_TRADE

    # VIX警戒レベルによる確信度補正
    vix = data.vix_close
    if vix >= 30:
        vix_penalty = 0.25
        vix_note = f"VIX（恐怖指数）が{vix:.1f}と危険水準（30超）。"
    elif vix >= 25:
        vix_penalty = 0.15
        vix_note = f"VIX（恐怖指数）が{vix:.1f}と警戒水準（25超）。"
    else:
        vix_penalty = 0.0
        vix_note = ""

    if futures_down and sp500_down:
        confidence = min(0.9, 0.6 + (abs_futures_change / 3000))
        confidence = max(0.1, confidence - vix_penalty)
        reason = f"CME日経先物が{data.cme_nikkei_change:+.0f}円安、S&P500が{data.sp500_change:+.2f}ポイント下落。下落局面での押し目買いシグナル。"
        if vix_note:
            reason += vix_note + "レバレッジ商品は特に注意。"
        return RuleSignal(action="BUY", amount=amount, reason=reason, confidence=round(confidence, 2))

    if futures_up and sp500_up:
        confidence = min(0.9, 0.6 + (abs_futures_change / 3000))
        confidence = max(0.1, confidence - vix_penalty)
        reason = f"CME日経先物が{data.cme_nikkei_change:+.0f}円高、S&P500が{data.sp500_change:+.2f}ポイント上昇。上昇局面での利益確定シグナル。"
        if vix_note:
            reason += vix_note
        return RuleSignal(action="SELL", amount=amount, reason=reason, confidence=round(confidence, 2))

    return RuleSignal(
        action="HOLD",
        amount=0,
        reason=f"CME日経先物とS&P500の方向性が一致しないため様子見。先物: {data.cme_nikkei_change:+.0f}円、S&P500: {data.sp500_change:+.2f}pts。",
        confidence=max(0.1, 0.5 - vix_penalty),
    )
