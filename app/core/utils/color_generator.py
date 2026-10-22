def get_priority_color(priority: str) -> str:
    return {'urgent': '#EF4444', 'high': '#F59E0B'}.get(priority, '#10B981')
