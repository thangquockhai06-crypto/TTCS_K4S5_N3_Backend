"""
Tiện ích chuyển đổi số tiền (VND) thành chữ tiếng Việt chuẩn xác (S7-05).
Phục vụ xuất file PDF báo giá và hợp đồng kinh tế theo quy chuẩn kế toán Việt Nam.
"""

UNIT_NAMES = ["", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ"]
DIGIT_NAMES = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _read_triple(triplet: int, show_zero_hundred: bool = False) -> str:
    hundred = triplet // 100
    ten = (triplet % 100) // 10
    unit = triplet % 10

    if triplet == 0 and not show_zero_hundred:
        return ""

    words = []
    if hundred > 0 or show_zero_hundred:
        words.append(DIGIT_NAMES[hundred] + " trăm")

    if ten > 1:
        words.append(DIGIT_NAMES[ten] + " mươi")
        if unit == 1:
            words.append("mốt")
        elif unit == 4:
            words.append("tư")
        elif unit == 5:
            words.append("lăm")
        elif unit > 0:
            words.append(DIGIT_NAMES[unit])
    elif ten == 1:
        words.append("mười")
        if unit == 5:
            words.append("lăm")
        elif unit > 0:
            words.append(DIGIT_NAMES[unit])
    elif ten == 0:
        if (hundred > 0 or show_zero_hundred) and unit > 0:
            words.append("lẻ " + DIGIT_NAMES[unit])
        elif unit > 0:
            words.append(DIGIT_NAMES[unit])

    return " ".join(words)


def convert_number_to_vietnamese_words(amount: float) -> str:
    """
    Chuyển số tiền VND thành chuỗi chữ tiếng Việt hoàn chỉnh.
    Ví dụ:
      - 150000000 -> "Một trăm năm mươi triệu đồng chẵn."
      - 3600000   -> "Ba triệu sáu trăm nghìn đồng chẵn."
      - 0         -> "Không đồng chẵn."
    """
    amount_int = int(round(amount))
    if amount_int <= 0:
        return "Không đồng chẵn."

    triplets = []
    temp = amount_int
    while temp > 0:
        triplets.append(temp % 1000)
        temp //= 1000

    result_parts = []
    for i, trip in enumerate(triplets):
        if trip > 0:
            trip_str = _read_triple(trip, show_zero_hundred=(i < len(triplets) - 1))
            unit = UNIT_NAMES[i]
            if unit:
                result_parts.append(f"{trip_str} {unit}")
            else:
                result_parts.append(trip_str)

    result_parts.reverse()
    full_sentence = " ".join([p for p in result_parts if p.strip()]) + " đồng chẵn."
    full_sentence = " ".join(full_sentence.split())
    # Capitalize the first letter
    return full_sentence[0].upper() + full_sentence[1:]
