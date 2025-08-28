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
ANALYSIS_SAMPLE_SIZE = 500

def fetch_geospatial_data():
    print("🌎 Fetching geospatial data...", flush=True)
    fishing_data, mpa_data = None, None
    try:
        print(f"  - Downloading fishing data from {FISHING_DATA_URL}...", flush=True)
        fishing_response = requests.get(FISHING_DATA_URL)
        fishing_response.raise_for_status()
        fishing_data = fishing_response.json()
        fishing_events = fishing_data.get('entries', [])
        print(f"  ✅ Success: Loaded {len(fishing_events)} fishing events from the 'entries' key.", flush=True)
    except Exception as e:
        print(f"  ❌ FATAL ERROR: Could not fetch or parse fishing data: {e}", flush=True)
        return None, None
    try:
        print(f"  - Downloading MPA data from {MPA_DATA_URL}...", flush=True)
        mpa_response = requests.get(MPA_DATA_URL)
        mpa_response.raise_for_status()
        mpa_data = mpa_response.json()
        mpa_geometries = mpa_data.get('geometries', [])
        print(f"  ✅ Success: Loaded {len(mpa_geometries)} MPA geometries from the 'geometries' key.", flush=True)
    except Exception as e:
        print(f"  ⚠️ WARNING: Could not fetch or parse MPA data: {e}", flush=True)
        mpa_data = None
    return fishing_data, mpa_data

def analyze_mpa_proximity(fishing_data, mpa_data):
    print("\n--- Starting Story Analysis: MPA Proximity ---", flush=True)
    mpa_geometries = mpa_data.get('geometries', [])
    fishing_events = fishing_data.get('entries', [])
    if not mpa_geometries or not fishing_events:
        return None
    print(f"  - Pre-processing {len(mpa_geometries)} MPA geometries...", flush=True)
    mpa_shapes = [shape(geom) for geom in mpa_geometries if geom and geom.get('coordinates')]
    print(f"  - Successfully processed {len(mpa_shapes)} valid MPA shapes.", flush=True)
    print("  - 🗺️ Building spatial index for all MPAs...", flush=True)
    idx = index.Index()
    for pos, mpa_shape in enumerate(mpa_shapes):
        idx.insert(pos, mpa_shape.bounds)
    print("  - ✅ Spatial index built successfully.", flush=True)
    sample_size = min(len(fishing_events), ANALYSIS_SAMPLE_SIZE)
    fishing_sample = random.sample(fishing_events, sample_size)
    print(f"  - Analyzing a random sample of {sample_size} fishing events.", flush=True)
    closest_event = None
    min_distance = float('inf')
    for i, event in enumerate(fishing_sample):
        if i % 100 == 0:
            print(f"    - Analyzing event {i}/{sample_size}...", flush=True)
        coords = [event['position']['lon'], event['position']['lat']]
        point = Point(coords)
        nearest_mpa_indices = list(idx.nearest(point.bounds, 5))
        for mpa_idx in nearest_mpa_indices:
            distance = point.distance(mpa_shapes[mpa_idx])
            if distance < min_distance:
                min_distance = distance
                closest_event = {"distance_km": distance * 111.32, "fishing_coords": coords}
    if closest_event:
        print("  ✅ Analysis Complete: Found a notable proximity event.", flush=True)
        distance_text = f"{closest_event['distance_km']:.2f} km"
        if closest_event['distance_km'] < 0.1:
            distance_text = "less than 100 meters"
        print(f"     - Closest Event: A fishing vessel was detected {distance_text} from a nearby MPA.", flush=True)
        closest_event['story_type'] = 'mpa_proximity'
        closest_event['distance_text'] = distance_text
        return closest_event
    return None

def analyze_global_hotspot(fishing_data, mpa_data=None):
    print("\n--- Starting Story Analysis: Global Fishing Hotspot ---", flush=True)
    fishing_events = fishing_data.get('entries', [])
    if not fishing_events:
        return None
    print(f"  - Analyzing all {len(fishing_events)} events to find the global hotspot...", flush=True)
    grid = {}
    for event in fishing_events:
        lon = int(event['position']['lon'] // 5 * 5)
        lat = int(event['position']['lat'] // 5 * 5)
        cell = (lon, lat)
        grid[cell] = grid.get(cell, 0) + 1
    if not grid:
        return None
    hotspot_cell = max(grid, key=grid.get)
    hotspot_count = grid[hotspot_cell]
    story_data = {
        "story_type": "global_hotspot",
        "center_coords": [hotspot_cell[0] + 2.5, hotspot_cell[1] + 2.5],
        "event_count": hotspot_count
    }
    print("  ✅ Analysis Complete: Found the global fishing hotspot.", flush=True)
    print(f"     - Hotspot: The 5x5 degree cell centered near {story_data['center_coords']} had {story_data['event_count']} fishing events.", flush=True)
    return story_data

def analyze_eez_focus(fishing_data, mpa_data=None):
    print("\n--- Starting Story Analysis: EEZ Focus ---", flush=True)
    fishing_events = fishing_data.get('entries', [])
    if not fishing_events:
        return None
    eez_counts = Counter(event['regions']['eez'][0] for event in fishing_events if event.get('regions', {}).get('eez'))
    if not eez_counts:
        print("  - ❌ No EEZ data found in fishing events.", flush=True)
        return None
    most_common_eez, event_count = eez_counts.most_common(1)[0]
    sample_coord = None
    for event in fishing_events:
        if event.get('regions', {}).get('eez') and event['regions']['eez'][0] == most_common_eez:
            sample_coord = [event['position']['lon'], event['position']['lat']]
            break
    story_data = {
        "story_type": "eez_focus",
        "eez_name": most_common_eez,
        "event_count": event_count,
        "center_coords": sample_coord
    }
    print("  ✅ Analysis Complete: Found the busiest EEZ.", flush=True)
    print(f"     - Busiest EEZ: '{story_data['eez_name']}' with {story_data['event_count']} fishing events.", flush=True)
    return story_data

def generate_insight_with_ai(story_data, client):
    print("\n--- Step 4: Generating AI Insight ---", flush=True)
    prompt = ""
    story_type = story_data.get('story_type')
    if story_type == 'mpa_proximity':
        distance_text = story_data['distance_text']
        fishing_coords = story_data['fishing_coords']
        prompt = f"""You are a science communicator for oceanist.blue. Analyze the following data and produce a JSON object.
Analysis Result: A fishing vessel was detected at a distance of {distance_text} from a Marine Protected Area boundary, at coordinates {fishing_coords}.
JSON Instructions: Create a JSON object with keys "tag" (#Fishing), "content" (3-4 sentences starting with the geographic region, stating the fact with cautious language, and explaining 'fishing the line'), and "map_view" (center: {fishing_coords}, zoom: 9, maxZoom: 14).
Return ONLY the raw JSON object."""
    elif story_type == 'global_hotspot':
        center_coords = story_data['center_coords']
        event_count = story_data['event_count']
        prompt = f"""You are a science communicator for oceanist.blue. Analyze the following data and produce a JSON object.
Analysis Result: The world's busiest fishing hotspot is the 5x5 degree area centered at {center_coords}, with {event_count} fishing events.
JSON Instructions: Create a JSON object with keys "tag" (#Fishing), "content" (3-4 sentences identifying the ocean basin/sea, explaining its significance as a fishery, and discussing the industrial scale), and "map_view" (center: {center_coords}, zoom: 5, maxZoom: 10).
Return ONLY the raw JSON object."""
    elif story_type == 'eez_focus':
        eez_name = story_data['eez_name']
        event_count = story_data['event_count']
        center_coords = story_data['center_coords']
        prompt = f"""You are a science communicator for oceanist.blue. Analyze the following data and produce a JSON object.
Analysis Result: The most active fishing zone was the Exclusive Economic Zone (EEZ) of '{eez_name}', with {event_count} fishing events. A sample event is at {center_coords}.
JSON Instructions: Create a JSON object with keys "tag" (#Fishing), "content" (3-4 sentences identifying the country, discussing the EEZ's significance, and explaining what an EEZ is), and "map_view" (center: {center_coords}, zoom: 5, maxZoom: 10).
Return ONLY the raw JSON object."""
    else:
        print("  - ❌ Error: Unknown story type.", flush=True)
        return None
    try:
        print(f"  - 🤖 Sending prompt for story type '{story_type}'...", flush=True)
        message = client.messages.create(
            model="claude-sonnet-4-20250514", # Your preferred model
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text
        print("   - AI Response (raw):", flush=True)
        print(message, flush=True)
        json_response = message.strip().lstrip("```json").rstrip("```")
        return json.loads(json_response)
    except Exception as e:
        print(f"  - ❌ AI insight generation failed: {e}", flush=True)
        return None

# In run_fishing_analyzer.py, replace the entire main() function

# In run_fishing_analyzer.py, replace the entire main() function with this:

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
        print("⛔️ FATAL ERROR: AI_API_KEY secret not found.", flush=True)
        return
    client = anthropic.Anthropic(api_key=api_key)

    print("\n--- Step 2: Fetching Geospatial Data ---", flush=True)
    fishing_data, mpa_data = fetch_geospatial_data()
    if not fishing_data:
        return

    print("\n--- Step 3: Performing Story Analysis (Roulette) ---", flush=True)
    story_functions = []
    if mpa_data and fishing_data:
        story_functions.append(analyze_mpa_proximity)
    if fishing_data:
        story_functions.append(analyze_global_hotspot)
        story_functions.append(analyze_eez_focus)
    if not story_functions:
        print("❌ Script finished: Not enough data for any analysis.", flush=True)
        return
    chosen_story_function = random.choice(story_functions)
    story_data = chosen_story_function(fishing_data, mpa_data)
    
    if not story_data:
        print("❌ Script finished: No compelling story found.", flush=True)
        return
        
    insight_data = generate_insight_with_ai(story_data, client)
    if not insight_data:
        print("❌ Script finished: AI failed to generate a valid insight.", flush=True)
        return
        
    # In main() for run_fishing_analyzer.py, REPLACE the final "Step 5" block

    print("\n--- Step 5: Finalizing and Archiving Output ---", flush=True)
    insight_data['date'] = datetime.utcnow().strftime('%Y-%m-%d')
    
    all_insights = []
    log_url = 'https://www.oceanist.blue/map-data/fishing_insight.json' # URL for THIS script's log
    try:
        existing_log_res = requests.get(log_url)
        if existing_log_res.status_code == 200:
            all_insights = existing_log_res.json()
            print(f"✅ Loaded existing fishing log with {len(all_insights)} insights.", flush=True)
    except Exception as e:
        print(f"⚠️ Could not load existing fishing log, will create a new one. Reason: {e}", flush=True)

    all_insights.insert(0, insight_data)
    
    with open("fishing_insight.json", 'w') as f:
        json.dump(all_insights, f, indent=2)
    print(f"✅ Saved updated fishing log with {len(all_insights)} total insights.", flush=True)

if __name__ == "__main__":
    main()
