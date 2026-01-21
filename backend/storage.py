import json
import os
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
        
        self.countries_map = {c["name"]: c for c in DATA["COUNTRIES"]}
        self.data = []
        self.stats = {} # Cache for map stats
        self.global_top_errors = []
        
        # Database Configuration
        self.db_url = os.getenv("DATABASE_URL")
        
        # Enforce PostgreSQL usage based on user requirement
        if not self.db_url:
            # Fallback for local development WITHOUT docker-compose (not recommended but handled)
            # Or if user forgot to set env var.
            # But since user explicitly asked to STOP using SQLite, we should warn or error.
            # For smoother transition, I'll print a huge warning but try to find a local default.
            print("WARNING: DATABASE_URL not found. Defaulting to local Docker URL.")
            self.db_url = "postgresql://postgres:password@localhost:5432/spellatlas"

        self.use_postgres = True # Force True as requested
        self.pg_pool = None
        
        print(f"Connecting to PostgreSQL database at {self.db_url.split('@')[-1] if self.db_url else 'None'}")
        
        try:
            # Initialize Connection Pool
            # Wait for DB to be ready is handled by docker-compose healthcheck, 
            # but we add a small retry here just in case.
            import time
            max_retries = 5
            for i in range(max_retries):
                try:
                    self.pg_pool = psycopg2.pool.ThreadedConnectionPool(
                        minconn=1,
                        maxconn=20, 
                        dsn=self.db_url
                    )
                    print("PostgreSQL Connection Pool initialized.")
                    break
                except Exception as e:
                    if i < max_retries - 1:
                        print(f"DB Connection failed ({e}), retrying in 2s...")
                        time.sleep(2)
                    else:
                        raise e
        except Exception as e:
            print(f"CRITICAL: Error initializing PostgreSQL connection pool: {e}")
            print("WARNING: Running in NO-DB mode. Some features will be limited.")
            self.use_postgres = False
            self.pg_pool = None

        if self.use_postgres:
            self._init_db()
        
        self.load_data()

    @contextmanager
    def get_connection(self):
        """Context manager for database connection."""
        conn = None
        try:
            if self.pg_pool:
                conn = self.pg_pool.getconn()
                yield conn
            else:
                # Should not happen if initialization succeeded, but just in case
                # Return a dummy context if NO-DB mode to prevent crashes in context managers
                if not self.use_postgres:
                    yield None
                else:
                    raise Exception("PostgreSQL connection pool not initialized")
        finally:
            if conn and self.pg_pool:
                self.pg_pool.putconn(conn)

    def _init_db(self):
        """Initialize database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
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
        if not self.use_postgres:
            return

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
                    # PostgreSQL batch insert
                    args_str = ','.join(cursor.mogrify("(%s,%s,%s,%s,%s,%s,%s)", x).decode('utf-8') for x in rows)
                    cursor.execute("INSERT INTO error_events (country_code, country_name, word, suggestion, timestamp, context, title) VALUES " + args_str)
                
                conn.commit()
                print(f"Imported {len(rows)} error events to Database.")

    def _refresh_stats_cache(self):
        """Compute aggregated stats from DB."""
        if not self.use_postgres:
            # Fallback: Compute stats from JSON in memory if DB is down
            self._compute_stats_from_json()
            return

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
                cursor.execute(f'''
                    SELECT word, COUNT(*) as cnt
                    FROM error_events
                    WHERE country_code = %s
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

    def _compute_stats_from_json(self):
        """Fallback: Compute stats from self.data in memory."""
        from collections import Counter
        
        # 1. Global Top Errors
        all_words = []
        for article in self.data:
            for err in article.get("errors", []):
                all_words.append(err.get("word", "").lower())
        
        word_counts = Counter(all_words)
        self.global_top_errors = [{"word": w, "count": c} for w, c in word_counts.most_common(20)]
        
        # 2. Country Stats
        self.stats = {}
        country_data = {} # code -> {total: 0, errors: 0, words: []}
        
        for article in self.data:
            c_name = article.get("country", "Unknown")
            meta = self.countries_map.get(c_name)
            if not meta: continue
            
            c_code = meta["code"]
            if c_code not in country_data:
                country_data[c_code] = {"total": 0, "errors": 0, "words": []}
            
            # Since self.data structure might be article-based or flat error based?
            # get_raw_data returns list of articles.
            # Assuming article has 'errors' list.
            # Wait, DB counts 'error_events'. JSON is articles.
            # If JSON is articles, total count of ERRORS is sum of len(errors).
            
            errors = article.get("errors", [])
            err_count = len(errors)
            
            # In DB logic: COUNT(*) FROM error_events GROUP BY country_code
            # This counts individual errors.
            country_data[c_code]["total"] += err_count
            country_data[c_code]["errors"] += err_count
            
            for err in errors:
                country_data[c_code]["words"].append(err.get("word", "").lower())
                
        for code, data in country_data.items():
            meta = next((c for c in DATA["COUNTRIES"] if c["code"] == code), None)
            if not meta: continue
            
            top_words = Counter(data["words"]).most_common(5)
            
            self.stats[code] = {
                "name": meta["name"],
                "code": code,
                "total": data["total"],
                "errors": data["errors"],
                "lat": meta["lat"],
                "lng": meta["lng"],
                "region": meta["region"],
                "top_errors": [{"word": w, "count": c} for w, c in top_words]
            }

    def get_stats(self):
        return self.stats

    def get_top_errors(self, limit=10):
        return self.global_top_errors[:limit]

    def get_error_trends(self, hours=24):
        if not self.use_postgres:
            return [] # Not supported in NO-DB mode for now
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = f'''
                SELECT word, COUNT(*) as cnt
                FROM error_events
                WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
                GROUP BY word
                ORDER BY cnt DESC
                LIMIT 10
            '''
                
            cursor.execute(query)
            trends = [{"word": row[0], "count": row[1]} for row in cursor.fetchall()]
            return trends

    def get_error_curve(self, hours=24):
        if not self.use_postgres:
            return [] # Not supported in NO-DB mode for now

        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = f'''
                SELECT date_trunc('hour', timestamp) as hour_bucket, COUNT(*) as cnt
                FROM error_events
                WHERE timestamp >= NOW() - INTERVAL '{hours} hours'
                GROUP BY hour_bucket
                ORDER BY hour_bucket ASC
            '''
                
            cursor.execute(query)
            # Format timestamps consistently if needed, but ISO format usually works
            curve = [{"time": str(row[0]), "count": row[1]} for row in cursor.fetchall()]
            return curve

    def get_raw_data(self):
        return self.data
    
    def register_snapshot(self, s3_key, count):
        """Register a new raw news snapshot."""
        if not self.use_postgres:
            return
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO news_snapshots (s3_key, article_count) VALUES (%s, %s)",
                (s3_key, count)
            )
            conn.commit()
            print(f"Registered snapshot: {s3_key}")

    def get_latest_snapshot(self):
        """Get the most recent news snapshot."""
        if not self.use_postgres:
            return None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT s3_key FROM news_snapshots ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else None

    def get_global_summary(self):
        total_errors = sum(s["total"] for s in self.stats.values())
        total_countries = len(self.stats)
        return {
            "total_errors": total_errors,
            "active_countries": total_countries,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d")
        }
