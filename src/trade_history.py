from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class TradeRecord:
    date: str
    action: str
    amount: int
    note: str = ""


class TradeHistory:
    def __init__(self):
        self.records: list = []

    def from_dict(self, data: dict) -> "TradeHistory":
        self.records = [TradeRecord(**r) for r in data.get("records", [])]
        return self

    def to_dict(self) -> dict:
        return {"records": [asdict(r) for r in self.records]}

    def add(self, action: str, amount: int, note: str = "") -> TradeRecord:
        record = TradeRecord(
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            action=action,
            amount=amount,
            note=note,
        )
        self.records.insert(0, record)
        return record

    def recent(self, n: int = 10) -> list:
        return self.records[:n]
