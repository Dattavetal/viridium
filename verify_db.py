import sqlite3
import pandas as pd

# 1. List all tables
conn = sqlite3.connect("pfas_lens.db")
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tables in database:", [row[0] for row in cur.fetchall()])

# 2. Preview first 5 rows from each table
df_s = pd.read_sql("SELECT * FROM substance LIMIT 5", conn)
df_a = pd.read_sql("SELECT * FROM alternative LIMIT 5", conn)

print("\nFirst 5 rows of 'substance':")
print(df_s)

print("\nFirst 5 rows of 'alternative':")
print(df_a)

conn.close()
