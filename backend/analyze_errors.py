import json
import os
from collections import Counter
import pandas as pd

def analyze_errors():
    input_file = os.path.join("data", "detected_errors.json")
    
    if not os.path.exists(input_file):
        print(f"File {input_file} not found. Run detect_errors.py first.")
        return
        
    print(f"Loading error data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} articles with errors.")
    
    # Flatten errors
    all_error_instances = []
    country_stats = Counter()
    
    for article in data:
        country = article.get("country", "Unknown")
        errors = article.get("errors", [])
        
        country_stats[country] += len(errors)
        
        for err in errors:
            all_error_instances.append({
                "word": err["word"],
                "suggestion": err["suggestion"],
                "tag": err.get("tag", ""),
                "country": country,
                "distance": err.get("distance", 0)
            })
            
    df = pd.DataFrame(all_error_instances)
    
    if df.empty:
        print("No errors found to analyze.")
        return
        
    print("\n--- Summary Statistics ---")
    print(f"Total Errors Detected: {len(df)}")
    print(f"Unique Misspelled Words: {df['word'].nunique()}")
    
    print("\n--- Top 20 Common Errors ---")
    top_errors = df['word'].value_counts().head(20)
    print(top_errors)
    
    print("\n--- Top 20 Error -> Suggestion Pairs ---")
    pair_counts = df.groupby(['word', 'suggestion']).size().sort_values(ascending=False).head(20)
    print(pair_counts)
    
    print("\n--- Errors by Country (Top 10) ---")
    print(pd.Series(country_stats).sort_values(ascending=False).head(10))
    
    # Save stats to CSV
    output_csv = os.path.join("data", "error_analysis_summary.csv")
    df.to_csv(output_csv, index=False)
    print(f"\nDetailed analysis saved to {output_csv}")

if __name__ == "__main__":
    analyze_errors()
