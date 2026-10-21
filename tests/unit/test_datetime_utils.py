from datetime import datetime, date
from app.core.utils.datetime_utils import ensure_utc_datetime


def test_ensure_utc_datetime():
    assert ensure_utc_datetime(None) is None
    d = date(2026, 10, 21)
    dt = ensure_utc_datetime(d)
    assert isinstance(dt, datetime)
    assert dt.year == 2026
    assert dt.month == 10
    assert dt.day == 21
