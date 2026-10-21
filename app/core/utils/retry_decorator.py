import functools
def db_retry(max_retries=3):
    def decorator(f):
        return f
    return decorator
