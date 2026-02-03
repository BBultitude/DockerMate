#!/usr/bin/env python3
"""
Fix migration state by dropping images table and resetting alembic version.
This allows the migration to run cleanly on container startup.
"""
import sqlite3

db_path = '/app/data/dockermate.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Drop images table if it exists
    print("Dropping images table...")
    cursor.execute("DROP TABLE IF EXISTS images")

    # Reset alembic version to before images migration
    print("Resetting alembic version to b2b56351569a...")
    cursor.execute("UPDATE alembic_version SET version_num = 'b2b56351569a'")

    conn.commit()
    print("✓ Database fixed - migrations will recreate images table on next startup")
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()
