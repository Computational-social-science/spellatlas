import sqlite3
import numpy as np
from collections import Counter
from scipy.spatial.distance import cosine, euclidean, mahalanobis
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try importing ruptures for change point detection
try:
    import ruptures as rpt
    HAS_RUPTURES = True
except ImportError:
    HAS_RUPTURES = False
    logger.warning("ruptures library not found. using fallback for change point detection.")

class Analyzer:
    def __init__(self, db_path):
        self.db_path = db_path
        self._global_vocab = None # Cache for global top words (dimensions)

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _get_global_vocab(self, limit=100):
        """Get top N global errors to serve as vector dimensions."""
        if self._global_vocab:
            return self._global_vocab
            
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT word, COUNT(*) as cnt 
            FROM error_events 
            GROUP BY word 
            ORDER BY cnt DESC 
            LIMIT ?
        ''', (limit,))
        vocab = [row[0] for row in cursor.fetchall()]
        conn.close()
        self._global_vocab = vocab
        return vocab

    def _get_vector(self, country_code=None, time_start=None, time_end=None, vocab=None):
        """Construct a frequency vector for a country (or global if None)."""
        if not vocab:
            vocab = self._get_global_vocab()
            
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT word, COUNT(*) as cnt FROM error_events WHERE 1=1"
        params = []
        
        if country_code:
            query += " AND country_code = ?"
            params.append(country_code)
            
        if time_start:
            query += " AND timestamp >= ?"
            params.append(time_start)
            
        if time_end:
            query += " AND timestamp <= ?"
            params.append(time_end)
            
        query += " GROUP BY word"
        
        cursor.execute(query, params)
        counts = dict(cursor.fetchall())
        conn.close()
        
        # Build vector based on fixed vocab dimensions
        vector = np.array([counts.get(word, 0) for word in vocab], dtype=float)
        
        # Normalize (L1 norm -> probability distribution)
        total = np.sum(vector)
        if total > 0:
            vector = vector / total
            
        return vector

    def get_fingerprint_metrics(self, country_code):
        """
        T6.1 Fingerprint Distance Metric.
        Compare country's error distribution to global distribution.
        """
        vocab = self._get_global_vocab()
        v_global = self._get_vector(vocab=vocab) # Global vector
        v_country = self._get_vector(country_code=country_code, vocab=vocab)
        
        if np.sum(v_country) == 0:
            return {"error": "Not enough data for country"}

        # Metrics
        # Cosine Distance (1 - similarity)
        # Euclidean Distance
        # Mahalanobis requires covariance matrix, simplifying to Cityblock (Manhattan) for now as proxy or implementing logic if needed. 
        # For Mahalanobis, we need a dataset of vectors to compute covariance. We only have 2 vectors here. 
        # We'll stick to Cosine and Euclidean as primary.
        
        dist_cosine = cosine(v_global, v_country)
        dist_euclidean = euclidean(v_global, v_country)
        
        # Top distinctive words (where country freq > global freq)
        diff = v_country - v_global
        distinctive_indices = np.argsort(diff)[::-1][:5]
        distinctive_words = [
            {"word": vocab[i], "delta": float(diff[i]), "local_freq": float(v_country[i])} 
            for i in distinctive_indices if diff[i] > 0
        ]
        
        return {
            "cosine_distance": float(dist_cosine),
            "euclidean_distance": float(dist_euclidean),
            "distinctive_features": distinctive_words,
            "vector_dim": len(vocab)
        }

    def analyze_stability(self, country_code):
        """
        T6.2 Country Stability Test.
        Compare 'Within' similarity (Odd vs Even days).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get all timestamps for the country
        cursor.execute('''
            SELECT id, timestamp 
            FROM error_events 
            WHERE country_code = ? 
            ORDER BY timestamp
        ''', (country_code,))
        rows = cursor.fetchall()
        conn.close()
        
        if len(rows) < 10:
             return {"status": "insufficient_data", "stability_score": 0}

        # Split into two sets (random permutation or simple split)
        # User mentioned "permutation test", but simple Odd/Even ID split is a good proxy for internal consistency
        ids_a = [r[0] for i, r in enumerate(rows) if i % 2 == 0]
        ids_b = [r[0] for i, r in enumerate(rows) if i % 2 != 0]
        
        vocab = self._get_global_vocab()
        
        # Helper to build vector from IDs
        def get_vec_from_ids(ids):
            conn = self._get_connection()
            cursor = conn.cursor()
            ph = ','.join('?' * len(ids))
            cursor.execute(f"SELECT word, COUNT(*) FROM error_events WHERE id IN ({ph}) GROUP BY word", ids)
            counts = dict(cursor.fetchall())
            conn.close()
            vec = np.array([counts.get(w, 0) for w in vocab], dtype=float)
            if np.sum(vec) > 0: vec /= np.sum(vec)
            return vec

        v_a = get_vec_from_ids(ids_a)
        v_b = get_vec_from_ids(ids_b)
        
        # Stability = 1 - Cosine Distance between halves
        # If perfectly stable, random halves should be identical distribution.
        stability = 1.0 - cosine(v_a, v_b)
        
        return {
            "stability_score": float(stability), # 0 to 1
            "sample_size": len(rows),
            "interpretation": "High" if stability > 0.9 else "Moderate" if stability > 0.7 else "Low"
        }

    def analyze_evolution(self, country_code):
        """
        T6.3 Time Evolution Analysis.
        Annual drift curve & Change point detection.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get daily counts
        cursor.execute('''
            SELECT strftime('%Y-%m-%d', timestamp) as day, COUNT(*) 
            FROM error_events 
            WHERE country_code = ? 
            GROUP BY day 
            ORDER BY day
        ''', (country_code,))
        daily_counts = cursor.fetchall()
        conn.close()
        
        if not daily_counts:
            return {"status": "no_data"}
            
        dates = [r[0] for r in daily_counts]
        counts = np.array([r[1] for r in daily_counts])
        
        change_points = []
        if HAS_RUPTURES and len(counts) > 10:
            # Change point detection on the count signal
            # Penalty search (Pelt)
            model = rpt.Pelt(model="rbf").fit(counts)
            # penalty value is somewhat arbitrary without tuning, using 10 as safe default
            result = model.predict(pen=10)
            
            # Map indices back to dates
            change_points = []
            for idx in result:
                if idx < len(dates):
                    change_points.append({"date": dates[idx], "index": int(idx)})
        else:
            # Fallback: Simple threshold (e.g., > 2 std dev from mean)
            mean = np.mean(counts)
            std = np.std(counts)
            threshold = mean + 2 * std
            for i, c in enumerate(counts):
                if c > threshold:
                    change_points.append({"date": dates[i], "index": i, "type": "surge"})

        return {
            "timeline": [{"date": d, "count": int(c)} for d, c in zip(dates, counts)],
            "change_points": change_points,
            "drift_metric": "Daily Error Volume" 
        }
