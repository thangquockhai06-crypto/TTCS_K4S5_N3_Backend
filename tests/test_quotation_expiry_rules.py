"""Kiểm thử tự động đánh dấu báo giá hết hạn khi qua thời hạn hiệu lực."""
from datetime import datetime, timedelta

def test_is_quote_expired():
    def check_expired(valid_until: datetime) -> bool:
        return datetime.utcnow() > valid_until
        
    past_date = datetime.utcnow() - timedelta(days=2)
    future_date = datetime.utcnow() + timedelta(days=5)
    
    assert check_expired(past_date) is True
    assert check_expired(future_date) is False
