import os
import json
from datetime import datetime
from pygooglenews import GoogleNews
from difflib import SequenceMatcher # New import for comparing strings

# --- Configuration ---
CONFIG_FILE = 'config.json'
LOG_FILE = 'published_headlines.log'
SIMILARITY_THRESHOLD = 0.9 # Headlines must be less than 90% similar to be unique

def get_keywords_for_today():
    """
    Checks the current day and returns the correct list of keywords from config.json.
    """
    today_weekday = datetime.utcnow().weekday()
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    print(f"Today is weekday {today_weekday}. (Wednesday is 2, Sunday is 6)")
    if today_weekday == 2:
        print("It's Wednesday, selecting news keywords.")
        return config.get("wednesday_keywords", [])
    elif today_weekday == 6:
        print("It's Sunday, selecting news keywords.")
        return config.get("sunday_keywords", [])
    else:
        print("Not a scheduled day for news curation. Exiting.")
        return None

def fetch_news_articles(keywords):
    """
    Fetches news articles from the last 48 hours using the given keywords.
    """
    gn = GoogleNews()
    query = f'({" OR ".join(keywords)}) AND ("study" OR "research" OR "report")'
    print(f"Searching with query: {query}")
    search_results = gn.search(query, when='2d')
    entries = search_results.get('entries', [])[:5]
    print(f"Found {len(entries)} potential articles.")
    return entries

# --- NEW FUNCTION ---
def find_unique_article(articles):
    """
    Finds the first article that has not been published before.
    """
    try:
        with open(LOG_FILE, 'r') as f:
            # Read all previous headlines, stripping any whitespace
            previous_headlines = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        # If the log file doesn't exist, this is our first run.
        previous_headlines = []

    print(f"Checking against {len(previous_headlines)} previously published headlines.")
    
    for article in articles:
        is_duplicate = False
        for prev_headline in previous_headlines:
            # Check how similar the new headline is to the old one
            similarity = SequenceMatcher(None, article.title, prev_headline).ratio()
            if similarity > SIMILARITY_THRESHOLD:
                print(f"Found duplicate (similarity: {similarity:.2f}): '{article.title}'")
                is_duplicate = True
                break # Move to the next new article
        
        if not is_duplicate:
            print(f"Found a unique article: '{article.title}'")
            return article # This is the one we'll use

    print("No unique articles found in the top results.")
    return None

def main():
    """
    Main function to run the news curation process.
    """
    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        print("Error: AI_API_KEY secret not found.")
        return

    keywords = get_keywords_for_today()
    if not keywords:
        return
    print(f"Keywords for today: {keywords}")
    
    articles = fetch_news_articles(keywords)
    if not articles:
        print("No articles found for the given keywords. Exiting.")
        return

    # --- NEW SECTION ---
    # Step 3: Find the first unique article to process
    unique_article = find_unique_article(articles)

    if not unique_article:
        print("No unique article to process. Exiting.")
        return
        
    # --- Next steps will go here ---
    # 4. Use AI to classify and summarize unique_article.
    # 5. Save the final output.
    # --------------------------------

if __name__ == "__main__":
    main()
