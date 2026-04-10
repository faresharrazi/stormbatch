import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.excel_parser import clean_cell, read_excel_with_header_detection
from app.services.livestorm_client import LivestormClient
from app.services.mapping_service import normalize_session_ids


ROOT = Path(__file__).resolve().parents[1]


def load_env_value(name: str) -> str:
    for line in (ROOT / ".env").read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key == name:
            return value.strip().strip('"').strip("'")
    return ""


def load_emails(excel_path: Path) -> list[str]:
    dataframe = read_excel_with_header_detection(excel_path.read_bytes())
    rows = [
        {str(key).strip(): clean_cell(value) for key, value in row.items()}
        for row in dataframe.to_dict(orient="records")
    ]
    return [row["Email"] for row in rows if row.get("Email")]


async def main() -> None:
    excel_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "test" / "list.xlsx"
    api_key = load_env_value("LS_KEY")
    if not api_key:
        raise SystemExit("LS_KEY missing from .env")

    emails = load_emails(excel_path)
    sessions = normalize_session_ids((ROOT / "test" / "session.txt").read_text())

    async with LivestormClient(api_key=api_key) as client:
        for session_id in sessions:
            print(f"SESSION {session_id}")
            for email in emails:
                matches = await client.list_session_people(session_id=session_id, email=email)
                print(f"EMAIL {email} registered={bool(matches)} matches={len(matches)}")


if __name__ == "__main__":
    asyncio.run(main())
