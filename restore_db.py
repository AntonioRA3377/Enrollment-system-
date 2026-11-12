import os
import sys
import glob
import json
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def run_restore(backup_file=None):
    if not backup_file:
        files = sorted(glob.glob('backups/*.json'))
        if not files:
            print("No JSON backup files found in backups/. Run python3 backup_db.py first.")
            return
        backup_file = files[-1]

    with open(backup_file, 'r') as f:
        snapshot = json.load(f)

    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'enrollment_system_db'),
        port=int(os.getenv('DB_PORT', 3306))
    )
    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS=0")

    for table, rows in snapshot.get("tables", {}).items():
        cursor.execute(f"TRUNCATE TABLE `{table}`")
        if rows:
            columns = list(rows[0].keys())
            col_str = ", ".join(f"`{c}`" for c in columns)
            placeholders = ", ".join(["%s"] * len(columns))
            sql = f"INSERT INTO `{table}` ({col_str}) VALUES ({placeholders})"
            for row in rows:
                cursor.execute(sql, [row[c] for c in columns])

    cursor.execute("SET FOREIGN_KEY_CHECKS=1")
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Database restored cleanly from: {backup_file}")


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else None
    run_restore(target)
