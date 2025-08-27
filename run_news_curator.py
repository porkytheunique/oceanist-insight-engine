import os
import json
from datetime import datetime
from pygooglenews import GoogleNews
from difflib import SequenceMatcher

# --- Configuration ---
CONFIG_FILE = 'config.json'
LOG_FILE = 'published_headlines.log'
SIMILARITY_THRESHOLD = 0.9

def get_keywords_for_today():
    """
    Checks the current day and returns the correct list of keywords from config.json.
    """
    today_weekday = datetime.utcnow().weekday()
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    print(f"🗓️ Today's UTC weekday is {today_weekday}. (Wednesday is 2, Sunday is 6)")
    if today_weekday == 2:
        print("✅ It's Wednesday, selecting news keywords.")
        return config.get("wednesday_keywords", [])
    elif today_weekday == 6:
        print("✅ It's Sunday, selecting news keywords.")
        return config.get("sunday_keywords", [])
    else:
        print("❌ Not a scheduled day for news curation.")
        return None

def fetch_news_articles(keywords):
    """
    Fetches news articles from the last 48 hours using the given keywords.
    """
    gn = GoogleNews()
    query = f'({" OR ".join(keywords)}) AND ("study" OR "research" OR "report")'
    print(f"🔎 Searching for news with query: {query}")
    search_results = gn.search(query, when='2d')
    entries = search_results.get('entries', [])[:5]
    print(f"📰 Found {len(entries)} potential articles in the top 5 results.")
    return entries

def find_unique_article(articles):
    """
    Finds the first article that has not been published before.
    """
    print("\n--- Starting De-duplication Process ---")
    try:
        with open(LOG_FILE, 'r') as f:
            previous_headlines = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        previous_headlines = []

    print(f"📚 Checking against {len(previous_headlines)} previously published headlines in '{LOG_FILE}'.")
    
    for article in articles:
        is_duplicate = False
        for prev_headline in previous_headlines:
            similarity = SequenceMatcher(None, article.title, prev_headline).ratio()
            if similarity > SIMILARITY_THRESHOLD:
                print(f"  - DUPLICATE (similarity: {similarity:.2f}): '{article.title}'")
                is_duplicate = True
                break
        
        if not is_duplicate:
            print(f"✅ Unique article found: '{article.title}'")
            print("--- De-duplication Finished ---")
            return article

    print("❌ No unique articles were found in the latest search results.")
    print("--- De-duplication Finished ---")
    return None

def main():
    """
    Main function to run the news curation process.
    """
    print("\n=============================================")
    print(f"🚀 Starting News Curator at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=============================================")

    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        print("⛔️ FATAL ERROR: AI_API_KEY secret not found.")
        return

    print("\n--- Step 1: Checking Schedule and Keywords ---")
    keywords = get_keywords_for_today()
    if not keywords:
        print("✅ Script finished: Not a scheduled day.")
        return
    print(f"🔑 Keywords for today: {keywords}")

    print("\n--- Step 2: Fetching News Articles ---")
    articles = fetch_news_articles(keywords)
    if not articles:
        print("✅ Script finished: No articles found for the given keywords.")
        return

    print("\n--- Step 3: Finding a Unique Article ---")
    unique_article = find_unique_article(articles)
    if not unique_article:
        print("✅ Script finished: No unique article to process.")
        return
        
    print("\n--- Step 4: AI Processing (Placeholder) ---")
    print("🤖 AI processing would happen here...")
    print(f"   - Article to process: '{unique_article.title}'")
    print("   - Link: {unique_article.link}")

    print("\n=============================================")
    print(f"🏁 News Curator finished at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=============================================")

if __name__ == "__main__":
    main()
