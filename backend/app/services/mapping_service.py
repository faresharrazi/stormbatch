from __future__ import annotations


def normalize_session_ids(raw_session_ids: str) -> list[str]:
    session_ids = [item.strip() for item in raw_session_ids.replace(",", "\n").splitlines()]
    cleaned = [session_id for session_id in session_ids if session_id]
    if not cleaned:
        raise ValueError("Session IDs must not be empty")
    return cleaned


def validate_mapping_and_rows(mapping: dict, rows: list[dict]) -> dict:
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("Excel columns could not be prepared for registration")

    duplicate_targets = set()
    used_targets = set()
    column_to_attribute = {}

    for column_name, attribute_id in mapping.items():
        value = str(attribute_id).strip()
        if not value or value == "__ignore__":
            continue
        if value in used_targets:
            duplicate_targets.add(value)
        used_targets.add(value)
        column_to_attribute[column_name] = value

    if duplicate_targets:
        raise ValueError("Duplicate normalized Excel column names are not allowed")

    email_columns = [column for column, attribute in column_to_attribute.items() if attribute == "email"]
    if not email_columns:
        raise ValueError("The file must include an Email column")

    email_column = email_columns[0]
    missing_emails = [index + 2 for index, row in enumerate(rows) if not row.get(email_column, "").strip()]
    if missing_emails:
        raise ValueError(
            "Empty email values were found in rows: " + ", ".join(str(row_number) for row_number in missing_emails[:10])
        )

    email_values = [row[email_column].strip().lower() for row in rows]
    duplicate_emails = sorted({email for email in email_values if email_values.count(email) > 1})

    return {
        "column_to_attribute": column_to_attribute,
        "duplicate_emails": duplicate_emails,
    }
