"""Script kiểm tra tính toàn vẹn dữ liệu và khóa ngoại trong cơ sở dữ liệu."""
import sqlite3
import os

def check_integrity():
    db_path = "nexuscrm.db" if os.path.exists("nexuscrm.db") else "crm.db"
    if not os.path.exists(db_path):
        print("Database file does not exist, skipping check.")
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check")
    result = cursor.fetchone()[0]
    cursor.execute("PRAGMA foreign_key_check")
    fk_errors = cursor.fetchall()
    conn.close()
    
    print(f"Database Integrity: {result}")
    print(f"Foreign Key Violations: {len(fk_errors)}")

if __name__ == "__main__":
    check_integrity()
