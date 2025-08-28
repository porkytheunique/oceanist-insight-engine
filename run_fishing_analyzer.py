import os
import json
import requests
import random
from datetime import datetime
from shapely.geometry import shape, Point

# --- Configuration ---
FISHING_DATA_URL = "https://porkytheunique.github.io/ocean-map-data/fishing_events.geojson"
MPA_DATA_URL = "https://porkytheunique.github.io/ocean-map-data/WDPA.json"
OUTPUT_FILE = 'latest_insight.json'
# To ensure the script runs quickly, we'll analyze a random sample of fishing points.
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
        print(f"  ✅ Success: Loaded {len(fishing_data.get('features', []))} fishing events.")
    except Exception as e:
        print(f"  ❌ FATAL ERROR: Could not fetch or parse fishing data: {e}")
        return None, None

    try:
        print(f"  - Downloading MPA data from {MPA_DATA_URL}...")
        mpa_response = requests.get(MPA_DATA_URL)
        mpa_response.raise_for_status()
        mpa_data = mpa_response.json()
        print(f"  ✅ Success: Loaded {len(mpa_data.get('features', []))} MPA features.")
    except Exception as e:
        print(f"  ❌ FATAL ERROR: Could not fetch or parse MPA data: {e}")
        return fishing_data, None

    return fishing_data, mpa_data

def analyze_mpa_proximity(fishing_data, mpa_data):
    """
    Finds a fishing event that is happening close to an MPA boundary.
    """
    print("\n--- Starting Story Analysis: MPA Proximity ---")
    if not mpa_data:
        print("  - ❌ Cannot run MPA Proximity analysis: MPA data failed to load.")
        return None

    # Convert MPA features to Shapely objects for efficient calculation
    print(f"  - Pre-processing {len(mpa_data['features'])} MPA geometries...")
    mpa_polygons = {
        mpa['properties'].get('NAME', 'Unnamed Area'): shape(mpa['geometry'])
        for mpa in mpa_data['features'] if mpa.get('geometry')
    }
    print(f"  - Successfully processed {len(mpa_polygons)} valid MPA geometries.")

    # Select a random sample of fishing events to analyze for performance
    all_fishing_events = fishing_data['features']
    sample_size = min(len(all_fishing_events), ANALYSIS_SAMPLE_SIZE)
    fishing_sample = random.sample(all_fishing_events, sample_size)
    print(f"  - Analyzing a random sample of {sample_size} fishing events.")

    closest_event = None
    min_distance = float('inf')

    # Brute-force check of each fishing point against each MPA polygon
    for i, event in enumerate(fishing_sample):
        if i % 50 == 0: # Print progress update every 50 events
            print(f"    - Analyzing event {i}/{sample_size}...")
        
        point = Point(event['geometry']['coordinates'])
        for mpa_name, mpa_poly in mpa_polygons.items():
            distance = point.distance(mpa_poly)
            if distance < min_distance:
                min_distance = distance
                closest_event = {
                    "mpa_name": mpa_name,
                    "distance_degrees": distance,
                    "distance_km": distance * 111.32, # Approximate conversion from degrees to km
                    "fishing_coords": event['geometry']['coordinates']
                }

    if closest_event:
        print("  ✅ Analysis Complete: Found a notable proximity event.")
        print(f"     - Closest Event: A fishing vessel was detected {closest_event['distance_km']:.2f} km from the boundary of '{closest_event['mpa_name']}'.")
        return closest_event
    else:
        print("  - ❌ Analysis Complete: Could not find a notable event in the sample.")
        return None

def main():
    """
    Main function to run the fishing analysis process.
    """
    print("\n=============================================")
    print(f"🎣 Starting Fishing Analyzer at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=============================================")

    # For now, we'll let it run any day for testing. We'll add the Monday check later.
    print("🗓️ Running scheduled fishing analysis.")
    
    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        print("⛔️ FATAL ERROR: AI_API_KEY secret not found.")
        return

    print("\n--- Step 2: Fetching Geospatial Data ---")
    fishing_data, mpa_data = fetch_geospatial_data()
    
    if not fishing_data:
        print("❌ Script finished: Could not retrieve fishing data.")
        return

    # --- REPLACED PLACEHOLDER ---
    print("\n--- Step 3: Performing Story Analysis ---")
    # This is the first part of our "Story Roulette". For now, it only has one option.
    story_data = analyze_mpa_proximity(fishing_data, mpa_data)

    if not story_data:
        print("❌ Script finished: No compelling story found in the data analysis.")
        return

    # --- Next steps will go here ---
    # 4. Build a prompt for the AI using story_data.
    # 5. Call the AI and save the output.
    # --------------------------------
    print("\n--- Step 4: AI Processing (Placeholder) ---")
    print("🤖 Analysis complete. AI prompt generation will go here.")
    print(f"   - Story data to use: {story_data}")


    print("\n=============================================")
    print(f"🏁 Fishing Analyzer finished at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=============================================")

if __name__ == "__main__":
    main()
