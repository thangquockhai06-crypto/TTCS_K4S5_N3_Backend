def format_duration_vietnamese(seconds: float) -> str:
    if seconds <= 0:
        return "vừa xong"

    total_minutes = int(seconds // 60)
    total_hours = int(seconds // 3600)
    total_days = int(seconds // 86400)

    if total_days > 0:
        rem_hours = int((seconds % 86400) // 3600)
        if rem_hours > 0:
            return f"{total_days} ngày {rem_hours} giờ"
        return f"{total_days} ngày"

    if total_hours > 0:
        rem_minutes = int((seconds % 3600) // 60)
        if rem_minutes > 0:
            return f"{total_hours} giờ {rem_minutes} phút"
        return f"{total_hours} giờ"

    return f"{max(1, total_minutes)} phút"
