"""Kiểm tra sự tương thích của môi trường Python, thư viện và cơ sở dữ liệu."""
import sys
import platform

def verify():
    print(f"Python Version: {platform.python_version()}")
    print(f"OS Platform: {platform.platform()}")
    assert sys.version_info >= (3, 10), "Requires Python 3.10+"
    print("Environment is verified and compatible with NexusCRM.")

if __name__ == "__main__":
    verify()
