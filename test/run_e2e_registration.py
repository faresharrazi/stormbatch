import asyncio
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.excel_parser import clean_cell, normalize_header, read_excel_with_header_detection
from app.services.livestorm_client import LivestormClient
from app.services.mapping_service import normalize_session_ids, validate_mapping_and_rows
from app.services.payload_builder import build_bulk_job_payload
from app.services.row_metadata import build_row_results


ROOT = Path(__file__).resolve().parents[1]
FINAL_STATUSES = {"ended", "failed", "completed"}


def load_env_value(name: str) -> str:
    env_path = ROOT / ".env"
    for line in env_path.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key == name:
            return value.strip().strip('"').strip("'")
    return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a StormBatch Livestorm e2e test.")
    parser.add_argument(
        "--file",
        default=str(ROOT / "test" / "list.xlsx"),
        help="Excel file to register.",
    )
    return parser.parse_args()


def infer_mapping(headers: list[str]) -> dict[str, str]:
    return {header: normalize_header(header) for header in headers}


def build_registration_tasks(excel_path: Path) -> tuple[list[str], list[dict], list[dict]]:
    dataframe = read_excel_with_header_detection(excel_path.read_bytes())
    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    rows = [
        {str(key).strip(): clean_cell(value) for key, value in row.items()}
        for row in dataframe.to_dict(orient="records")
    ]
    mapping = infer_mapping(list(dataframe.columns))

    validation = validate_mapping_and_rows(mapping, rows)
    sessions = normalize_session_ids((ROOT / "test" / "session.txt").read_text())
    tasks = build_bulk_job_payload(rows, validation["column_to_attribute"])
    row_results = build_row_results(rows, validation["column_to_attribute"])

    print(f"Excel file: {excel_path}", flush=True)
    print(f"Mapping: {mapping}", flush=True)
    print(f"Validated {len(rows)} registrants for {len(sessions)} sessions.", flush=True)
    print(f"Duplicate emails: {len(validation['duplicate_emails'])}", flush=True)
    return sessions, tasks, row_results


async def main() -> None:
    args = parse_args()
    api_key = load_env_value("LS_KEY")
    if not api_key:
        raise SystemExit("LS_KEY missing from .env")

    sessions, tasks, row_results = build_registration_tasks(excel_path=Path(args.file))
    created_jobs = []

    async with LivestormClient(api_key=api_key) as client:
        for session_id in sessions:
            created = await client.create_bulk_job(session_id=session_id, tasks=tasks)
            job = {
                "session_id": session_id,
                "job_id": created["job_id"],
                "status": created.get("status", "pending"),
            }
            created_jobs.append(job)
            print(
                f"CREATED session={session_id} job={job['job_id']} status={job['status']}"
                ,
                flush=True,
            )

        for attempt in range(1, 31):
            unfinished = [
                job
                for job in created_jobs
                if str(job["status"]).lower() not in FINAL_STATUSES
            ]
            if not unfinished:
                break

            await asyncio.sleep(2.5)
            print(f"POLL attempt={attempt}", flush=True)
            for job in unfinished:
                status = await client.get_job_status(
                    session_id=job["session_id"],
                    job_id=job["job_id"],
                )
                job["status"] = status["status"]
                job["tasks"] = status.get("tasks", [])
                print(
                    f"STATUS session={job['session_id']} job={job['job_id']} "
                    f"status={job['status']} tasks={len(job.get('tasks', []))}"
                    ,
                    flush=True,
                )

    print("FINAL", flush=True)
    for job in created_jobs:
        print(
            f"FINAL session={job['session_id']} job={job['job_id']} "
            f"status={job['status']} tasks={len(job.get('tasks', []))}"
            ,
            flush=True,
        )
        for index, task in enumerate(job.get("tasks", []), start=1):
            attributes = task.get("attributes", {}) if isinstance(task, dict) else {}
            status = attributes.get("status") or task.get("status", "unknown")
            error = attributes.get("error") or attributes.get("errors") or task.get("error", "")
            row = row_results[index - 1] if index - 1 < len(row_results) else {}
            fields = ", ".join(
                f"{field['attribute_id']}={field['value']}"
                for field in row.get("fields", [])
                if field.get("value")
            )
            print(
                f"TASK excel_row={row.get('row_number', index + 1)} "
                f"email={row.get('email', '')} fields=[{fields}] status={status} error={error}",
                flush=True,
            )


if __name__ == "__main__":
    asyncio.run(main())
