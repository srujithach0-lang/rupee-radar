import csv
import io
import re

from app.models.enums import TransactionType
from app.parsers.base import ParseResult, RawTransaction
from app.parsers.common import SKIP_PATTERNS, parse_amount, parse_date

ICICI_MARKERS = re.compile(r"transaction remarks|withdrawal amount", re.I)


class IciciCsvParser:
    def can_parse(self, filename: str, content_sample: bytes) -> bool:
        if not filename.lower().endswith(".csv"):
            return False
        try:
            text = content_sample.decode("utf-8-sig", errors="ignore")
        except Exception:
            return False
        first_line = text.splitlines()[0].lower() if text.splitlines() else ""
        if "narration" in first_line and "withdrawal" in first_line:
            return False
        return bool(ICICI_MARKERS.search(first_line))

    def parse(self, file: io.BufferedIOBase, filename: str) -> ParseResult:
        text = file.read().decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return ParseResult(warnings=["No headers found in CSV"])

        field_map = {name.strip().lower(): name for name in reader.fieldnames}

        date_col = _pick_column(field_map, ["transaction date", "value date", "date"])
        desc_col = _pick_column(field_map, ["transaction remarks", "remarks", "description", "narration"])
        withdrawal_col = _pick_column(
            field_map,
            ["withdrawal amount (inr)", "withdrawal amount", "withdrawal amt.", "debit", "debit amount"],
        )
        deposit_col = _pick_column(
            field_map,
            ["deposit amount (inr)", "deposit amount", "deposit amt.", "credit", "credit amount"],
        )
        balance_col = _pick_column(field_map, ["balance (inr)", "balance", "closing balance"])

        missing = [name for name, col in [("date", date_col), ("description", desc_col)] if not col]
        if missing:
            return ParseResult(warnings=[f"Missing columns: {', '.join(missing)}"])
        if not withdrawal_col and not deposit_col:
            return ParseResult(warnings=["Missing amount columns (withdrawal/deposit or debit/credit)"])

        transactions: list[RawTransaction] = []
        warnings: list[str] = []

        for row_num, row in enumerate(reader, start=2):
            narration = (row.get(desc_col) or "").strip()
            date_raw = (row.get(date_col) or "").strip()

            if not narration or SKIP_PATTERNS.search(narration):
                warnings.append(f"Row {row_num}: skipped summary or empty row")
                continue

            iso_date = parse_date(date_raw)
            if not iso_date:
                warnings.append(f"Row {row_num}: invalid date '{date_raw}'")
                continue

            withdrawal = parse_amount(row.get(withdrawal_col) or "") if withdrawal_col else None
            deposit = parse_amount(row.get(deposit_col) or "") if deposit_col else None
            balance = parse_amount(row.get(balance_col) or "") if balance_col else None

            if withdrawal and withdrawal > 0:
                amount = -abs(withdrawal)
                txn_type = TransactionType.DEBIT
            elif deposit and deposit > 0:
                amount = abs(deposit)
                txn_type = TransactionType.CREDIT
            else:
                warnings.append(f"Row {row_num}: no valid amount")
                continue

            transactions.append(
                RawTransaction(
                    date=iso_date,
                    description_raw=narration,
                    amount=amount,
                    type=txn_type,
                    balance=balance,
                )
            )

        if not transactions:
            warnings.append("No transactions found in file")

        return ParseResult(transactions=transactions, warnings=warnings)


def _pick_column(field_map: dict[str, str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in field_map:
            return field_map[candidate]
    return None


icici_parser = IciciCsvParser()
