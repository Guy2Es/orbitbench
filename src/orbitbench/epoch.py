# src/orbitbench/epoch.py
"""UTCGregorian epochs ("01 Jan 2026 00:00:00.000") as integer milliseconds.

Leap seconds are ignored: the instances span a few hours, far from any leap second.
"""
import re
from datetime import datetime, timedelta

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
EPOCH_PATTERN = r"\d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2}(?:\.\d{1,3})?"
_EPOCH = re.compile(r"^(\d{2}) ([A-Z][a-z]{2}) (\d{4}) (\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?$")
_ORIGIN = datetime(1970, 1, 1)
_MS = timedelta(milliseconds=1)


def parse_epoch(text: str) -> int:
    """Milliseconds since 1970. Raises ValueError on a malformed or impossible date."""
    m = _EPOCH.match(text)
    if not m or m.group(2) not in MONTHS:
        raise ValueError(f"not a UTCGregorian epoch: {text!r}")
    day, year, hour, minute, second = (int(m.group(i)) for i in (1, 3, 4, 5, 6))
    millis = int((m.group(7) or "0").ljust(3, "0"))
    try:
        date = datetime(year, MONTHS.index(m.group(2)) + 1, day, hour, minute, second)
    except ValueError as exc:
        raise ValueError(f"not a UTCGregorian epoch: {text!r} ({exc})") from None
    return (date - _ORIGIN) // _MS + millis


def format_epoch(ms: int) -> str:
    dt = _ORIGIN + timedelta(milliseconds=ms)
    return (f"{dt.day:02d} {MONTHS[dt.month - 1]} {dt.year:04d} "
            f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}.{dt.microsecond // 1000:03d}")


def add_seconds(text: str, seconds: float) -> str:
    """The epoch `seconds` later, rounded to the millisecond."""
    return format_epoch(parse_epoch(text) + round(seconds * 1000))
