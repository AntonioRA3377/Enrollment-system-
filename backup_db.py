import os
import json
from datetime import datetime, date
from decimal import Decimal
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def json_serializer(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def run_backup():
    os.makedirs('backups', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    db_name = os.getenv('DB_NAME', 'enrollment_system_db')

    conn = mysql.connector.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=db_name,
        port=int(os.getenv('DB_PORT', 3306))
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SHOW TABLES")
    tables = [list(row.values())[0] for row in cursor.fetchall()]

    snapshot = {"database": db_name, "created_at": timestamp, "tables": {}}
    sql_lines = [f"-- Backup of {db_name} ({timestamp})", "SET FOREIGN_KEY_CHECKS=0;
"]

    for table in tables:
        cursor.execute(f"SELECT * FROM `{table}`")
        rows = cursor.fetchall()
        snapshot["tables"][table] = rows

        sql_lines.append(f"TRUNCATE TABLE `{table}`;")
        for r in rows:
            cols = ", ".join(f"`{k}`" for k in r.keys())
            vals = []
            for v in r.values():
                if v is None:
                    vals.append("NULL")
                elif isinstance(v, (int, float, Decimal)):
                    vals.append(str(v))
                else:
                    escaped = str(v).replace("'", "''")
                    vals.append(f"'{escaped}'")
            sql_lines.append(f"INSERT INTO `{table}` ({cols}) VALUES ({', '.join(vals)});")
        sql_lines.append("")

    sql_lines.append("SET FOREIGN_KEY_CHECKS=1;")

    json_path = f"backups/{db_name}_{timestamp}.json"
    sql_path = f"backups/{db_name}_{timestamp}.sql"

    with open(json_path, 'w') as jf:
        json.dump(snapshot, jf, indent=2, default=json_serializer)
    with open(sql_path, 'w') as sf:
        sf.write("\n".join(sql_lines))

    cursor.close()
    conn.close()
    print(f"Backup completed successfully:\n  - {json_path}\n  - {sql_path}")


if __name__ == '__main__':
    run_backup()
