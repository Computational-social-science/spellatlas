import os
import json
import psycopg2
import sys
from datetime import datetime

# Add project root directory to path to allow imports like 'from backend.data import DATA'
# File is at: backend/scripts/migrate_json_to_pg.py
# Root is at: ../../
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def migrate():
    # Path to JSON file (relative to project root)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    json_path = os.path.join(base_dir, "data", "detected_errors.json")
    
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return

    print(f"Reading data from {json_path}...")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    if not data:
        print("No data found in JSON.")
        return

    # Database connection
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL environment variable not set.")
        # Fallback for local testing if running outside docker but with port exposed
        # db_url = "postgresql://postgres:password@localhost:5432/spellatlas"
        return

    print(f"Connecting to database...")
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
    except Exception as e:
        print(f"Database connection failed: {e}")
        return

    # Prepare data
    rows = []
    print(f"Processing {len(data)} articles...")
    
    # Simple mapping for country codes (simplified version of backend/storage.py logic)
    # Ideally we should fetch this from DB or use the same map, but for migration script we keep it simple or try to import
    from backend.data import DATA
    countries_map = {c["name"]: c for c in DATA["COUNTRIES"]}

    for article in data:
        c_name = article.get("country", "Unknown")
        meta = countries_map.get(c_name)
        c_code = meta["code"] if meta else "UNK"
        ts = article.get("scraped_at") or article.get("date") or datetime.utcnow().isoformat()
        title = article.get("title", "")
        
        for err in article.get("errors", []):
            rows.append((
                c_code,
                c_name,
                err.get("word", "").lower(),
                err.get("suggestion", ""),
                ts,
                err.get("context", ""),
                title
            ))

    if not rows:
        print("No error events found to migrate.")
        return

    print(f"Inserting {len(rows)} error events...")
    
    try:
        # Batch insert
        args_str = ','.join(cursor.mogrify("(%s,%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in rows)
        cursor.execute("INSERT INTO error_events (country_code, country_name, word, suggestion, timestamp, context, title) VALUES " + args_str)
        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
