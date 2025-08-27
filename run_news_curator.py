import os
import json
import requests
import feedparser
import anthropic # New library for Claude
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import quote_plus

# --- Configuration ---
CONFIG_FILE = 'config.json'
LOG_FILE = 'published_headlines.log'
OUTPUT_FILE = 'latest_insight.json' # Define the output file name
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
    Fetches news articles directly from Google's RSS feed.
    """
    query = f'({" OR ".join(keywords)}) AND ("study" OR "research" OR "report")'
    encoded_query = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&when=2d&hl=en-US&gl=US&ceid=US:en"
    print(f"🔎 Fetching news from RSS feed URL...")
    response = requests.get(url)
    if response.status_code != 200:
        print(f"❌ Failed to fetch RSS feed. Status code: {response.status_code}")
        return []
    feed = feedparser.parse(response.content)
    entries = feed.get('entries', [])[:5]
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
        title_to_check = article.title
        is_duplicate = False
        for prev_headline in previous_headlines:
            similarity = SequenceMatcher(None, title_to_check, prev_headline).ratio()
            if similarity > SIMILARITY_THRESHOLD:
                print(f"  - DUPLICATE (similarity: {similarity:.2f}): '{title_to_check}'")
                is_duplicate = True
                break
        if not is_duplicate:
            print(f"✅ Unique article found: '{title_to_check}'")
            print("--- De-duplication Finished ---")
            return article
    print("❌ No unique articles were found in the latest search results.")
    print("--- De-duplication Finished ---")
    return None

# --- NEW AI FUNCTIONS ---
def is_article_relevant(article_title, article_summary, client):
    """
    Uses a fast AI model to quickly classify if an article is relevant.
    """
    print("🤖 Step 4.1: Asking AI to classify article relevance...")
    prompt = f"You are a marine science news editor. Is an article with the title '{article_title}' and summary '{article_summary}' relevant to marine conservation, ocean science, or environmental policy? Answer only with YES or NO."
    try:
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=5,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text
        
        print(f"   - AI Relevance Check Response: '{message.strip()}'")
        return "YES" in message.upper()
    except Exception as e:
        print(f"❌ AI classification failed: {e}")
        return False

def summarize_article_with_ai(article, client):
    """
    Uses a powerful AI model to summarize the article and extract data.
    """
    print("🤖 Step 4.2: Asking AI to summarize and structure the article...")
    # We use article.summary which comes from the RSS feed as context
    prompt = f"""You are an expert science communicator for the website oceanist.blue. Your task is to analyze the following news article and produce a JSON object for our 'Human Impact Map' insight feed.

Article Title: {article.title}
Article Link: {article.link}
Article Summary: {article.summary}

Based on the information, create a JSON object with the following structure:
- "tag": A single, relevant hashtag from this list: #CoralReefs, #MPAs, #Policy, #Plastic, #Conservation.
- "content": A 3-4 sentence summary of the key findings or news, written in an engaging and informative tone for a general audience.
- "map_view": An object with "center" (lat, lon), "zoom" (integer), and "maxZoom" (integer). If a specific location is central to the article (e.g., a specific country's reef), provide its approximate coordinates and a suitable zoom level. If the topic is global or lacks a specific location, use center [0, 0] and zoom 2.

Return ONLY the raw JSON object and nothing else.
"""
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620", # Using the more powerful model for quality output
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text
        
        print("   - AI Summary Response (raw):")
        print(message)
        # Clean up the response to ensure it's valid JSON
        json_response = message.strip().lstrip("```json").rstrip("```")
        return json.loads(json_response)
    except Exception as e:
        print(f"❌ AI summarization failed: {e}")
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

    # Initialize the AI client
    client = anthropic.Anthropic(api_key=api_key)

    print("\n--- Step 1: Checking Schedule and Keywords ---")
    keywords = get_keywords_for_today()
    if not keywords:
        print("✅ Script finished: Not a scheduled day.")
        return
    print(f"🔑 Keywords for today: {keywords}")

    print("\n--- Step 2: Fetching News Articles ---")
    articles = fetch_news_articles(keywords)
    if not articles:
        print("✅ Script finished: No articles found.")
        return

    print("\n--- Step 3: Finding a Unique Article ---")
    unique_article = find_unique_article(articles)
    if not unique_article:
        print("✅ Script finished: No unique article to process.")
        return

    # --- REPLACED PLACEHOLDER WITH AI LOGIC ---
    print("\n--- Step 4: AI Processing ---")
    # First, a quick, cheap check if the article is relevant.
    if not is_article_relevant(unique_article.title, unique_article.summary, client):
        print("❌ Article deemed not relevant by AI. Exiting.")
        return

    # If relevant, proceed with the full summarization.
    insight_data = summarize_article_with_ai(unique_article, client)
    
    if not insight_data:
        print("❌ AI failed to generate a valid summary. Exiting.")
        return

    print("\n--- Step 5: Finalizing and Saving Output ---")
    # Add the static and source data to our AI-generated object
    insight_data['date'] = datetime.utcnow().strftime('%Y-%m-%d')
    insight_data['source_headline'] = unique_article.title
    insight_data['source_url'] = unique_article.link
    
    # Save the final JSON object to a file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(insight_data, f, indent=2)
    print(f"✅ Successfully saved new insight to '{OUTPUT_FILE}'.")
    
    # Finally, add the headline to our log to prevent future duplicates
    with open(LOG_FILE, 'a') as f:
        f.write(unique_article.title + '\n')
    print(f"✍️  Added '{unique_article.title}' to the log file.")

    print("\n=============================================")
    print(f"🏁 News Curator finished at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=============================================")

if __name__ == "__main__":
    main()
