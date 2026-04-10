from __future__ import annotations

from io import BytesIO

import pandas as pd
from fastapi import UploadFile


AUTO_SUGGESTIONS = {
    "email": "email",
    "email_address": "email",
    "first_name": "first_name",
    "firstname": "first_name",
    "last_name": "last_name",
    "lastname": "last_name",
}


def normalize_header(header: str) -> str:
    return "_".join(str(header).strip().lower().split())


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def read_excel_with_header_detection(raw_bytes: bytes) -> pd.DataFrame:
    dataframe = pd.read_excel(BytesIO(raw_bytes), engine="openpyxl")
    if dataframe.empty:
        return dataframe

    normalized_columns = [normalize_header(column) for column in dataframe.columns]
    has_placeholder_columns = any(column.startswith("unnamed") for column in normalized_columns)
    first_row_values = [
        clean_cell(value)
        for value in dataframe.iloc[0].tolist()
        if clean_cell(value)
    ]
    normalized_first_row = [normalize_header(value) for value in first_row_values]

    # Some exports include a title row before the real headers. If the first data row
    # looks more like a header row than pandas' detected columns, re-read from row 2.
    first_row_has_email = any(value in {"email", "email_address"} for value in normalized_first_row)
    columns_have_email = any(value in {"email", "email_address"} for value in normalized_columns)
    if has_placeholder_columns and first_row_has_email and not columns_have_email:
        return pd.read_excel(BytesIO(raw_bytes), engine="openpyxl", header=1)

    return dataframe


def read_csv_with_delimiter_detection(raw_bytes: bytes) -> pd.DataFrame:
    try:
        dataframe = pd.read_csv(BytesIO(raw_bytes), sep=None, engine="python")
    except Exception:
        # Fall back to the default comma parser if Python's CSV sniffer cannot
        # infer the delimiter from a very small or unusual file.
        dataframe = pd.read_csv(BytesIO(raw_bytes))

    if dataframe.empty:
        return dataframe

    normalized_columns = [normalize_header(column) for column in dataframe.columns]
    first_row_values = [
        clean_cell(value)
        for value in dataframe.iloc[0].tolist()
        if clean_cell(value)
    ]
    normalized_first_row = [normalize_header(value) for value in first_row_values]
    first_row_has_email = any(value in {"email", "email_address"} for value in normalized_first_row)
    columns_have_email = any(value in {"email", "email_address"} for value in normalized_columns)

    if first_row_has_email and not columns_have_email:
        try:
            return pd.read_csv(BytesIO(raw_bytes), sep=None, engine="python", header=1)
        except Exception:
            return pd.read_csv(BytesIO(raw_bytes), header=1)

    return dataframe


def read_upload_to_dataframe(filename: str, raw_bytes: bytes) -> pd.DataFrame:
    lowered_filename = filename.lower()
    if lowered_filename.endswith(".xlsx"):
        return read_excel_with_header_detection(raw_bytes)
    if lowered_filename.endswith(".csv"):
        return read_csv_with_delimiter_detection(raw_bytes)
    raise ValueError("The uploaded file must be .xlsx or .csv")


def clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.dropna(axis="columns", how="all")
    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    dataframe = dataframe.loc[:, [not normalize_header(column).startswith("unnamed") for column in dataframe.columns]]
    return dataframe.dropna(how="all")


async def parse_excel_upload(file: UploadFile) -> dict:
    if not file.filename:
        raise ValueError("The uploaded file must be .xlsx or .csv")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise ValueError("Uploaded file is empty")

    dataframe = read_upload_to_dataframe(file.filename, raw_bytes)
    if dataframe.empty:
        raise ValueError("Uploaded file is empty")

    dataframe = clean_dataframe(dataframe)
    if dataframe.empty:
        raise ValueError("Uploaded file is empty")

    rows = []
    for row in dataframe.to_dict(orient="records"):
        cleaned_row = {str(key).strip(): clean_cell(value) for key, value in row.items()}
        rows.append(cleaned_row)

    if not rows:
        raise ValueError("Must detect at least one row")

    headers = list(dataframe.columns)
    normalized_headers = {header: normalize_header(header) for header in headers}
    suggestions = {
        header: AUTO_SUGGESTIONS.get(normalized_headers[header], "")
        for header in headers
    }

    duplicate_email_columns = {}
    for header in headers:
        lowered_values = [row[header].lower() for row in rows if row[header]]
        counts = {}
        for email in lowered_values:
            counts[email] = counts.get(email, 0) + 1
        duplicate_email_columns[header] = sorted(
            [email for email, count in counts.items() if count > 1]
        )

    return {
        "headers": headers,
        "preview_rows": rows[:5],
        "normalized_headers": normalized_headers,
        "suggestions": suggestions,
        "row_count": len(rows),
        "duplicate_email_columns": duplicate_email_columns,
        "rows": rows,
    }
