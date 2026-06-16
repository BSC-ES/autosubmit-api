from abc import ABC, abstractmethod
from typing import Optional


class RuntimePerChunkStrategy(ABC):
    """Interface for calculating the average runtime per chunk unit."""

    @abstractmethod
    def calculate(
        self, expid: str, chunk_unit: str, chunk_size: int
    ) -> Optional[float]: ...


# TODO: Implement a strategy that computes the average runtime per chunk unit
# based on the last N completed chunks. Need to think about this...


class FallbackStrategy(RuntimePerChunkStrategy):
    """Fallback strategy that returns None when there is not enough data
    to calculate the average runtime per chunk unit."""

    def calculate(
        self, expid: str, chunk_unit: str, chunk_size: int
    ) -> Optional[float]:
        return None
