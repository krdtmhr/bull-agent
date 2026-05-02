from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    def analyze(self, market_data: dict) -> str:
        pass
