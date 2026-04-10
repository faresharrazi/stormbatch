from __future__ import annotations


def build_bulk_job_payload(rows: list[dict], mapping: dict[str, str]) -> list[dict]:
    tasks = []
    for row in rows:
        fields = []
        for column_name, attribute_id in mapping.items():
            value = row.get(column_name, "").strip()
            if not value:
                if attribute_id == "email":
                    raise ValueError("The Excel file must include an Email column")
                continue
            fields.append({"id": attribute_id, "value": value})
        tasks.append({"fields": fields})
    return tasks
