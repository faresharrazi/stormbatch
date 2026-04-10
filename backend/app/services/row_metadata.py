from __future__ import annotations


def build_row_results(rows: list[dict], mapping: dict[str, str]) -> list[dict]:
    email_column = next(
        (column for column, attribute_id in mapping.items() if attribute_id == "email"),
        "",
    )

    results = []
    for index, row in enumerate(rows, start=2):
        mapped_fields = []
        for column_name, attribute_id in mapping.items():
            value = row.get(column_name, "")
            mapped_fields.append(
                {
                    "column": column_name,
                    "attribute_id": attribute_id,
                    "value": value,
                }
            )

        results.append(
            {
                "row_number": index,
                "email": row.get(email_column, ""),
                "fields": mapped_fields,
            }
        )
    return results
