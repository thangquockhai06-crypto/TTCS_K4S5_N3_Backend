import re
import unicodedata


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFD", value or "")
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return " ".join(value.casefold().strip().split())


def normalize_tax_code(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", value or "").casefold()


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("0084"):
        digits = "0" + digits[4:]
    elif digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
