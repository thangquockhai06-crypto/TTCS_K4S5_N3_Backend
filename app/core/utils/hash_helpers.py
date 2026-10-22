import hashlib
def compute_task_fingerprint(task_id: str, due_str: str) -> str:
    return hashlib.md5(f'{task_id}:{due_str}'.encode()).hexdigest()
