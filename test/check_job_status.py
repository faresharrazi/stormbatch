import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.livestorm_client import LivestormClient


ROOT = Path(__file__).resolve().parents[1]


def load_env_value(name: str) -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key == name:
            return value.strip().strip('"').strip("'")
    return ""


async def main() -> None:
    if len(sys.argv) < 3 or len(sys.argv[1:]) % 2:
        raise SystemExit("Usage: python3 test/check_job_status.py SESSION_ID JOB_ID [...]")

    api_key = load_env_value("LS_KEY")
    if not api_key:
        raise SystemExit("LS_KEY missing from .env")

    async with LivestormClient(api_key=api_key) as client:
        pairs = zip(sys.argv[1::2], sys.argv[2::2])
        for session_id, job_id in pairs:
            result = await client.get_job_status(session_id=session_id, job_id=job_id)
            print(
                f"JOB session={session_id} job={job_id} "
                f"status={result['status']} tasks={len(result.get('tasks', []))}"
            )
            for index, task in enumerate(result.get("tasks", []), start=1):
                attributes = task.get("attributes", {}) if isinstance(task, dict) else {}
                status = attributes.get("status") or task.get("status", "unknown")
                error = attributes.get("error") or attributes.get("errors") or task.get("error", "")
                print(f"TASK row={index} status={status} error={error}")


if __name__ == "__main__":
    asyncio.run(main())
