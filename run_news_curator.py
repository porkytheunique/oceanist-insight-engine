import os
import json
from datetime import datetime
from pygooglenews import GoogleNews # Import the new library

# --- Configuration ---
CONFIG_FILE = 'config.json'
LOG_FILE = 'published_headlines.log'

def get_keywords_for_today():
    """
    Checks the current day and returns the correct list of keywords from config.json.
    Returns None if it's not a scheduled day.
    """
    today_weekday = datetime.utcnow().weekday()
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

    print(f"Today is weekday {today_weekday}. (Wednesday is 2, Sunday is 6)")
    
    if today_weekday == 2: # Wednesday
        print("It's Wednesday, selecting news keywords.")
        return config.get("wednesday_keywords", [])
    elif today_weekday == 6: # Sunday
        print("It's Sunday, selecting news keywords.")
        return config.get("sunday_keywords", [])
    else:
        print("Not a scheduled day for news curation. Exiting.")
        return None

# --- NEW FUNCTION ---
def fetch_news_articles(keywords):
    """
    Fetches news articles from the last 48 hours using the given keywords.
    """
    gn = GoogleNews()
    
    # We combine the keywords with OR for a broader search
    # and add terms to focus on scientific/policy news.
    query = f'({" OR ".join(keywords)}) AND ("study" OR "research" OR "report")'
    print(f"Searching with query: {query}")
    
    # Search for news from the last 2 days ('2d')
    search_results = gn.search(query, when='2d')
    
    # We only need the top 5 most relevant articles to check
    entries = search_results.get('entries', [])[:5]
    print(f"Found {len(entries)} articles to check.")
    
    return entries

def main():
    """
    Main function to run the news curation process.
    """
    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        print("Error: AI_API_KEY secret not found. Please set it in repository settings.")
        return

    keywords = get_keywords_for_today()
    if not keywords:
        return
    print(f"Keywords for today: {keywords}")

    # --- NEW SECTION ---
    # Step 2: Fetch a list of potential articles
    articles = fetch_news_articles(keywords)
    if not articles:
        print("No articles found for the given keywords. Exiting.")
        return

    # --- Next steps will go here ---
    # 3. De-duplicate based on the log file.
    # 4. Use AI to classify and summarize.
    # 5. Save the final output.
    # --------------------------------
    
    # For now, let's just print the titles of the articles we found
    for article in articles:
        print(f"- Found article: {article.title}")


if __name__ == "__main__":
    main()
