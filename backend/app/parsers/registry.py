from typing import BinaryIO

from app.parsers.base import ParseResult, StatementParser
from app.parsers.excel_loader import xlsx_to_csv_bytes
from app.parsers.generic import generic_parser
from app.parsers.hdfc import hdfc_parser
from app.parsers.icici import icici_parser

PARSERS: list[StatementParser] = [hdfc_parser, icici_parser, generic_parser]

UNSUPPORTED_MESSAGE = (
    "Unsupported file format. Supported: HDFC CSV, ICICI CSV, generic CSV, or Excel (.xlsx). "
    "Download the sample template from docs/sample-statement-template.csv"
)


def get_parser(filename: str, content: bytes) -> StatementParser | None:
    sample = content[:4096]
    for parser in PARSERS:
        if parser.can_parse(filename, sample):
            return parser
    return None


def parse_statement(file: BinaryIO, filename: str, content: bytes) -> tuple[ParseResult, StatementParser | None]:
    normalized_filename = filename
    normalized_content = content

    if filename.lower().endswith(".xlsx"):
        try:
            normalized_content = xlsx_to_csv_bytes(content)
            normalized_filename = filename.rsplit(".", 1)[0] + ".csv"
        except Exception:
            return ParseResult(warnings=["Failed to read Excel file. Ensure it is a valid .xlsx workbook."]), None

    parser = get_parser(normalized_filename, normalized_content)
    if not parser:
        return ParseResult(warnings=[UNSUPPORTED_MESSAGE]), None

    file_obj = file
    if normalized_content is not content:
        import io

        file_obj = io.BytesIO(normalized_content)

    return parser.parse(file_obj, normalized_filename), parser
