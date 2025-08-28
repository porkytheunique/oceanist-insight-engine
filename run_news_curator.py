import os
import json
import requests
import feedparser
import anthropic
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import quote_plus

# --- Configuration ---
CONFIG_FILE = 'config.json'
LOG_FILE = 'published_headlines.log'
OUTPUT_FILE = 'news_insight.json'
SIMILARITY_THRESHOLD = 0.9

def get_keywords_for_today():
    event_name = os.getenv('GITHUB_EVENT_NAME')
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    if event_name == 'workflow_dispatch':
        print("✅ Manual run detected, bypassing date check.", flush=True)
        return config.get("wednesday_keywords", [])
    today_weekday = datetime.utcnow().weekday()
    print(f"🗓️ Today's UTC weekday is {today_weekday}. (Wednesday is 2, Sunday is 6)", flush=True)
    if today_weekday == 2:
        print("✅ It's Wednesday, selecting news keywords.", flush=True)
        return config.get("wednesday_keywords", [])
    elif today_weekday == 6:
        print("✅ It's Sunday, selecting news keywords.", flush=True)
        return config.get("sunday_keywords", [])
    else:
        print("❌ Not a scheduled day for news curation.", flush=True)
        return None

def fetch_news_articles(keywords):
    query = f'({" OR ".join(keywords)}) AND ("study" OR "research" OR "report")'
    encoded_query = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&when=2d&hl=en-US&gl=US&ceid=US:en"
    print(f"🔎 Fetching news from RSS feed URL...", flush=True)
    response = requests.get(url)
    if response.status_code != 200:
        print(f"❌ Failed to fetch RSS feed. Status code: {response.status_code}", flush=True)
        return []
    feed = feedparser.parse(response.content)
    entries = feed.get('entries', [])[:5]
    print(f"📰 Found {len(entries)} potential articles in the top 5 results.", flush=True)
    return entries

def find_unique_article(articles):
    print("\n--- Starting De-duplication Process ---", flush=True)
    try:
        with open(LOG_FILE, 'r') as f:
            previous_headlines = [line.strip() for line in f.readlines()]
    except FileNotFoundError:
        previous_headlines = []
    print(f"📚 Checking against {len(previous_headlines)} previously published headlines in '{LOG_FILE}'.", flush=True)
    for article in articles:
        title_to_check = article.title
        is_duplicate = False
        for prev_headline in previous_headlines:
            similarity = SequenceMatcher(None, title_to_check, prev_headline).ratio()
            if similarity > SIMILARITY_THRESHOLD:
                print(f"  - DUPLICATE (similarity: {similarity:.2f}): '{title_to_check}'", flush=True)
                is_duplicate = True
                break
        if not is_duplicate:
            print(f"✅ Unique article found: '{title_to_check}'", flush=True)
            print("--- De-duplication Finished ---", flush=True)
            return article
    print("❌ No unique articles were found in the latest search results.", flush=True)
    print("--- De-duplication Finished ---", flush=True)
    return None

def is_article_relevant(article_title, article_summary, client):
    print("🤖 Step 4.1: Asking AI to classify article relevance...", flush=True)
    prompt = f"You are a marine science news editor. Is an article with the title '{article_title}' and summary '{article_summary}' relevant to marine conservation, ocean science, or environmental policy? Answer only with YES or NO."
    try:
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=5,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text
        print(f"   - AI Relevance Check Response: '{message.strip()}'", flush=True)
        return "YES" in message.upper()
    except Exception as e:
        print(f"❌ AI classification failed: {e}", flush=True)
        return False

def summarize_article_with_ai(article, client):
    print("🤖 Step 4.2: Asking AI to summarize and structure the article...", flush=True)
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
            model="claude-sonnet-4-20250514", # Your preferred model
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text
        print("   - AI Summary Response (raw):", flush=True)
        print(message, flush=True)
        json_response = message.strip().lstrip("```json").rstrip("```")
        return json.loads(json_response)
    except Exception as e:
        print(f"❌ AI summarization failed: {e}", flush=True)
        return None

# In run_news_curator.py, replace the entire main() function with this:

def main():
    print("\n=============================================", flush=True)
    print(f"🚀 Starting News Curator at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
    print("=============================================", flush=True)
    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        print("⛔️ FATAL ERROR: AI_API_KEY secret not found.", flush=True)
        return
    client = anthropic.Anthropic(api_key=api_key)

    print("\n--- Step 1: Checking Schedule and Keywords ---", flush=True)
    keywords = get_keywords_for_today()
    if not keywords:
        return

    print("\n--- Step 2: Fetching News Articles ---", flush=True)
    articles = fetch_news_articles(keywords)
    if not articles:
        return

    print("\n--- Step 3: Finding a Unique Article ---", flush=True)
    unique_article = find_unique_article(articles)
    if not unique_article:
        return

    print("\n--- Step 4: AI Processing ---", flush=True)
    if not is_article_relevant(unique_article.title, unique_article.summary, client):
        print("❌ Article deemed not relevant by AI. Exiting.", flush=True)
        return
        
    insight_data = summarize_article_with_ai(unique_article, client)
    if not insight_data:
        print("❌ AI failed to generate a valid summary. Exiting.", flush=True)
        return

    # In main() for run_news_curator.py
    print("\n--- Step 5: Finalizing and Saving Output ---", flush=True)
    insight_data['date'] = datetime.utcnow().strftime('%Y-%m-%d')
    insight_data['source_headline'] = unique_article.title
    insight_data['source_url'] = unique_article.link
    
    with open("news_insight.json", 'w') as f:
        json.dump(insight_data, f, indent=2)
    print(f"✅ Successfully saved new insight to 'news_insight.json'.", flush=True)
    
    with open(LOG_FILE, 'a') as f:
        f.write(insight_data['source_headline'] + '\n')
    print(f"✍️  Added '{insight_data['source_headline']}' to the de-duplication log.", flush=True)

    print("\n=============================================", flush=True)
    print(f"🏁 News Curator finished at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
    print("=============================================", flush=True)

if __name__ == "__main__":
    main()
