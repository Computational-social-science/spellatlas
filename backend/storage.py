import json
import os
import sqlite3
from datetime import datetime
from collections import defaultdict, Counter
try:
    from backend.data import DATA
except ImportError:
    from data import DATA

class DataStorage:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.errors_path = os.path.join(self.base_dir, "data", "detected_errors.json")
        self.db_path = os.path.join(self.base_dir, "data", "stats.db")
        self.countries_map = {c["name"]: c for c in DATA["COUNTRIES"]}
        self.data = []
        self.stats = {} # Cache for map stats
        self.global_top_errors = []
        
        self._init_db()
        self.load_data()

    def _init_db(self):
        """Initialize SQLite database and tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
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
        conn.close()

    def load_data(self):
        """Load data from JSON and sync to SQLite if needed."""
        # 1. Load Raw JSON (Required for WebSocket replay)
        if os.path.exists(self.errors_path):
            try:
                with open(self.errors_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"Error loading data: {e}")
                self.data = []
        else:
            self.data = []

        # 2. Sync SQLite
        self._sync_db()

        # 3. Warm up cache
        self._refresh_stats_cache()

    def _sync_db(self):
        """Check if DB needs update from JSON."""
        # Simple logic: If JSON is newer than DB file, or DB is empty -> Reload
        # For robustness in this demo, we'll reload if DB is empty or explicitly requested.
        # In production, check mtimes.
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM error_events')
        count = cursor.fetchone()[0]
        
        json_mtime = os.path.getmtime(self.errors_path) if os.path.exists(self.errors_path) else 0
        db_mtime = os.path.getmtime(self.db_path) if os.path.exists(self.db_path) else 0
        
        # Reload if DB empty or JSON is significantly newer (buffer 1s)
        if count == 0 or (json_mtime > db_mtime + 1):
            print("Syncing SQLite with JSON data...")
            cursor.execute('DELETE FROM error_events')
            
            rows = []
            for article in self.data:
                c_name = article.get("country", "Unknown")
                meta = self.countries_map.get(c_name)
                c_code = meta["code"] if meta else "UNK"
                
                # Use scraped_at or date or now
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
                cursor.executemany('''
                    INSERT INTO error_events (country_code, country_name, word, suggestion, timestamp, context, title)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', rows)
            
            conn.commit()
            print(f"Imported {len(rows)} error events to SQLite.")
            
        conn.close()

    def _refresh_stats_cache(self):
        """Compute aggregated stats from SQLite."""
        conn = sqlite3.connect(self.db_path)
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
            GROUP BY country_code
        ''')
        country_totals = cursor.fetchall()
        
        for code, name, total in country_totals:
            if not code or code == 'UNK': continue
            
            # Get meta
            meta = self.countries_map.get(name)
            if not meta: continue # Should map by code ideally, but we stored name too
            
            # Get top errors for this country
            cursor.execute('''
                SELECT word, COUNT(*) as cnt
                FROM error_events
                WHERE country_code = ?
                GROUP BY word
                ORDER BY cnt DESC
                LIMIT 5
            ''', (code,))
            top_errors = [{"word": r[0], "count": r[1]} for r in cursor.fetchall()]
            
            self.stats[code] = {
                "name": name,
                "code": code,
                "total": total,
                "errors": total, # Assuming 1 event = 1 error
                "lat": meta["lat"],
                "lng": meta["lng"],
                "region": meta["region"],
                "top_errors": top_errors
            }
            
        conn.close()

    def get_stats(self):
        """Return aggregated stats."""
        return self.stats

    def get_top_errors(self, limit=10):
        """Return global top errors."""
        return self.global_top_errors[:limit]

    def get_error_trends(self, hours=24):
        """Get error trends for the last N hours."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # SQLite 'now' is in UTC. Ensure timestamps are compatible.
        # Our ts is ISO string. SQLite string comparison works for ISO dates.
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
        conn.close()
        return trends

    def get_error_curve(self, hours=24):
        """Get hourly error volume for the last N hours."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Aggregate by hour
        # Use strftime to truncate timestamp to hour
        query = f'''
            SELECT strftime('%Y-%m-%dT%H:00:00', timestamp) as hour_bucket, COUNT(*) as cnt
            FROM error_events
            WHERE timestamp >= datetime('now', '-{hours} hours')
            GROUP BY hour_bucket
            ORDER BY hour_bucket ASC
        '''
        cursor.execute(query)
        
        # Format for frontend: [{"time": "2026-01-20T10:00:00", "count": 5}, ...]
        curve = [{"time": row[0], "count": row[1]} for row in cursor.fetchall()]
        conn.close()
        return curve

    def get_raw_data(self):
        """Return raw article data."""
        return self.data

    def get_global_summary(self):
        """Return global summary."""
        total_errors = sum(s["total"] for s in self.stats.values())
        total_countries = len(self.stats)
        return {
            "total_errors": total_errors,
            "active_countries": total_countries,
            "timestamp": "2026-01-20" # Placeholder or file mtime
        }
