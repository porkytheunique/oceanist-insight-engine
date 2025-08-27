import os
import json
from datetime import datetime

# --- Configuration ---
# These are the file names we'll be working with.
CONFIG_FILE = 'config.json'
LOG_FILE = 'published_headlines.log'

def get_keywords_for_today():
    """
    Checks the current day and returns the correct list of keywords from config.json.
    Returns None if it's not a scheduled day.
    """
    # Get the current day as an integer (Monday is 0, Sunday is 6)
    # Note: GitHub Actions run on UTC time.
    today_weekday = datetime.utcnow().weekday()
    
    # Load the keywords from our configuration file
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    print(f"Today is weekday {today_weekday}. (Wednesday is 2, Sunday is 6)")

    # Check if today is a scheduled day and return the appropriate keywords
    if today_weekday == 2: # Wednesday
        print("It's Wednesday, selecting news keywords.")
        return config.get("wednesday_keywords", [])
    elif today_weekday == 6: # Sunday
        print("It's Sunday, selecting news keywords.")
        return config.get("sunday_keywords", [])
    else:
        print("Not a scheduled day for news curation. Exiting.")
        return None

def main():
    """
    Main function to run the news curation process.
    """
    # Retrieve the AI API key securely from GitHub Secrets
    # This is how the script accesses the secret you created.
    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        print("Error: AI_API_KEY secret not found. Please set it in repository settings.")
        return

    # Step 1: Determine which keywords to use based on the day
    keywords = get_keywords_for_today()
    
    # If it's not a scheduled day, the script stops.
    if not keywords:
        return

    print(f"Keywords for today: {keywords}")

    # --- Next steps will go here ---
    # 2. Fetch news from Google News API using these keywords.
    # 3. De-duplicate based on the log file.
    # 4. Use AI to classify and summarize.
    # 5. Save the final output.
    # --------------------------------

if __name__ == "__main__":
    main()
