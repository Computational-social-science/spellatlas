import asyncio
import random
import json
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import os
try:
    from backend.storage import DataStorage
    from backend.analysis import Analyzer
except ImportError:
    from storage import DataStorage
    from analysis import Analyzer

app = FastAPI()

# Initialize Storage
storage = DataStorage()
# Initialize Analyzer
analyzer = Analyzer(storage.db_path)

origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "system": "SpellAtlas Backend V1.0",
        "data_loaded": len(storage.get_raw_data())
    }

@app.get("/api/stats")
def get_global_stats():
    """Get global summary statistics."""
    return storage.get_global_summary()

@app.get("/api/map-data")
def get_map_data():
    """Get country-level statistics for map visualization."""
    return storage.get_stats()

@app.get("/api/errors")
def get_errors(limit: int = 100):
    """Get raw error list (flat)."""
    raw = storage.get_raw_data()
    flat_errors = []
    for article in raw:
        country = article.get("country", "Unknown")
        title = article.get("title", "")
        for err in article.get("errors", []):
            flat_errors.append({
                "country": country,
                "title": title,
                **err
            })
    return flat_errors[:limit]

@app.get("/api/stats/top-errors")
def get_top_errors(limit: int = 10):
    """Get global top spelling errors."""
    return storage.get_top_errors(limit)

@app.get("/api/stats/country/{code}")
def get_country_stats(code: str):
    """Get statistics for a specific country."""
    stats = storage.get_stats()
    return stats.get(code.upper(), {"error": "Country not found"})

@app.get("/api/stats/trends")
def get_trends(hours: int = 24):
    """Get error trends for the last N hours."""
    return storage.get_error_trends(hours)

@app.get("/api/stats/curve")
def get_curve(hours: int = 24):
    """Get hourly error volume for the last N hours."""
    return storage.get_error_curve(hours)

@app.get("/api/analysis/{code}/fingerprint")
def get_fingerprint(code: str):
    """Get fingerprint analysis for a country."""
    return analyzer.get_fingerprint_metrics(code.upper())

@app.get("/api/analysis/{code}/stability")
def get_stability(code: str):
    """Get stability analysis for a country."""
    return analyzer.analyze_stability(code.upper())

@app.get("/api/analysis/{code}/evolution")
def get_evolution(code: str):
    """Get evolution analysis for a country."""
    return analyzer.analyze_evolution(code.upper())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Prepare replay queue
    raw_data = storage.get_raw_data()
    replay_queue = []
    for article in raw_data:
        country_name = article.get("country", "Unknown")
        title = article.get("title", "Unknown Title")
        
        # Look up country code
        country_info = storage.countries_map.get(country_name)
        country_code = country_info["code"] if country_info else "UNK"
        lat = country_info["lat"] if country_info else 0
        lng = country_info["lng"] if country_info else 0

        for err in article.get("errors", []):
            replay_queue.append({
                "type": "news_item",
                "country_name": country_name,
                "country_code": country_code,
                "coordinates": {"lat": lat, "lng": lng},
                "has_error": True,
                "title": title,
                "error_details": {
                    "word": err["word"],
                    "suggestion": err["suggestion"],
                    "context": err.get("context", "")
                }
            })
            
    # If no real data, fallback to heartbeat or empty
    if not replay_queue:
        # Send one keepalive
        await websocket.send_json({"type": "info", "message": "No errors in database."})
    
    try:
        idx = 0
        while True:
            if replay_queue:
                # Cycle through errors to simulate activity
                item = replay_queue[idx % len(replay_queue)]
                await websocket.send_json(item)
                idx += 1
                
                # Random delay 2s - 5s
                await asyncio.sleep(2.0 + random.random() * 3.0)
            else:
                # Idle heartbeat
                await asyncio.sleep(5)
                await websocket.send_json({"type": "heartbeat"})
                
    except asyncio.CancelledError:
        print("WS Connection cancelled")
    except Exception as e:
        print(f"WS Connection closed: {e}")
