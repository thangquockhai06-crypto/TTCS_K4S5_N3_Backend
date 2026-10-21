import time

def benchmark():
    start = time.perf_counter()
    # Gia lap quet 10,000 tasks
    dummy_tasks = [{"id": i, "status": "pending", "reminded": []} for i in range(10000)]
    scanned = [t for t in dummy_tasks if t["status"] == "pending"]
    elapsed = time.perf_counter() - start
    print(f"[BENCHMARK] Quet {len(scanned)} tasks mat {elapsed*1000:.2f}ms")

if __name__ == "__main__":
    benchmark()
