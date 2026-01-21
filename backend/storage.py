import json
import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

try:
    import psycopg2
    from psycopg2 import pool
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None

try:
    from backend.data import DATA
except ImportError:
    from data import DATA

class DataStorage:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.errors_path = os.path.join(self.base_dir, "data", "detected_errors.json")
        self.db_path = os.path.join(self.base_dir, "data", "stats.db")
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.countries_map = {c["name"]: c for c in DATA["COUNTRIES"]}
        self.data = []
        self.stats = {} # Cache for map stats
        self.global_top_errors = []
        
        # Database Configuration
        self.db_url = os.getenv("DATABASE_URL")
        self.use_postgres = bool(self.db_url and psycopg2)
        self.pg_pool = None
        
        if self.use_postgres:
            print(f"Using PostgreSQL database.")
            try:
                # Initialize Connection Pool
                self.pg_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=20, # Render/Supabase free tier limits usually 20-60
                    dsn=self.db_url
                )
                print("PostgreSQL Connection Pool initialized.")
            except Exception as e:
                print(f"Error initializing connection pool: {e}")
                self.use_postgres = False
        else:
            print(f"Using SQLite database at {self.db_path}")

        self._init_db()
        self.load_data()

    @contextmanager
    def get_connection(self):
        """Context manager for database connection."""
        conn = None
        try:
            if self.use_postgres and self.pg_pool:
                conn = self.pg_pool.getconn()
                yield conn
            else:
                conn = sqlite3.connect(self.db_path)
                yield conn
        finally:
            if conn:
                if self.use_postgres and self.pg_pool:
                    self.pg_pool.putconn(conn)
                else:
                    conn.close()

    def _init_db(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if self.use_postgres:
                # PostgreSQL Schema
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS error_events (
                        id SERIAL PRIMARY KEY,
                        country_code TEXT,
                        country_name TEXT,
                        word TEXT,
                        suggestion TEXT,
                        timestamp TIMESTAMP,
                        context TEXT,
                        title TEXT
                    )
                ''')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON error_events(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_country ON error_events(country_code)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_word ON error_events(word)')
            else:
                # SQLite Schema
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS error_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        country_code TEXT,
                        country_name TEXT,
                        word TEXT,
                        suggestion TEXT,
                        timestamp TEXT,
                        context TEXT,
                        title TEXT
                    )
                ''')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON error_events(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_country ON error_events(country_code)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_word ON error_events(word)')
            
            conn.commit()

    def load_data(self):
        """Load data from JSON and sync to DB if needed."""
        # 1. Load Raw JSON (Still useful for simple iteration/fallback)
        if os.path.exists(self.errors_path):
            try:
                with open(self.errors_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"Error loading data: {e}")
                self.data = []
        else:
            self.data = []

        # 2. Sync DB
        self._sync_db()

        # 3. Warm up cache
        self._refresh_stats_cache()

    def _sync_db(self):
        """Sync DB with JSON data if DB is empty."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM error_events')
            count = cursor.fetchone()[0]
            
            # Only import if DB is empty to avoid duplicates on restart
            if count == 0 and self.data:
                print("Syncing Database with JSON data...")
                
                rows = []
                for article in self.data:
                    c_name = article.get("country", "Unknown")
                    meta = self.countries_map.get(c_name)
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
                
                if rows:
                    if self.use_postgres:
                        # PostgreSQL batch insert
                        args_str = ','.join(cursor.mogrify("(%s,%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in rows)
                        cursor.execute("INSERT INTO error_events (country_code, country_name, word, suggestion, timestamp, context, title) VALUES " + args_str)
                    else:
                        # SQLite batch insert
                        cursor.executemany('''
                            INSERT INTO error_events (country_code, country_name, word, suggestion, timestamp, context, title)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', rows)
                
                conn.commit()
                print(f"Imported {len(rows)} error events to Database.")

    def _refresh_stats_cache(self):
        """Compute aggregated stats from DB."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Global Top Errors
            cursor.execute('''
                SELECT word, COUNT(*) as cnt 
                FROM error_events 
                GROUP BY word 
                ORDER BY cnt DESC 
                LIMIT 20
            ''')
            self.global_top_errors = [{"word": row[0], "count": row[1]} for row in cursor.fetchall()]
            
            # Country Stats
            self.stats = {}
            
            # Get totals per country
            cursor.execute('''
                SELECT country_code, country_name, COUNT(*) as total
                FROM error_events
                GROUP BY country_code, country_name
            ''')
            country_totals = cursor.fetchall()
            
            for row in country_totals:
                # Handle tuple access differences if any (both return tuples by default)
                code, name, total = row[0], row[1], row[2]
                
                if not code or code == 'UNK': continue
                
                meta = self.countries_map.get(name)
                if not meta: continue
                
                # Get top errors for this country
                ph = '%s' if self.use_postgres else '?'
                cursor.execute(f'''
                    SELECT word, COUNT(*) as cnt
                    FROM error_events
                    WHERE country_code = {ph}
                    GROUP BY word
                    ORDER BY cnt DESC
                    LIMIT 5
                ''', (code,))
                top_errors = [{"word": r[0], "count": r[1]} for r in cursor.fetchall()]
                
                self.stats[code] = {
                    "name": name,
                    "code": code,
                    "total": total,
                    "errors": total,
                    "lat": meta["lat"],
                    "lng": meta["lng"],
                    "region": meta["region"],
                    "top_errors": top_errors
                }

    def get_stats(self):
        return self.stats

    def get_top_errors(self, limit=10):
        return self.global_top_errors[:limit]

    def get_error_trends(self, hours=24):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if self.use_postgres:
                query = f'''
                    SELECT word, COUNT(*) as cnt
                    FROM error_events
                    WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
                    GROUP BY word
                    ORDER BY cnt DESC
                    LIMIT 10
                '''
            else:
                query = f'''
                    SELECT word, COUNT(*) as cnt
                    FROM error_events
                    WHERE timestamp >= datetime('now', '-{hours} hours')
                    GROUP BY word
                    ORDER BY cnt DESC
                    LIMIT 10
                '''
                
            cursor.execute(query)
            trends = [{"word": row[0], "count": row[1]} for row in cursor.fetchall()]
            return trends

    def get_error_curve(self, hours=24):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if self.use_postgres:
                query = f'''
                    SELECT date_trunc('hour', timestamp) as hour_bucket, COUNT(*) as cnt
                    FROM error_events
                    WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
                    GROUP BY hour_bucket
                    ORDER BY hour_bucket ASC
                '''
            else:
                query = f'''
                    SELECT strftime('%Y-%m-%dT%H:00:00', timestamp) as hour_bucket, COUNT(*) as cnt
                    FROM error_events
                    WHERE timestamp >= datetime('now', '-{hours} hours')
                    GROUP BY hour_bucket
                    ORDER BY hour_bucket ASC
                '''
                
            cursor.execute(query)
            # Format timestamps consistently if needed, but ISO format usually works
            curve = [{"time": str(row[0]), "count": row[1]} for row in cursor.fetchall()]
            return curve

    def get_raw_data(self):
        return self.data

    def get_global_summary(self):
        total_errors = sum(s["total"] for s in self.stats.values())
        total_countries = len(self.stats)
        return {
            "total_errors": total_errors,
            "active_countries": total_countries,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d")
        }
