import csv
import io
import re

from app.models.enums import TransactionType
from app.parsers.base import ParseResult, RawTransaction
from app.parsers.common import SKIP_PATTERNS, parse_amount, parse_date

DATE_HEADERS = ("date", "transaction date", "txn date", "value date", "posting date")
DESC_HEADERS = ("description", "narration", "details", "remarks", "transaction remarks", "particulars")
WITHDRAWAL_HEADERS = ("withdrawal", "withdrawal amt.", "withdrawal amount", "debit", "debit amount", "dr")
DEPOSIT_HEADERS = ("deposit", "deposit amt.", "deposit amount", "credit", "credit amount", "cr")
AMOUNT_HEADERS = ("amount", "transaction amount", "txn amount")
TYPE_HEADERS = ("type", "dr/cr", "debit/credit")


class GenericCsvParser:
    def can_parse(self, filename: str, content_sample: bytes) -> bool:
        if not filename.lower().endswith(".csv"):
            return False
        try:
            text = content_sample.decode("utf-8-sig", errors="ignore")
        except Exception:
            return False
        if not text.strip():
            return False
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return False
        field_map = {name.strip().lower(): name for name in reader.fieldnames}
        return _detect_columns(field_map) is not None

    def parse(self, file: io.BufferedIOBase, filename: str) -> ParseResult:
        text = file.read().decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return ParseResult(warnings=["No headers found in CSV"])

        field_map = {name.strip().lower(): name for name in reader.fieldnames}
        columns = _detect_columns(field_map)
        if not columns:
            return ParseResult(
                warnings=[
                    "Could not detect required columns. "
                    "Use our sample template: docs/sample-statement-template.csv"
                ]
            )

        transactions: list[RawTransaction] = []
        warnings: list[str] = []

        for row_num, row in enumerate(reader, start=2):
            narration = (row.get(columns["description"]) or "").strip()
            date_raw = (row.get(columns["date"]) or "").strip()

            if not narration or SKIP_PATTERNS.search(narration):
                warnings.append(f"Row {row_num}: skipped summary or empty row")
                continue

            iso_date = parse_date(date_raw)
            if not iso_date:
                warnings.append(f"Row {row_num}: invalid date '{date_raw}'")
                continue

            amount: float | None = None
            txn_type: TransactionType | None = None

            if columns.get("withdrawal") or columns.get("deposit"):
                withdrawal = parse_amount(row.get(columns.get("withdrawal", "")) or "")
                deposit = parse_amount(row.get(columns.get("deposit", "")) or "")
                if withdrawal and withdrawal > 0:
                    amount = -abs(withdrawal)
                    txn_type = TransactionType.DEBIT
                elif deposit and deposit > 0:
                    amount = abs(deposit)
                    txn_type = TransactionType.CREDIT
            elif columns.get("amount"):
                raw_amount = parse_amount(row.get(columns["amount"]) or "")
                if raw_amount is None:
                    warnings.append(f"Row {row_num}: invalid amount")
                    continue
                type_col = columns.get("type")
                type_hint = (row.get(type_col) or "").strip().lower() if type_col else ""
                if type_hint in ("dr", "debit", "d"):
                    amount = -abs(raw_amount)
                    txn_type = TransactionType.DEBIT
                elif type_hint in ("cr", "credit", "c"):
                    amount = abs(raw_amount)
                    txn_type = TransactionType.CREDIT
                elif raw_amount < 0:
                    amount = raw_amount
                    txn_type = TransactionType.DEBIT
                else:
                    amount = abs(raw_amount)
                    txn_type = TransactionType.CREDIT

            if amount is None or txn_type is None:
                warnings.append(f"Row {row_num}: no valid amount")
                continue

            balance = None
            if columns.get("balance"):
                balance = parse_amount(row.get(columns["balance"]) or "")

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


def _detect_columns(field_map: dict[str, str]) -> dict[str, str] | None:
    date_col = _first_match(field_map, DATE_HEADERS)
    desc_col = _first_match(field_map, DESC_HEADERS)
    if not date_col or not desc_col:
        return None

    withdrawal_col = _first_match(field_map, WITHDRAWAL_HEADERS)
    deposit_col = _first_match(field_map, DEPOSIT_HEADERS)
    amount_col = _first_match(field_map, AMOUNT_HEADERS)
    type_col = _first_match(field_map, TYPE_HEADERS)
    balance_col = _first_match(field_map, ("balance", "closing balance"))

    if withdrawal_col or deposit_col:
        return {
            "date": date_col,
            "description": desc_col,
            "withdrawal": withdrawal_col or "",
            "deposit": deposit_col or "",
            "balance": balance_col or "",
        }
    if amount_col:
        return {
            "date": date_col,
            "description": desc_col,
            "amount": amount_col,
            "type": type_col or "",
            "balance": balance_col or "",
        }
    return None


def _first_match(field_map: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in field_map:
            return field_map[candidate]
        for key, original in field_map.items():
            if re.sub(r"[^a-z0-9]", "", key) == re.sub(r"[^a-z0-9]", "", candidate):
                return original
    return None


generic_parser = GenericCsvParser()
