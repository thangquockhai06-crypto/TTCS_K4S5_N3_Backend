from app.core.utils.system_clock import current_utc_time
def test_clock():
    assert current_utc_time() is not None
