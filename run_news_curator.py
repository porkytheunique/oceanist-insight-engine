import os
import json
import requests
import feedparser
import anthropic
from datetime import datetime
from urllib.parse import quote_plus

# --- Configuration ---
OUTPUT_FILE = 'news_insight.json'
SERVER_LOG_URL = 'https://www.oceanist.blue/map-data/news_insight.json'
CONFIG_FILE = 'config.json'

def get_keywords_for_today():
    event_name = os.getenv('GITHUB_EVENT_NAME')
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    if event_name == 'workflow_dispatch':
        print("✅ Manual run detected, bypassing date check.", flush=True)
        return config.get("wednesday_keywords", [])
    today_weekday = datetime.utcnow().weekday()
    print(f"🗓️ Today's UTC weekday is {today_weekday}. (Wednesday is 2, Sunday is 6)", flush=True)
    if today_weekday == 2 or today_weekday == 6:
        print(f"✅ It's a scheduled day, selecting news keywords.", flush=True)
        return config.get("wednesday_keywords", [])
    else:
        print("❌ Not a scheduled day for news curation.", flush=True)
        return None

def fetch_news_articles(keywords):
    query = f'({" OR ".join(keywords)}) AND ("study" OR "research" OR "report")'
    encoded_query = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&when=2d&hl=en-US&gl=US&ceid=US:en"
    print(f"🔎 Fetching news from RSS feed URL...", flush=True)
    try:
        response = requests.get(url)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        entries = feed.get('entries', [])[:5]
        print(f"📰 Found {len(entries)} potential articles.", flush=True)
        return entries
    except Exception as e:
        print(f"❌ Failed to fetch RSS feed: {e}", flush=True)
        return []

def find_unique_article(articles, existing_insights):
    print("\n--- Starting De-duplication Process ---", flush=True)
    published_urls = {item.get('source_url') for item in existing_insights}
    print(f"📚 Checking against {len(published_urls)} previously published URLs.", flush=True)
    for article in articles:
        if article.link in published_urls:
            print(f"  - DUPLICATE: '{article.title}'", flush=True)
            continue
        print(f"✅ Unique article found: '{article.title}'", flush=True)
        return article
    print("❌ No unique articles found.", flush=True)
    return None

def is_article_relevant(article, client):
    print("🤖 Step 4.1: Asking AI to classify article relevance...", flush=True)
    prompt = f"Is an article with the title '{article.title}' and summary '{article.summary}' relevant to marine conservation, ocean science, or environmental policy? Answer only YES or NO."
    try:
        message = client.messages.create(model="claude-3-haiku-20240307", max_tokens=5, messages=[{"role": "user", "content": prompt}]).content[0].text
        print(f"   - AI Relevance Check Response: '{message.strip()}'", flush=True)
        return "YES" in message.upper()
    except Exception as e:
        print(f"❌ AI classification failed: {e}", flush=True)
        return False

def summarize_article_with_ai(article, client):
    print("🤖 Step 4.2: Asking AI to summarize and structure the article...", flush=True)
    prompt = f"""You are an expert science communicator. Analyze the news article below and create a JSON object.

Article Title: {article.title}
Article Link: {article.link}
Article Summary: {article.summary}

Create a JSON object with the following structure:
- "tag": A single, relevant hashtag (#CoralReefs, #MPAs, #Policy, #Plastic, #Conservation).
- "content": A 3-4 sentence summary. **If the article mentions a specific place (e.g., 'Nha Trang Bay'), you MUST include its name in the summary.** Be specific.
- "map_view": An object with "center" (lat, lon), "zoom", and "maxZoom". Provide coordinates for the specific location. If global, use center [0, 0] and zoom 2.

Return ONLY the raw JSON object.
"""
    try:
        message = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role": "user", "content": prompt}]).content[0].text
        print("   - AI Summary Response (raw):", flush=True); print(message, flush=True)
        return json.loads(message.strip().lstrip("```json").rstrip("```"))
    except Exception as e:
        print(f"❌ AI summarization failed: {e}", flush=True)
        return None

def main():
    print("\n=============================================", flush=True)
    print(f"🚀 Starting News Curator at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
    print("=============================================", flush=True)
    
    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        print("⛔️ FATAL ERROR: AI_API_KEY secret not found.", flush=True); return
    client = anthropic.Anthropic(api_key=api_key)

    print("\n--- Step 1: Checking Schedule and Keywords ---", flush=True)
    keywords = get_keywords_for_today()
    if not keywords: return

    print("\n--- Step 2: Fetching Existing Insights & News Articles ---", flush=True)
    all_insights = []
    try:
        res = requests.get(SERVER_LOG_URL)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list): all_insights = data
            elif isinstance(data, dict): all_insights = [data]
            print(f"✅ Successfully loaded existing log with {len(all_insights)} insights.", flush=True)
    except Exception as e:
        print(f"⚠️ Could not load existing log, will create a new one. Reason: {e}", flush=True)
    
    articles = fetch_news_articles(keywords)
    if not articles: return

    print("\n--- Step 3: Finding a Unique Article ---", flush=True)
    unique_article = find_unique_article(articles, all_insights)
    if not unique_article: return

    print("\n--- Step 4: AI Processing ---", flush=True)
    if not is_article_relevant(unique_article, client):
        print("❌ Article deemed not relevant by AI. Exiting.", flush=True); return
        
    insight_data = summarize_article_with_ai(unique_article, client)
    if not insight_data:
        print("❌ AI failed to generate a valid summary. Exiting.", flush=True); return

    print("\n--- Step 5: Finalizing and Archiving Output ---", flush=True)
    insight_data['date'] = datetime.utcnow().strftime('%Y-%m-%d')
    insight_data['source_headline'] = unique_article.title
    insight_data['source_url'] = unique_article.link
    
    all_insights.insert(0, insight_data)
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_insights, f, indent=2)
    print(f"✅ Saved updated log with {len(all_insights)} total insights to '{OUTPUT_FILE}'.", flush=True)
    
    print("\n=============================================", flush=True)
    print(f"🏁 News Curator finished at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", flush=True)
    print("=============================================", flush=True)

if __name__ == "__main__":
    main()
