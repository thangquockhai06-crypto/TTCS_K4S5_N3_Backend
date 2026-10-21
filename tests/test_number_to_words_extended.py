"""Kiểm thử mở rộng các trường hợp biên của hàm đọc số tiền thành chữ."""
from app.core.number_to_words import number_to_words_vi

def test_number_zero():
    assert "Không đồng chẵn" in number_to_words_vi(0)

def test_large_amounts():
    res = number_to_words_vi(1500000000)
    assert "Một tỷ" in res
    assert "đồng chẵn" in res

def test_negative_amount_returns_default():
    assert "Không đồng chẵn" in number_to_words_vi(-500)
