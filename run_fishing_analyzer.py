import os
import json
import requests
import random
import anthropic
from datetime import datetime
from shapely.geometry import shape, Point
from rtree import index # New import for the spatial index

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
        print(f"  ❌ FATAL ERROR: Could not fetch or parse MPA data: {e}")
        return fishing_data, None

    return fishing_data, mpa_data

def analyze_mpa_proximity(fishing_data, mpa_data):
    """
    Finds a fishing event that is happening close to an MPA boundary using a spatial index.
    """
    print("\n--- Starting Story Analysis: MPA Proximity ---")
    mpa_geometries = mpa_data.get('geometries', [])
    fishing_events = fishing_data.get('entries', [])

    if not mpa_geometries or not fishing_events:
        print("  - ❌ Cannot run analysis: Missing MPA or fishing data.")
        return None

    print(f"  - Pre-processing {len(mpa_geometries)} MPA geometries...")
    mpa_shapes = [shape(geom) for geom in mpa_geometries if geom and geom.get('coordinates')]
    print(f"  - Successfully processed {len(mpa_shapes)} valid MPA shapes.")

    # --- NEW: Build the Spatial Index ---
    print("  - 🗺️ Building spatial index for all MPAs...")
    idx = index.Index()
    for pos, mpa_shape in enumerate(mpa_shapes):
        idx.insert(pos, mpa_shape.bounds)
    print("  - ✅ Spatial index built successfully.")
    # ------------------------------------
        
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
        
        # --- NEW: Query the index to find the nearest MPA(s) ---
        # Find the 5 nearest MPA candidates from the index
        nearest_mpa_indices = list(idx.nearest(point.bounds, 5))
        
        # Now, only check the distance against these few candidates
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
        print(f"     - Closest Event: A fishing vessel was detected {closest_event['distance_km']:.2f} km from the boundary of a nearby Marine Protected Area.")
        closest_event['story_type'] = 'mpa_proximity'
        return closest_event
    else:
        print("  - ❌ Analysis Complete: Could not find a notable event in the sample.")
        return None

def generate_insight_with_ai(story_data, client):
    """
    Builds a prompt based on the story type and asks the AI to generate the insight.
    """
    print("\n--- Step 4: Generating AI Insight ---")
    
    if story_data.get('story_type') == 'mpa_proximity':
        distance_km = story_data['distance_km']
        
        prompt = f"""You are an expert science communicator for the website oceanist.blue. Your task is to analyze the following geospatial data and produce a JSON object for our 'Human Impact Map' insight feed.

Analysis Result: A fishing vessel was detected {distance_km:.2f} km from the boundary of a Marine Protected Area.

Based on this, create a JSON object with the following structure:
- "tag": Use the hashtag #Fishing.
- "content": Write a 3-4 sentence analysis. Start by stating the fact. Then, briefly explain the concept of 'fishing the line' and why intense fishing activity often clusters around the edges of MPAs, putting these protected ecosystems at risk.
- "map_view": An object with "center" (the fishing vessel's coordinates: {story_data['fishing_coords']}), "zoom": 9, and "maxZoom": 14.

Return ONLY the raw JSON object and nothing else.
"""
    else:
        print("  - ❌ Error: Unknown story type. Cannot generate prompt.")
        return None

    try:
        print("  - 🤖 Sending prompt to AI...")
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
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

def main():
    """
    Main function to run the fishing analysis process.
    """
    print("\n=============================================")
    print(f"🎣 Starting Fishing Analyzer at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=============================================")
    print("🗓️ Running scheduled fishing analysis.")
    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        print("⛔️ FATAL ERROR: AI_API_KEY secret not found.")
        return
    client = anthropic.Anthropic(api_key=api_key)
    print("\n--- Step 2: Fetching Geospatial Data ---")
    fishing_data, mpa_data = fetch_geospatial_data()
    if not fishing_data:
        print("❌ Script finished: Could not retrieve fishing data.")
        return
    print("\n--- Step 3: Performing Story Analysis ---")
    story_data = analyze_mpa_proximity(fishing_data, mpa_data)
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
