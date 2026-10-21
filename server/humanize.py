from __future__ import annotations

import time
from datetime import datetime


def clock(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%I:%M %p").lstrip("0")


def ago(ts: float, now: float | None = None) -> str:
    seconds = int((time.time() if now is None else now) - ts)
    if seconds < 45:
        return "just now"
    if seconds < 90:
        return "about a minute ago"
    minutes = round(seconds / 60)
    if minutes < 60:
        return f"{minutes} minutes ago"
    hours = round(seconds / 3600)
    if hours < 24:
        return "about an hour ago" if hours == 1 else f"about {hours} hours ago"
    days = round(hours / 24)
    return "yesterday" if days == 1 else f"{days} days ago"


def join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" and {items[-1]}"
