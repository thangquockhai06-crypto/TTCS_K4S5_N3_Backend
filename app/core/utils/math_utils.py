def calculate_percentage(part: int, whole: int) -> float:
    return round((part / whole * 100.0), 2) if whole > 0 else 0.0
