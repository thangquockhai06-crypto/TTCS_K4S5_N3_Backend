from typing import List, Tuple


def parse_milestone_key(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes}m"
    if minutes < 1440:
        hours = minutes // 60
        return f"{hours}h"
    days = minutes // 1440
    return f"{days}d"


def get_applicable_milestones(remaining_seconds: float, configured_minutes: List[int]) -> List[Tuple[int, str]]:
    applicable = []
    rem_min = remaining_seconds / 60.0
    for m in sorted(configured_minutes, reverse=True):
        if rem_min <= float(m):
            applicable.append((m, f"{m}m"))
    return applicable
