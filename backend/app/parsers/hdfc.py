import csv
import io

from app.models.enums import TransactionType
from app.parsers.base import ParseResult, RawTransaction
from app.parsers.common import SKIP_PATTERNS, parse_amount, parse_date


class HdfcCsvParser:
    def can_parse(self, filename: str, content_sample: bytes) -> bool:
        if not filename.lower().endswith(".csv"):
            return False
        try:
            text = content_sample.decode("utf-8-sig", errors="ignore")
        except Exception:
            return False
        first_line = text.splitlines()[0].lower() if text.splitlines() else ""
        return "narration" in first_line and "withdrawal" in first_line

    def parse(self, file: io.BufferedIOBase, filename: str) -> ParseResult:
        text = file.read().decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return ParseResult(warnings=["No headers found in CSV"])

        field_map = {name.strip().lower(): name for name in reader.fieldnames}
        required = ["date", "narration", "withdrawal amt.", "deposit amt."]
        missing = [col for col in required if col not in field_map]
        if missing:
            return ParseResult(warnings=[f"Missing columns: {', '.join(missing)}"])

        transactions: list[RawTransaction] = []
        warnings: list[str] = []

        for row_num, row in enumerate(reader, start=2):
            narration = (row.get(field_map["narration"]) or "").strip()
            date_raw = (row.get(field_map["date"]) or "").strip()

            if not narration or SKIP_PATTERNS.search(narration):
                warnings.append(f"Row {row_num}: skipped summary or empty row")
                continue

            iso_date = parse_date(date_raw)
            if not iso_date:
                warnings.append(f"Row {row_num}: invalid date '{date_raw}'")
                continue

            withdrawal = parse_amount(row.get(field_map["withdrawal amt."]) or "")
            deposit = parse_amount(row.get(field_map["deposit amt."]) or "")

            balance = None
            if "closing balance" in field_map:
                balance = parse_amount(row.get(field_map["closing balance"]) or "")

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


hdfc_parser = HdfcCsvParser()
