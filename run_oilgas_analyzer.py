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

def fetch_geospatial_data():
    print("🌎 Fetching geospatial data...", flush=True)
    platform_data, coral_data = None, None
    try:
        print(f"  - Downloading platform data from {PLATFORM_DATA_URL}...", flush=True)
        platform_response = requests.get(PLATFORM_DATA_URL)
        platform_response.raise_for_status()
        platform_data = platform_response.json()
        platform_features = platform_data.get('features', [])
        print(f"  ✅ Success: Loaded {len(platform_features)} oil & gas platforms.", flush=True)
    except Exception as e:
        print(f"  ❌ FATAL ERROR: Could not fetch or parse platform data: {e}", flush=True)
        return None, None
    try:
        print(f"  - Downloading coral data from {CORAL_DATA_URL}...", flush=True)
        coral_response = requests.get(CORAL_DATA_URL)
        coral_response.raise_for_status()
        coral_data = coral_response.json()
        coral_features = coral_data.get('features', [])
        print(f"  ✅ Success: Loaded {len(coral_features)} coral reef features.", flush=True)
    except Exception as e:
        print(f"  ⚠️ WARNING: Could not fetch or parse coral data: {e}", flush=True)
        coral_data = None
    return platform_data, coral_data

# In run_oilgas_analyzer.py

def analyze_coral_proximity(platform_data, coral_data):
    """
    Finds a random oil/gas platform that is CLOSE to a coral reef.
    """
    print("\n--- Starting Story Analysis: Coral Proximity ---", flush=True)
    platform_features = platform_data.get('features', [])
    coral_features = coral_data.get('features', [])
    if not platform_features or not coral_features:
        print("  - ❌ Cannot run analysis: Missing platform or coral data.", flush=True); return None

    # ... (pre-processing and index building is the same) ...
    print(f"  - Pre-processing {len(coral_features)} coral reef geometries...", flush=True)
    coral_shapes = [shape(geom['geometry']) for geom in coral_features if geom.get('geometry')]
    print(f"  - Successfully processed {len(coral_shapes)} valid coral reef shapes.", flush=True)
    print("  - 🗺️ Building spatial index for all coral reefs...", flush=True)
    idx = index.Index()
    valid_shapes_for_index = []
    original_indices = []
    for i, coral_shape in enumerate(coral_shapes):
        min_x, min_y, max_x, max_y = coral_shape.bounds
        if min_x <= max_x and min_y <= max_y:
            idx.insert(i, coral_shape.bounds)
            valid_shapes_for_index.append(coral_shape)
            original_indices.append(i)
    print(f"  - ✅ Spatial index built successfully with {len(valid_shapes_for_index)} valid shapes.", flush=True)

    # Try a few random platforms to find one that is close enough
    for _ in range(20): # Try up to 20 times to find a close one
        platform = random.choice(platform_features)
        platform_point = shape(platform['geometry'])
        
        nearest_coral_indices_map = list(idx.nearest(platform_point.bounds, 1))
        if not nearest_coral_indices_map:
            continue
            
        mapped_idx = nearest_coral_indices_map[0]
        original_idx = original_indices[mapped_idx]
        distance = platform_point.distance(valid_shapes_for_index[mapped_idx])
        distance_km = distance * 111.32

        # --- NEW THRESHOLD CHECK ---
        # Only consider it a story if it's within 200 km
        if distance_km <= 200:
            print(f"  - Analyzing platform: '{platform['properties'].get('Unit Name', 'Unnamed')}'")
            closest_coral_feature = coral_features[original_idx]
            story_data = {
                "platform_name": platform['properties'].get('Unit Name', 'Unnamed Platform'),
                "platform_country": platform['properties'].get('Country/Area', 'an unknown location'),
                "platform_coords": platform['geometry']['coordinates'],
                "coral_ecoregion": closest_coral_feature['properties'].get('ECOREGION', 'a sensitive marine area'),
                "distance_km": distance_km
            }
            print("  ✅ Analysis Complete: Found a notable proximity event.", flush=True)
            print(f"     - Platform '{story_data['platform_name']}' is {story_data['distance_km']:.2f} km from a coral reef.", flush=True)
            return story_data
    
    print("  - ❌ Analysis Complete: No platforms found within the 200km threshold in this run's samples.", flush=True)
    return None

def generate_insight_with_ai(story_data, client):
    print("\n--- Generating AI Insight ---", flush=True)
    platform_name = story_data['platform_name']; platform_country = story_data['platform_country']
    coral_ecoregion = story_data['coral_ecoregion']; distance_km = round(story_data['distance_km'], 1)
    platform_coords = story_data['platform_coords']
    prompt = f"""You are a science communicator. Analyze: The '{platform_name}' oil/gas platform in {platform_country} is approx. {distance_km} km from a coral reef in the '{coral_ecoregion}' ecoregion at {platform_coords}. Create a JSON object with keys "tag" (#FossilFuels), "content" (3-4 sentences on the location, fact, and risks to reefs, using approximate language), and "map_view" (center: {platform_coords}, zoom: 8, maxZoom: 12). Return ONLY the raw JSON object."""
    try:
        print(f"  - 🤖 Sending prompt to AI...", flush=True)
        message = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role": "user", "content": prompt}]).content[0].text
        print("   - AI Response (raw):", flush=True); print(message, flush=True)
        return json.loads(message.strip().lstrip("```json").rstrip("```"))
    except Exception as e:
        print(f"  - ❌ AI insight generation failed: {e}", flush=True); return None

def main():
    print("\n=============================================", flush=True)
    print(f"🛢️ Starting Oil & Gas Analyzer at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
    print("=============================================", flush=True)
    
    event_name = os.getenv('GITHUB_EVENT_NAME')
    if event_name == 'schedule':
        today_weekday = datetime.utcnow().weekday()
        if today_weekday != 4:
            print(f"🗓️ Today is weekday {today_weekday}, but this job only runs on Fridays (4). Exiting.", flush=True); return
    print("🗓️ Running oil & gas analysis (manual run or correct day).", flush=True)
    
    api_key = os.getenv('AI_API_KEY')
    if not api_key: print("⛔️ FATAL ERROR: AI_API_KEY secret not found.", flush=True); return
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
            data = res.json()
            if isinstance(data, list): all_insights = data
            elif isinstance(data, dict): all_insights = [data]
    except Exception: pass
    
    today_date = datetime.utcnow().strftime('%Y-%m-%d')
    unique_id = f"{story_data['platform_name']}-{today_date}"
    is_duplicate = any(item.get('unique_id') == unique_id for item in all_insights)
    
    if is_duplicate:
        print(f"❌ Duplicate story for today found ('{unique_id}'). Exiting.", flush=True); return

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

if __name__ == "__main__":
    main()
