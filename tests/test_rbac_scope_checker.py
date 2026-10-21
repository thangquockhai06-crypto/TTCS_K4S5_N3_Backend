"""Kiểm thử cơ chế kiểm tra phân quyền dữ liệu Data Scope."""
from app.core.scope import check_data_scope_access

def test_admin_has_global_access():
    user = {"role": "ADMIN", "data_scope": "GLOBAL", "id": 1}
    assert check_data_scope_access(user, record_owner_id=999) is True

def test_sales_cannot_access_other_record():
    user = {"role": "SALES", "data_scope": "PERSONAL", "id": 10}
    assert check_data_scope_access(user, record_owner_id=10) is True
    assert check_data_scope_access(user, record_owner_id=99) is False
