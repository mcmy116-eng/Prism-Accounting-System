"""Tiny date-advance helper so we don't need python-dateutil for one function."""
from datetime import date
import calendar


def _add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def advance_date(d: date, frequency: str) -> date:
    if frequency == "weekly":
        from datetime import timedelta
        return d + timedelta(days=7)
    if frequency == "monthly":
        return _add_months(d, 1)
    if frequency == "quarterly":
        return _add_months(d, 3)
    if frequency == "annual":
        return _add_months(d, 12)
    return _add_months(d, 1)
