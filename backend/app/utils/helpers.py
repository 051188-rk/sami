"""Shared utility functions."""

import re


def normalize_phone(phone: str) -> str:
    """Strip non-digit characters and ensure a leading + for international format."""
    digits = re.sub(r"\D", "", phone)
    if not digits.startswith("+"):
        if len(digits) == 10:
            # Assume US number
            digits = "+1" + digits
        elif len(digits) > 10:
            digits = "+" + digits
    return digits


def format_time_12h(time_24: str) -> str:
    """Convert 'HH:MM' to '12:00 PM' format."""
    try:
        hour, minute = map(int, time_24.split(":"))
        period = "AM" if hour < 12 else "PM"
        hour_12 = hour % 12 or 12
        return f"{hour_12}:{minute:02d} {period}"
    except Exception:
        return time_24
