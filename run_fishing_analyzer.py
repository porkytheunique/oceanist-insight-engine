import os
import json
import requests
import random
import anthropic
from datetime import datetime
from shapely.geometry import shape, Point

# --- Configuration ---
FISHING_DATA_URL = "https://porkytheunique.github.io/ocean-map-data/fishing_events.geojson"
MPA_DATA_URL = "https://porkytheunique.github.io/ocean-map-data/WDPA.json"
OUTPUT_FILE = 'latest_insight.json'
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

    print(f"  - Pre-processing {len(mpa_data['features'])} MPA geometries...")
    mpa_polygons = {
        mpa['properties'].get('NAME', 'Unnamed Area'): shape(mpa['geometry'])
        for mpa in mpa_data['features'] if mpa.get('geometry')
    }
    print(f"  - Successfully processed {len(mpa_polygons)} valid MPA geometries.")

    all_fishing_events = fishing_data['features']
    sample_size = min(len(all_fishing_events), ANALYSIS_SAMPLE_SIZE)
    fishing_sample = random.sample(all_fishing_events, sample_size)
    print(f"  - Analyzing a random sample of {sample_size} fishing events.")

    closest_event = None
    min_distance = float('inf')

    for i, event in enumerate(fishing_sample):
        if i % 50 == 0:
            print(f"    - Analyzing event {i}/{sample_size}...")
        
        point = Point(event['geometry']['coordinates'])
        for mpa_name, mpa_poly in mpa_polygons.items():
            distance = point.distance(mpa_poly)
            if distance < min_distance:
                min_distance = distance
                closest_event = {
                    "mpa_name": mpa_name,
                    "distance_degrees": distance,
                    "distance_km": distance * 111.32,
                    "fishing_coords": event['geometry']['coordinates']
                }

    if closest_event:
        print("  ✅ Analysis Complete: Found a notable proximity event.")
        print(f"     - Closest Event: A fishing vessel was detected {closest_event['distance_km']:.2f} km from the boundary of '{closest_event['mpa_name']}'.")
        # Add a story type for the AI prompt
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
    
    # We can have different prompts for different story types in the future.
    if story_data.get('story_type') == 'mpa_proximity':
        mpa_name = story_data['mpa_name']
        distance_km = story_data['distance_km']
        
        prompt = f"""You are an expert science communicator for the website oceanist.blue. Your task is to analyze the following geospatial data and produce a JSON object for our 'Human Impact Map' insight feed.

Analysis Result: A fishing vessel was detected {distance_km:.2f} km from the boundary of the '{mpa_name}' Marine Protected Area.

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

    # --- REPLACED PLACEHOLDER ---
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
