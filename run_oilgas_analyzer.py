import os
import json
import requests
import random
import anthropic
from datetime import datetime
from shapely.geometry import shape, Point
from rtree import index

# --- Configuration ---
PLATFORM_DATA_URL = "https://porkytheunique.github.io/ocean-map-data/oil_gas_platforms.geojson"
CORAL_DATA_URL = "https://porkytheunique.github.io/ocean-map-data/corals_with_regions.geojson"
OUTPUT_FILE = 'oilgas_insight.json'
SERVER_LOG_URL = 'https://www.oceanist.blue/map-data/oilgas_insight.json'

# ... (All analysis functions like fetch_geospatial_data, analyze_coral_proximity, etc., remain the same) ...

def main():
    print("\n=============================================", flush=True)
    print(f"🛢️ Starting Oil & Gas Analyzer at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
    print("=============================================", flush=True)

    event_name = os.getenv('GITHUB_EVENT_NAME')
    if event_name == 'schedule':
        today_weekday = datetime.utcnow().weekday()
        if today_weekday != 4: # Friday
            print(f"🗓️ Today is weekday {today_weekday}, but this job only runs on Fridays (4). Exiting.", flush=True)
            return
    print("🗓️ Running oil & gas analysis (manual run or correct day).", flush=True)

    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        print("⛔️ FATAL ERROR: AI_API_KEY secret not found.", flush=True); return
    client = anthropic.Anthropic(api_key=api_key)

    print("\n--- Step 1: Fetching Geospatial Data ---", flush=True)
    platform_data, coral_data = fetch_geospatial_data()
    if not platform_data or not coral_data: return

    print("\n--- Step 2: Performing Story Analysis ---", flush=True)
    story_data = analyze_coral_proximity(platform_data, coral_data)
    if not story_data: return
        
    print("\n--- Step 3: De-duplication Check ---", flush=True)
    all_insights = []
    try:
        res = requests.get(SERVER_LOG_URL)
        if res.status_code == 200:
            all_insights = res.json()
            if not isinstance(all_insights, list): all_insights = [all_insights]
    except Exception: pass

    today_date = datetime.utcnow().strftime('%Y-%m-%d')
    unique_id = f"{story_data['platform_name']}-{today_date}" # Use platform name for uniqueness
    is_duplicate = any(item.get('unique_id') == unique_id for item in all_insights)

    if is_duplicate:
        print(f"❌ Duplicate story for today found ('{unique_id}'). Exiting.", flush=True)
        return

    insight_data = generate_insight_with_ai(story_data, client)
    if not insight_data: return
        
    print("\n--- Step 4: Finalizing and Archiving Output ---", flush=True)
    insight_data['date'] = today_date
    insight_data['unique_id'] = unique_id

    all_insights.insert(0, insight_data)
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_insights, f, indent=2)
    print(f"✅ Saved updated log with {len(all_insights)} total insights to '{OUTPUT_FILE}'.", flush=True)
    
    print("\n=============================================", flush=True)
    print(f"🏁 Oil & Gas Analyzer finished at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
    print("=============================================", flush=True)
# ... (Remember to include all the other functions like generate_insight_with_ai, analyze_coral_proximity, etc. in the file)
