import argparse
import sqlite3
from pathlib import Path


def apply_sql(sql_path: Path, db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        sql = sql_path.read_text()
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a SQL schema to data.db")
    parser.add_argument("--sql", required=True, help="Path to SQL schema file")
    parser.add_argument(
        "--db",
        default=None,
        help="Optional path to SQLite database (default: data.db)",
    )
    args = parser.parse_args()

    sql_path = Path(args.sql).expanduser().resolve()
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    if args.db:
        db_path = Path(args.db).expanduser().resolve()
    else:
        db_path = Path(__file__).resolve().parents[1] / "data.db"

    apply_sql(sql_path, db_path)


if __name__ == "__main__":
    main()
