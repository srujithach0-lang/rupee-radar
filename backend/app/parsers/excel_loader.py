import io

import pandas as pd


def xlsx_to_csv_bytes(content: bytes) -> bytes:
    """Convert the first sheet of an Excel workbook to CSV bytes for parser registry."""
    df = pd.read_excel(io.BytesIO(content), engine="openpyxl", sheet_name=0)
    df = df.dropna(how="all")
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")
