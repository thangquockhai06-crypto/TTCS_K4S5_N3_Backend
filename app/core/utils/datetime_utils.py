from datetime import datetime, date, timezone, timedelta
from typing import Optional


def ensure_utc_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return datetime.combine(dt, datetime.min.time())
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def format_vietnamese_datetime(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    # Giả định múi giờ UTC+7
    vn_dt = dt + timedelta(hours=7)
    return vn_dt.strftime("%H:%M ngày %d/%m/%Y")
