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

    usdjpy_rate: float
    usdjpy_change: float
    usdjpy_change_pct: float

    cme_nikkei_close: float
    cme_nikkei_change: float
    cme_nikkei_change_pct: float

    vix_close: float
    vix_change: float
    vix_change_pct: float

    us10y_rate: float
    us10y_change: float
    us10y_change_pct: float

    data_as_of: str = ""


def _fetch_ticker(symbol: str) -> tuple[float, float, float, str]:
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="5d")
    if len(hist) < 2:
        raise ValueError(f"{symbol}: データが2行未満")
    close_today = float(hist["Close"].iloc[-1])
    close_prev = float(hist["Close"].iloc[-2])
    change = close_today - close_prev
    change_pct = (change / close_prev) * 100
    # タイムゾーンを除いた日付文字列
    data_date = str(hist.index[-1].date())
    return close_today, change, change_pct, data_date


def fetch_market_data() -> MarketData:
    nikkei = _fetch_ticker("^N225")
    sp500 = _fetch_ticker("^GSPC")
    nasdaq = _fetch_ticker("^IXIC")
    usdjpy = _fetch_ticker("USDJPY=X")
    cme = _fetch_ticker("NKD=F")
    vix = _fetch_ticker("^VIX")
    us10y = _fetch_ticker("^TNX")
    print(f"[market_data] 日経基準日={nikkei[3]} S&P500={sp500[3]} VIX={vix[3]}")

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
        usdjpy_rate=usdjpy[0],
        usdjpy_change=usdjpy[1],
        usdjpy_change_pct=usdjpy[2],
        cme_nikkei_close=cme[0],
        cme_nikkei_change=cme[1],
        cme_nikkei_change_pct=cme[2],
        vix_close=vix[0],
        vix_change=vix[1],
        vix_change_pct=vix[2],
        us10y_rate=us10y[0],
        us10y_change=us10y[1],
        us10y_change_pct=us10y[2],
        data_as_of=nikkei[3],
    )
