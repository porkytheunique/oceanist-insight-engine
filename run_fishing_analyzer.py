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
                    "
