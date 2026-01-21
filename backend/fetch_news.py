import asyncio
import aiohttp
import trafilatura
import json
import os
from datetime import datetime, timezone

GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

def is_english(text):
    """
    Simple heuristic to check if text is primarily English.
    Checks if > 80% of characters are ASCII.
    """
    if not text:
        return False
    try:
        # Calculate ratio of ASCII characters
        ascii_count = sum(1 for c in text if c.isascii())
        ratio = ascii_count / len(text)
        return ratio > 0.8
    except:
        return False

async def fetch_gdelt_news(query="sourcelang:eng (domain:cnn.com OR domain:bbc.com OR domain:reuters.com OR domain:aljazeera.com)", max_records=20):
    """
    Fetch news metadata from GDELT 2.0 Doc API.
    """
    # GDELT API Parameters
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": max_records,
        "format": "json",
        "sort": "DateDesc"
    }
    print(f"Requesting GDELT API: {params}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(GDELT_API_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    articles = data.get("articles", [])
                    print(f"GDELT API returned {len(articles)} articles.")
                    return articles
                else:
                    print(f"Error fetching GDELT: HTTP {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text[:200]}")
                    return []
        except Exception as e:
            print(f"Exception fetching GDELT: {e}")
            return []

async def process_article(session, article):
    """
    Fetch article HTML and extract main text using trafilatura.
    """
    url = article.get("url")
    if not url:
        return None
    
    # Basic metadata preservation
    processed = {
        "url": url,
        "title": article.get("title"),
        "date": article.get("seendate"),
        "country": article.get("sourcecountry"),
        "domain": article.get("domain"),
        "language": article.get("language"),
        "scraped_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        # Timeout is crucial for crawling
        timeout = aiohttp.ClientTimeout(total=10)
        async with session.get(url, timeout=timeout, headers={"User-Agent": "SpellAtlasBot/1.0"}) as resp:
            if resp.status == 200:
                # Read as binary then decode to handle encoding issues gracefully if needed, 
                # but aiohttp text() is usually good.
                try:
                    html = await resp.text()
                except UnicodeDecodeError:
                    html = await resp.read() # trafilatura can handle bytes too sometimes or we decode loosely
                
                # Run trafilatura in a separate thread to not block async loop
                # trafilatura.extract can take a string or bytes
                text = await asyncio.to_thread(trafilatura.extract, html)
                
                if text:
                    # Quality Filters
                    if len(text) < 200:
                        print(f"Skipping {url}: Content too short ({len(text)} chars)")
                    elif not is_english(text):
                        print(f"Skipping {url}: Content not English")
                    else:
                        processed["content"] = text
                        return processed
                else:
                    print(f"Skipping {url}: Trafilatura extraction failed")
            else:
                print(f"Skipping {url}: HTTP {resp.status}")
    except asyncio.TimeoutError:
        print(f"Skipping {url}: Timeout")
    except Exception as e:
        print(f"Skipping {url}: {e}")
        
    return None

async def main():
    print("--- Phase 2: Data Acquisition Started ---")
    
    # 1. Fetch Metadata from GDELT
    # We query for English news.
    # Note: GDELT updates every 15 mins.
    articles = await fetch_gdelt_news(max_records=20)
    
    if not articles:
        print("No articles found from GDELT. Exiting.")
        return

    # 2. Scrape Content
    print(f"\nScraping content for {len(articles)} articles...")
    results = []
    
    async with aiohttp.ClientSession() as session:
        tasks = [process_article(session, a) for a in articles]
        processed = await asyncio.gather(*tasks)
        results = [p for p in processed if p]
        
    print(f"\n--- Summary ---")
    print(f"Requested: {len(articles)}")
    print(f"Successfully Scraped: {len(results)}")
    
    # 3. Upload to S3 and Register in DB
    if not results:
        print("No results to save.")
        return

    # Prepare JSON
    json_data = json.dumps(results, indent=2, ensure_ascii=False)
    
    # Generate S3 Key
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    s3_key = f"raw_news/news_{timestamp}.json"
    
    # Save to temp file for upload (S3Client expects file path)
    temp_file = f"temp_{timestamp}.json"
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(json_data)
        
    print(f"\nUploading to Object Storage (Key: {s3_key})...")
    s3 = S3Client()
    success = s3.upload_file(temp_file, s3_key)
    
    # Clean up temp file
    if os.path.exists(temp_file):
        os.remove(temp_file)
        
    if success:
        print("Upload successful.")
        try:
            print("Registering snapshot in Database...")
            storage = DataStorage()
            storage.register_snapshot(s3_key, len(results))
            print("Snapshot registered.")
        except Exception as e:
            print(f"Failed to register snapshot in DB: {e}")
    else:
        print("Upload failed. Dumping to local fallback.")
        # Fallback to local
        output_dir = "data"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "sample_news_scraped.json")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json_data)
        print(f"Saved fallback to {output_file}")

    # Show a sample
    if results:
        print("\nSample Article:")
        print(f"Title: {results[0]['title']}")
        print(f"Country: {results[0]['country']}")
        print(f"Content Snippet: {results[0]['content'][:100]}...")

if __name__ == "__main__":
    # Windows SelectorEventLoop policy fix for Python 3.8+
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
