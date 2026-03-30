from pathlib import Path

import mysql.connector

from job_tracker.config import Config


def split_sql_statements(sql_text: str) -> list[str]:
    statements = []
    current = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current).strip().rstrip(";"))
            current = []
    if current:
        statements.append("\n".join(current).strip().rstrip(";"))
    return statements


def main():
    connection = mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
    )
    cursor = connection.cursor()
    try:
        schema_sql = Path("schema.sql").read_text(encoding="utf-8")
        for statement in split_sql_statements(schema_sql):
            cursor.execute(statement)
        connection.commit()
        print(f"Database '{Config.DB_NAME}' configured successfully.")
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
