import asyncio
import random
import json
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import os
try:
    from backend.storage import DataStorage
    from backend.analysis import Analyzer
    from backend.simulator import Simulator
except ImportError:
    from storage import DataStorage
    from analysis import Analyzer
    from simulator import Simulator

app = FastAPI()

# Initialize Storage
storage = DataStorage()
# Initialize Analyzer
analyzer = Analyzer(storage.db_path)

# Enhanced CORS Configuration
# Defaults to "*" but explicitly allows common development and production origins
default_origins = [
    "http://localhost:5173", # Vite local dev
    "http://localhost:3000",
    "https://computational-social-science.github.io" # GitHub Pages
]

env_origins = os.getenv("ALLOWED_ORIGINS", "")
if env_origins:
    origins = env_origins.split(",") + default_origins
else:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Generate a news item
            item = Simulator.generate_item()
            
            # Adapt format to what frontend expects
            payload = {
                "type": "news_item",
                "country_name": item["country_name"],
                "country_code": item["country_code"],
                "coordinates": item["coordinates"],
                "has_error": item["has_error"],
                "title": item["headline"], # Map headline to title
                "error_details": item["error_detail"] # Map error_detail to error_details
            }
            
            await websocket.send_json(payload)
            
            # Variable delay to simulate real-time feed
            await asyncio.sleep(random.uniform(0.5, 2.0))
    except Exception as e:
        print(f"WebSocket error: {e}")
        # Normal disconnect or error
        pass


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
