def sanitize_title(title: str) -> str:
    return title.strip()[:255]
