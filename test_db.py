import psycopg2
import os

try:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="EduVista@7291618",
        host="db.wztqimzxyfsedozseqxt.supabase.co",
        port="5432"
    )
    print("✅ Connection successful!")
    conn.close()
except Exception as e:
    print("❌ Connection failed:", e)
