import base64
import json
from datetime import datetime


def encode_cursor(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def decode_cursor(cursor: str | None) -> dict | None:
    if not cursor:
        return None
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
        return json.loads(raw)
    except Exception:
        return None


def dt_to_cursor(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.isoformat()


def cursor_to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None

