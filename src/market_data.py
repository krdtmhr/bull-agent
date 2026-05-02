import yfinance as yf
from dataclasses import dataclass
from typing import Optional


@dataclass
class MarketData:
    nikkei_close: float
    nikkei_change: float
    nikkei_change_pct: float

    sp500_close: float
    sp500_change: float
    sp500_change_pct: float

    nasdaq_close: float
    nasdaq_change: float
    nasdaq_change_pct: float

    dow_close: float
    dow_change: float
    dow_change_pct: float

    usdjpy_rate: float
    usdjpy_change: float
    usdjpy_change_pct: float

    cme_nikkei_close: float
    cme_nikkei_change: float
    cme_nikkei_change_pct: float


def _fetch_ticker(symbol: str) -> tuple[float, float, float]:
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="2d")
    if len(hist) < 2:
        hist = ticker.history(period="5d")
    close_today = float(hist["Close"].iloc[-1])
    close_prev = float(hist["Close"].iloc[-2])
    change = close_today - close_prev
    change_pct = (change / close_prev) * 100
    return close_today, change, change_pct


def fetch_market_data() -> MarketData:
    nikkei = _fetch_ticker("^N225")
    sp500 = _fetch_ticker("^GSPC")
    nasdaq = _fetch_ticker("^IXIC")
    dow = _fetch_ticker("^DJI")
    usdjpy = _fetch_ticker("USDJPY=X")
    cme = _fetch_ticker("NKD=F")

    return MarketData(
        nikkei_close=nikkei[0],
        nikkei_change=nikkei[1],
        nikkei_change_pct=nikkei[2],
        sp500_close=sp500[0],
        sp500_change=sp500[1],
        sp500_change_pct=sp500[2],
        nasdaq_close=nasdaq[0],
        nasdaq_change=nasdaq[1],
        nasdaq_change_pct=nasdaq[2],
        dow_close=dow[0],
        dow_change=dow[1],
        dow_change_pct=dow[2],
        usdjpy_rate=usdjpy[0],
        usdjpy_change=usdjpy[1],
        usdjpy_change_pct=usdjpy[2],
        cme_nikkei_close=cme[0],
        cme_nikkei_change=cme[1],
        cme_nikkei_change_pct=cme[2],
    )
