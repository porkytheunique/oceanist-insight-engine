import os
import json
import requests
from datetime import datetime

# --- Configuration ---
FISHING_DATA_URL = "https://porkytheunique.github.io/ocean-map-data/fishing_events.geojson"
MPA_DATA_URL = "https://porkytheunique.github.io/ocean-map-data/WDPA.json"
OUTPUT_FILE = 'latest_insight.json' # This will be our output file

def fetch_geospatial_data():
    """
    Downloads the fishing and MPA GeoJSON data from their URLs.
    """
    print("🌎 Fetching geospatial data...")
    try:
        print(f"  - Downloading fishing data from {FISHING_DATA_URL}...")
        fishing_response = requests.get(FISHING_DATA_URL)
        fishing_response.raise_for_status()  # Will raise an error for bad status codes
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
        # Even if MPAs fail, we might still be able to do a hotspot analysis
        return fishing_data, None

    return fishing_data, mpa_data

def main():
    """
    Main function to run the fishing analysis process.
    """
    print("\n=============================================")
    print(f"🎣 Starting Fishing Analyzer at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=============================================")

    # --- Step 1: Check if it's Monday ---
    # We'll add this check later when updating the workflow file.
    # For now, we'll let it run any day for testing.
    print("🗓️ Running scheduled fishing analysis.")
    
    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        print("⛔️ FATAL ERROR: AI_API_KEY secret not found.")
        return

    # --- Step 2: Fetch the required data ---
    fishing_data, mpa_data = fetch_geospatial_data()
    
    if not fishing_data:
        print("❌ Script finished: Could not retrieve fishing data.")
        return

    # --- Next steps will go here ---
    # 3. Implement the "Story Roulette" to pick an analysis type.
    # 4. Perform the chosen analysis (e.g., find hotspot).
    # 5. Build a prompt for the AI.
    # 6. Call the AI and save the output.
    # --------------------------------

    print("\n--- Step 3: Story Analysis (Placeholder) ---")
    print("⚙️ Data is loaded. Analysis logic will go here.")


    print("\n=============================================")
    print(f"🏁 Fishing Analyzer finished at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=============================================")

if __name__ == "__main__":
    main()
