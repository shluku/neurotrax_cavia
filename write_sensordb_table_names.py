from pathlib import Path

import pandas as pd

from main import connect_sensordata_db


OUT_PATH = Path("output/analysis_candidates/phase2_sql_fieldwork_samples/sensordb_table_names.csv")


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = connect_sensordata_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DATABASE()")
        database_name = str(cur.fetchone()[0])
        cur.execute("SHOW TABLES")
        table_names = sorted(str(row[0]) for row in cur.fetchall())
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()

    pd.DataFrame(
        [{"database_name": database_name, "table_name": table_name} for table_name in table_names]
    ).to_csv(OUT_PATH, index=False)

    print(f"database_name={database_name}")
    print(f"total_tables={len(table_names)}")
    print("table_names:")
    for table_name in table_names:
        print(f"- {table_name}")
    print(f"output_file={OUT_PATH}")


if __name__ == "__main__":
    main()
