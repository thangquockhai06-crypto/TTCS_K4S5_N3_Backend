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


from typing import Optional


def normalize_website(url: Optional[str]) -> str:
    """
    Chuẩn hóa domain website:
    - Bỏ scheme http://, https://
    - Bỏ tiền tố www.
    - Bỏ path, query string, trailing slash
    - Chuyển về lowercase
    """
    if not url:
        return ""
    val = url.strip().casefold()
    val = re.sub(r"^https?://", "", val)
    val = re.sub(r"^www\.", "", val)
    val = val.split("/")[0].split("?")[0].split("#")[0].strip()
    return val


LEGAL_COMPANY_TERMS = [
    "cong ty co phan",
    "cong ty tnhh mtv",
    "cong ty tnhh 1 tv",
    "cong ty tnhh 2 tv",
    "cong ty tnhh hai thanh vien",
    "cong ty tnhh",
    "cong ty hop danh",
    "doanh nghiep tu nhan",
    "tong cong ty",
    "tap doan",
    "chi nhanh",
    "van phong dai dien",
    "co phan",
    "tnhh mtv",
    "tnhh",
    "co., ltd",
    "co. ltd",
    "co ltd",
    "ltd",
    "jsc",
    "corp",
    "corporation",
    "group",
    "holdings",
    "enterprise",
    "viet nam",
    "vietnam",
    "vn",
]


def normalize_company_name(name: Optional[str]) -> str:
    """
    Chuẩn hóa tên công ty phục vụ so khớp độ tương đồng:
    - Bỏ dấu tiếng Việt, chuyển chữ thường
    - Loại bỏ ký tự đặc biệt
    - Loại bỏ các tiền tố / hậu tố pháp lý phổ biến
    """
    if not name:
        return ""
    s = normalize_text(name)
    s = re.sub(r"[\.,\-_/\\()&@#$!*]", " ", s)
    s = " ".join(s.split())
    for term in sorted(LEGAL_COMPANY_TERMS, key=len, reverse=True):
        term_norm = normalize_text(term)
        pattern = r"\b" + re.escape(term_norm) + r"\b"
        s = re.sub(pattern, " ", s)
    return " ".join(s.split())


def calculate_company_similarity(name1: Optional[str], name2: Optional[str]) -> float:
    """
    Tính độ tương đồng tên công ty giữa 2 chuỗi (từ 0.0 đến 1.0).
    Sử dụng SequenceMatcher sau khi đã chuẩn hóa bỏ tiền tố/hậu tố pháp lý.
    """
    from difflib import SequenceMatcher

    if not name1 or not name2:
        return 0.0
    c1 = normalize_company_name(name1)
    c2 = normalize_company_name(name2)
    if not c1 or not c2:
        c1 = normalize_text(name1)
        c2 = normalize_text(name2)
    if not c1 or not c2:
        return 0.0
    if c1 == c2 and len(c1) >= 2:
        return 1.0
    return round(SequenceMatcher(None, c1, c2).ratio(), 3)

