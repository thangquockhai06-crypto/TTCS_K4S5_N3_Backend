"""Tiện ích xử lý múi giờ và định dạng thời gian Việt Nam chuẩn ISO-8601."""
from datetime import datetime, timezone, timedelta

VN_TIMEZONE = timezone(timedelta(hours=7))

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

def to_vn_time(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(VN_TIMEZONE)

def format_vn_datetime(dt: datetime) -> str:
    vn_dt = to_vn_time(dt)
    return vn_dt.strftime("%d/%m/%Y %H:%M:%S")

def format_vn_date(dt: datetime) -> str:
    vn_dt = to_vn_time(dt)
    return vn_dt.strftime("%d/%m/%Y")
