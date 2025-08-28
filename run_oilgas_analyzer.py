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

def fetch_geospatial_data():
    """
    Downloads the platform and coral GeoJSON data from their URLs.
    """
    print("🌎 Fetching geospatial data...")
    platform_data, coral_data = None, None
    try:
        print(f"  - Downloading platform data from {PLATFORM_DATA_URL}...")
        platform_response = requests.get(PLATFORM_DATA_URL)
        platform_response.raise_for_status()
        platform_data = platform_response.json()
        platform_features = platform_data.get('features', [])
        print(f"  ✅ Success: Loaded {len(platform_features)} oil & gas platforms.")
    except Exception as e:
        print(f"  ❌ FATAL ERROR: Could not fetch or parse platform data: {e}")
        return None, None

    try:
        print(f"  - Downloading coral data from {CORAL_DATA_URL}...")
        coral_response = requests.get(CORAL_DATA_URL)
        coral_response.raise_for_status()
        coral_data = coral_response.json()
        coral_features = coral_data.get('features', [])
        print(f"  ✅ Success: Loaded {len(coral_features)} coral reef features.")
    except Exception as e:
        print(f"  ⚠️ WARNING: Could not fetch or parse coral data: {e}")
        coral_data = None

    return platform_data, coral_data

def analyze_coral_proximity(platform_data, coral_data):
    """
    Finds a random oil/gas platform that is close to a coral reef.
    """
    print("\n--- Starting Story Analysis: Coral Proximity ---")
    platform_features = platform_data.get('features', [])
    coral_features = coral_data.get('features', [])

    if not platform_features or not coral_features:
        print("  - ❌ Cannot run analysis: Missing platform or coral data.")
        return None

    print(f"  - Pre-processing {len(coral_features)} coral reef geometries...")
    coral_shapes = [shape(geom['geometry']) for geom in coral_features if geom.get('geometry')]
    print(f"  - Successfully processed {len(coral_shapes)} valid coral reef shapes.")

    print("  - 🗺️ Building spatial index for all coral reefs...")
    idx = index.Index()
    valid_shapes_for_index = []
    for i, coral_shape in enumerate(coral_shapes):
        # --- NEW VALIDATION STEP ---
        # A valid bounding box has min_x <= max_x and min_y <= max_y
        min_x, min_y, max_x, max_y = coral_shape.bounds
        if min_x <= max_x and min_y <= max_y:
            idx.insert(i, coral_shape.bounds)
            valid_shapes_for_index.append(coral_shape)
        # ---------------------------
        
    print(f"  - ✅ Spatial index built successfully with {len(valid_shapes_for_index)} valid shapes.")
        
    platform = random.choice(platform_features)
    platform_point = shape(platform['geometry'])
    
    print(f"  - Analyzing a random platform: '{platform['properties'].get('Unit Name', 'Unnamed')}'")

    nearest_coral_indices = list(idx.nearest(platform_point.bounds, 5))
    
    min_distance = float('inf')
    closest_coral_feature = None

    for coral_idx in nearest_coral_indices:
        # Use the validated list of shapes
        distance = platform_point.distance(valid_shapes_for_index[coral_idx])
        if distance < min_distance:
            min_distance = distance
            # Find the original feature data that corresponds to this shape
            closest_coral_feature = coral_features[coral_idx]

    if closest_coral_feature:
        story_data = {
            "story_type": "coral_proximity",
            "platform_name": platform['properties'].get('Unit Name', 'Unnamed Platform'),
            "platform_country": platform['properties'].get('Country/Area', 'an unknown location'),
            "platform_coords": platform['geometry']['coordinates'],
            "coral_ecoregion": closest_coral_feature['properties'].get('ECOREGION', 'a sensitive marine area'),
            "distance_km": min_distance * 111.32
        }
        print("  ✅ Analysis Complete: Found a notable proximity event.")
        print(f"     - Platform '{story_data['platform_name']}' is {story_data['distance_km']:.2f} km from a coral reef in the '{story_data['coral_ecoregion']}' ecoregion.")
        return story_data
    else:
        print("  - ❌ Analysis Complete: Could not find a nearby coral reef for the selected platform.")
        return None

def generate_insight_with_ai(story_data, client):
    """
    Builds a prompt based on the analysis and asks the AI to generate the insight.
    """
    print("\n--- Step 3: Generating AI Insight ---")
    
    platform_name = story_data['platform_name']
    platform_country = story_data['platform_country']
    coral_ecoregion = story_data['coral_ecoregion']
    # NEW: Round the distance to one decimal place for a less overly precise figure
    distance_km = round(story_data['distance_km'], 1) 
    platform_coords = story_data['platform_coords']

    # NEW: Updated prompt to use more cautious language
    prompt = f"""You are a science communicator for oceanist.blue. Analyze the following data and produce a JSON object for our insight feed.

Analysis Result: The '{platform_name}' oil and gas platform, in the waters of {platform_country}, was found to be operating approximately {distance_km} km from a coral reef in the '{coral_ecoregion}' ecoregion. The platform is at {platform_coords}.

Based on this, create a JSON object:
- "tag": Use the hashtag #FossilFuels.
- "content": Write a 3-4 sentence analysis. Start by stating the location and the fact. **Use approximate and cautious language (e.g., 'approximately 8.7 km', 'just over 8 km') to reflect the nature of geospatial data.** Then, briefly explain the potential environmental risks that offshore infrastructure poses to nearby fragile ecosystems like coral reefs.
- "map_view": An object with "center": {platform_coords}, "zoom": 8, and "maxZoom": 12.

Return ONLY the raw JSON object and nothing else.
"""
        
    try:
        print(f"  - 🤖 Sending prompt to AI...")
        message = client.messages.create(
            model="claude-sonnet-4-20250514", # Or your preferred model
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

# In run_oilgas_analyzer.py, replace the entire main() function with this:

def main():
    """
    Main function to run the oil & gas analysis process.
    """
    print("\n=============================================")
    print(f"🛢️ Starting Oil & Gas Analyzer at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=============================================")

    event_name = os.getenv('GITHUB_EVENT_NAME')

    if event_name == 'schedule':
        today_weekday = datetime.utcnow().weekday()
        if today_weekday != 4: # Friday is 4
             print(f"🗓️ Today is weekday {today_weekday}, but this job only runs on Fridays (4). Exiting.")
             return
             
    print("🗓️ Running oil & gas analysis (manual run or correct day).")

    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        print("⛔️ FATAL ERROR: AI_API_KEY secret not found.")
        return
    client = anthropic.Anthropic(api_key=api_key)

    print("\n--- Step 1: Fetching Geospatial Data ---")
    platform_data, coral_data = fetch_geospatial_data()
    if not platform_data or not coral_data:
        print("❌ Script finished: Could not retrieve all required data.")
        return

    print("\n--- Step 2: Performing Story Analysis ---")
    story_data = analyze_coral_proximity(platform_data, coral_data)
    if not story_data:
        print("❌ Script finished: No compelling story found in the data analysis.")
        return
        
    insight_data = generate_insight_with_ai(story_data, client)
    if not insight_data:
        print("❌ Script finished: AI failed to generate a valid insight.")
        return
        
    print("\n--- Step 4: Finalizing and Saving Output ---")
    insight_data['date'] = datetime.utcnow().strftime('%Y-%m-%d')
    with open("oilgas_insight.json", 'w') as f:
        json.dump(insight_data, f, indent=2)
    print(f"✅ Successfully saved new insight to 'oilgas_insight.json'.")
    print("\n=============================================")
    print(f"🏁 Oil & Gas Analyzer finished at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=============================================")

if __name__ == "__main__":
    main()
