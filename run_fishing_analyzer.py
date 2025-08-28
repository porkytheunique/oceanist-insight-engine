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
    """
    Downloads the fishing and MPA GeoJSON data from their URLs.
    """
    print("🌎 Fetching geospatial data...")
    fishing_data, mpa_data = None, None
    try:
        print(f"  - Downloading fishing data from {FISHING_DATA_URL}...")
        fishing_response = requests.get(FISHING_DATA_URL)
        fishing_response.raise_for_status()
        fishing_data = fishing_response.json()
        fishing_events = fishing_data.get('entries', [])
        print(f"  ✅ Success: Loaded {len(fishing_events)} fishing events from the 'entries' key.")
    except Exception as e:
        print(f"  ❌ FATAL ERROR: Could not fetch or parse fishing data: {e}")
        return None, None

    try:
        print(f"  - Downloading MPA data from {MPA_DATA_URL}...")
        mpa_response = requests.get(MPA_DATA_URL)
        mpa_response.raise_for_status()
        mpa_data = mpa_response.json()
        mpa_geometries = mpa_data.get('geometries', [])
        print(f"  ✅ Success: Loaded {len(mpa_geometries)} MPA geometries from the 'geometries' key.")
    except Exception as e:
        print(f"  ⚠️ WARNING: Could not fetch or parse MPA data: {e}")
        mpa_data = None

    return fishing_data, mpa_data

def analyze_mpa_proximity(fishing_data, mpa_data):
    """
    Finds a fishing event that is happening close to an MPA boundary.
    """
    print("\n--- Starting Story Analysis: MPA Proximity ---")
    mpa_geometries = mpa_data.get('geometries', [])
    fishing_events = fishing_data.get('entries', [])

    if not mpa_geometries or not fishing_events:
        return None

    print(f"  - Pre-processing {len(mpa_geometries)} MPA geometries...")
    mpa_shapes = [shape(geom) for geom in mpa_geometries if geom and geom.get('coordinates')]
    print(f"  - Successfully processed {len(mpa_shapes)} valid MPA shapes.")

    print("  - 🗺️ Building spatial index for all MPAs...")
    idx = index.Index()
    for pos, mpa_shape in enumerate(mpa_shapes):
        idx.insert(pos, mpa_shape.bounds)
    print("  - ✅ Spatial index built successfully.")
        
    sample_size = min(len(fishing_events), ANALYSIS_SAMPLE_SIZE)
    fishing_sample = random.sample(fishing_events, sample_size)
    print(f"  - Analyzing a random sample of {sample_size} fishing events.")

    closest_event = None
    min_distance = float('inf')

    for i, event in enumerate(fishing_sample):
        if i % 100 == 0:
            print(f"    - Analyzing event {i}/{sample_size}...")
        
        coords = [event['position']['lon'], event['position']['lat']]
        point = Point(coords)
        
        nearest_mpa_indices = list(idx.nearest(point.bounds, 5))
        
        for mpa_idx in nearest_mpa_indices:
            distance = point.distance(mpa_shapes[mpa_idx])
            if distance < min_distance:
                min_distance = distance
                closest_event = {
                    "distance_km": distance * 111.32,
                    "fishing_coords": coords
                }

    if closest_event:
        print("  ✅ Analysis Complete: Found a notable proximity event.")
        distance_text = f"{closest_event['distance_km']:.2f} km"
        if closest_event['distance_km'] < 0.1:
            distance_text = "less than 100 meters"
        
        print(f"     - Closest Event: A fishing vessel was detected {distance_text} from a nearby MPA.")
        closest_event['story_type'] = 'mpa_proximity'
        closest_event['distance_text'] = distance_text
        return closest_event
    return None

def analyze_global_hotspot(fishing_data, mpa_data=None):
    """
    Finds the busiest 5x5 degree grid cell of fishing activity in the world.
    """
    print("\n--- Starting Story Analysis: Global Fishing Hotspot ---")
    fishing_events = fishing_data.get('entries', [])
    if not fishing_events:
        return None

    print(f"  - Analyzing all {len(fishing_events)} events to find the global hotspot...")
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
    
    print("  ✅ Analysis Complete: Found the global fishing hotspot.")
    print(f"     - Hotspot: The 5x5 degree cell centered near {story_data['center_coords']} had {story_data['event_count']} fishing events.")
    return story_data

def analyze_eez_focus(fishing_data, mpa_data=None):
    """
    Finds which EEZ contains the most fishing activity from the GFW data.
    """
    print("\n--- Starting Story Analysis: EEZ Focus ---")
    fishing_events = fishing_data.get('entries', [])
    if not fishing_events:
        return None
    
    eez_counts = Counter(event['regions']['eez'][0] for event in fishing_events if event.get('regions', {}).get('eez'))
    
    if not eez_counts:
        print("  - ❌ No EEZ data found in fishing events.")
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

    print("  ✅ Analysis Complete: Found the busiest EEZ.")
    print(f"     - Busiest EEZ: '{story_data['eez_name']}' with {story_data['event_count']} fishing events.")
    return story_data

def generate_insight_with_ai(story_data, client):
    """
    Builds a prompt based on the story type and asks the AI to generate the insight.
    """
    print("\n--- Step 4: Generating AI Insight ---")
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
        print("  - ❌ Error: Unknown story type.")
        return None
        
    try:
        print(f"  - 🤖 Sending prompt for story type '{story_type}'...")
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text
        
        print("   - AI Response (raw):")
        print(message)
        json_response = message.strip().lstrip("```json").rstrip("```")
        return json.loads(json_response)
    except Exception as e:
        print(f"  - ❌ AI insight generation failed: {e}")
        return None

# In run_fishing_analyzer.py

def main():
    """
    Main function to run the fishing analysis process.
    """
    print("\n=============================================")
    print(f"🎣 Starting Fishing Analyzer at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=============================================")
    
    # Check how the workflow was triggered
    event_name = os.getenv('GITHUB_EVENT_NAME')
    
    # Only check the schedule if it's a scheduled run
    if event_name == 'schedule':
        today_weekday = datetime.utcnow().weekday()
        if today_weekday != 0: # Monday is 0
             print(f"🗓️ Today is weekday {today_weekday}, but this job only runs on Mondays (0). Exiting.")
             return

    print("🗓️ Running fishing analysis (manual run or correct day).")
    
    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        print("⛔️ FATAL ERROR: AI_API_KEY secret not found.")
        return
    client = anthropic.Anthropic(api_key=api_key)

    # ... (the rest of the main function is the same) ...
    print("\n--- Step 2: Fetching Geospatial Data ---")
    fishing_data, mpa_data = fetch_geospatial_data()
    if not fishing_data:
        print("❌ Script finished: Could not retrieve fishing data.")
        return

    print("\n--- Step 3: Performing Story Analysis (Roulette) ---")
    
    story_functions = []
    if mpa_data and fishing_data:
        story_functions.append(analyze_mpa_proximity)
    if fishing_data:
        story_functions.append(analyze_global_hotspot)
        story_functions.append(analyze_eez_focus)

    if not story_functions:
        print("❌ Script finished: Not enough data to run any analysis.")
        return

    chosen_story_function = random.choice(story_functions)
    story_data = chosen_story_function(fishing_data, mpa_data)
    
    if not story_data:
        print("❌ Script finished: No compelling story found in the data analysis.")
        return
        
    insight_data = generate_insight_with_ai(story_data, client)
    if not insight_data:
        print("❌ Script finished: AI failed to generate a valid insight.")
        return
        
    print("\n--- Step 5: Finalizing and Saving Output ---")
    insight_data['date'] = datetime.utcnow().strftime('%Y-%m-%d')
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(insight_data, f, indent=2)
    print(f"✅ Successfully saved new insight to '{OUTPUT_FILE}'.")
    print("\n=============================================")
    print(f"🏁 Fishing Analyzer finished at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=============================================")

if __name__ == "__main__":
    main()
