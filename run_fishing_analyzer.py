import os
import json
import requests
import random
import anthropic
from collections import Counter
from datetime import datetime
from shapely.geometry import shape, Point
from rtree import index

# --- Configuration ---
FISHING_DATA_URL = "https://porkytheunique.github.io/ocean-map-data/fishing_events.geojson"
MPA_DATA_URL = "https://porkytheunique.github.io/ocean-map-data/WDPA2.json"
OUTPUT_FILE = 'fishing_insight.json'
SERVER_LOG_URL = 'https://www.oceanist.blue/map-data/fishing_insight.json'
ANALYSIS_SAMPLE_SIZE = 500

# ... (All analysis functions like fetch_geospatial_data, analyze_mpa_proximity, etc., remain the same) ...

def main():
    print("\n=============================================", flush=True)
    print(f"🎣 Starting Fishing Analyzer at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
    print("=============================================", flush=True)
    
    event_name = os.getenv('GITHUB_EVENT_NAME')
    if event_name == 'schedule':
        today_weekday = datetime.utcnow().weekday()
        if today_weekday != 0: # Monday
            print(f"🗓️ Today is weekday {today_weekday}, but this job only runs on Mondays (0). Exiting.", flush=True)
            return
    print("🗓️ Running fishing analysis (manual run or correct day).", flush=True)
    
    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        print("⛔️ FATAL ERROR: AI_API_KEY secret not found.", flush=True); return
    client = anthropic.Anthropic(api_key=api_key)

    print("\n--- Step 2: Fetching Geospatial Data ---", flush=True)
    fishing_data, mpa_data = fetch_geospatial_data()
    if not fishing_data: return

    print("\n--- Step 3: Performing Story Analysis (Roulette) ---", flush=True)
    story_functions = [analyze_mpa_proximity, analyze_global_hotspot, analyze_eez_focus]
    if not mpa_data: story_functions.remove(analyze_mpa_proximity)
        
    chosen_story_function = random.choice(story_functions)
    story_data = chosen_story_function(fishing_data, mpa_data)
    if not story_data:
        print("❌ Script finished: No compelling story found.", flush=True); return
        
    print("\n--- Step 4: De-duplication Check ---", flush=True)
    all_insights = []
    try:
        res = requests.get(SERVER_LOG_URL)
        if res.status_code == 200:
            all_insights = res.json()
            if not isinstance(all_insights, list): all_insights = [all_insights]
    except Exception: pass
    
    today_date = datetime.utcnow().strftime('%Y-%m-%d')
    unique_id = f"{story_data['story_type']}-{today_date}"
    is_duplicate = any(item.get('unique_id') == unique_id for item in all_insights)
    
    if is_duplicate:
        print(f"❌ Duplicate story type for today found ('{unique_id}'). Exiting.", flush=True)
        return

    insight_data = generate_insight_with_ai(story_data, client)
    if not insight_data:
        print("❌ Script finished: AI failed to generate a valid insight.", flush=True); return
        
    print("\n--- Step 5: Finalizing and Archiving Output ---", flush=True)
    insight_data['date'] = today_date
    insight_data['unique_id'] = unique_id
    
    all_insights.insert(0, insight_data)
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_insights, f, indent=2)
    print(f"✅ Saved updated log with {len(all_insights)} total insights to '{OUTPUT_FILE}'.", flush=True)

    print("\n=============================================", flush=True)
    print(f"🏁 Fishing Analyzer finished at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
    print("=============================================", flush=True)
# ... (Remember to include all the other functions like generate_insight_with_ai, analyze_mpa_proximity, etc. in the file)
