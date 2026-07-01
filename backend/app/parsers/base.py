from dataclasses import dataclass, field
from typing import BinaryIO, Protocol

from app.models.enums import TransactionType


@dataclass
class RawTransaction:
    date: str
    description_raw: str
    amount: float
    type: TransactionType
    balance: float | None = None


@dataclass
class ParseResult:
    transactions: list[RawTransaction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class StatementParser(Protocol):
    def can_parse(self, filename: str, content_sample: bytes) -> bool: ...

    def parse(self, file: BinaryIO, filename: str) -> ParseResult: ...
