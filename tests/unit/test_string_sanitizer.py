from app.core.utils.string_sanitizer import sanitize_title
def test_sanitize():
    assert sanitize_title('  test  ') == 'test'
