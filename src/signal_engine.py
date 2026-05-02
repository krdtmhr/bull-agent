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

    if futures_down and sp500_down:
        confidence = min(0.9, 0.6 + (abs_futures_change / 3000))
        return RuleSignal(
            action="BUY",
            amount=amount,
            reason=f"CME日経先物が{data.cme_nikkei_change:+.0f}円安、S&P500が{data.sp500_change:+.2f}ポイント下落。下落局面での押し目買いシグナル。",
            confidence=round(confidence, 2),
        )

    if futures_up and sp500_up:
        confidence = min(0.9, 0.6 + (abs_futures_change / 3000))
        return RuleSignal(
            action="SELL",
            amount=amount,
            reason=f"CME日経先物が{data.cme_nikkei_change:+.0f}円高、S&P500が{data.sp500_change:+.2f}ポイント上昇。上昇局面での利益確定シグナル。",
            confidence=round(confidence, 2),
        )

    return RuleSignal(
        action="HOLD",
        amount=0,
        reason=f"CME日経先物とS&P500の方向性が一致しないため様子見。先物: {data.cme_nikkei_change:+.0f}円、S&P500: {data.sp500_change:+.2f}pts。",
        confidence=0.5,
    )
