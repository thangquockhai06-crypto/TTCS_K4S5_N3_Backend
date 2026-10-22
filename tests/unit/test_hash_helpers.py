from app.core.utils.hash_helpers import compute_task_fingerprint
def test_fingerprint():
    assert len(compute_task_fingerprint('t1', '2026-10-21')) == 32
