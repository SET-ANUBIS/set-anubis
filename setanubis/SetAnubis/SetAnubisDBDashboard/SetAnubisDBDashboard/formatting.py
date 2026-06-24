import json
from typing import Any, Optional


def human_bytes(value: Optional[float]) -> str:
    if value is None:
        return "—"
    try:
        n = float(value)
    except Exception:
        return "—"
    sign = "-" if n < 0 else ""
    n = abs(n)
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if n < 1024.0 or unit == "PB":
            if unit == "B":
                return f"{sign}{int(n)} B"
            return f"{sign}{n:.2f} {unit}"
        n /= 1024.0
    return f"{sign}{n:.2f} PB"


def human_number(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    try:
        x = float(value)
    except Exception:
        return str(value)
    if abs(x) >= 1e5 or (abs(x) > 0 and abs(x) < 1e-3):
        return f"{x:.{digits}e}"
    if abs(x - int(x)) < 1e-12:
        return f"{int(x):,}".replace(",", " ")
    return f"{x:.{digits}g}"


def human_percent(value: Optional[float], digits: int = 1) -> str:
    if value is None:
        return "—"
    try:
        return f"{100.0 * float(value):.{digits}f}%"
    except Exception:
        return "—"


def safe_ratio(num: Optional[float], den: Optional[float]) -> Optional[float]:
    try:
        if den in (None, 0):
            return None
        return float(num or 0) / float(den)
    except Exception:
        return None


def pretty_json(value: Any, max_chars: int = 24000) -> str:
    if value is None:
        return "{}"
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return value[:max_chars]
    try:
        text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:
        text = str(value)
    if len(text) > max_chars:
        return text[:max_chars] + "\n… truncated …"
    return text


def short_id(value: Optional[str], n: int = 8) -> str:
    if not value:
        return "—"
    s = str(value)
    return s if len(s) <= 2 * n + 3 else f"{s[:n]}…{s[-n:]}"
