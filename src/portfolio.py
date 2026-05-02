import json
import os
from datetime import datetime
import config

STATE_FILE = "portfolio_state.json"


class Portfolio:
    def __init__(self):
        self.total_capital: int = config.CAPITAL
        self.available_capital: int = config.CAPITAL
        self.current_position_value: int = 0
        self.trade_count: int = 0
        self.last_updated: str = datetime.now().isoformat()

    def load(self) -> "Portfolio":
        if not os.path.exists(STATE_FILE):
            self.save()
            return self
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.total_capital = data.get("total_capital", config.CAPITAL)
        self.available_capital = data.get("available_capital", config.CAPITAL)
        self.current_position_value = data.get("current_position_value", 0)
        self.trade_count = data.get("trade_count", 0)
        self.last_updated = data.get("last_updated", datetime.now().isoformat())
        return self

    def save(self):
        self.last_updated = datetime.now().isoformat()
        data = {
            "total_capital": self.total_capital,
            "available_capital": self.available_capital,
            "current_position_value": self.current_position_value,
            "trade_count": self.trade_count,
            "last_updated": self.last_updated,
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def can_buy(self, amount: int) -> bool:
        return self.available_capital >= amount

    def can_sell(self, amount: int) -> bool:
        return self.current_position_value >= amount

    def record_trade(self, action: str, amount: int):
        if action == "BUY":
            self.available_capital -= amount
            self.current_position_value += amount
        elif action == "SELL":
            self.current_position_value -= amount
            self.available_capital += amount
        self.trade_count += 1
        self.save()

    def parts_used(self) -> int:
        return int(self.current_position_value / (self.total_capital / 10))

    def parts_available(self) -> int:
        return 10 - self.parts_used()
