import feedparser
import sqlite3
from datetime import datetime
from models import get_feeds

def fetch_feed(feed_url):
    articles = []
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        articles.append({
            'title': entry.title,
            'pubTime': entry.published if 'published' in entry else datetime.now().isoformat(),
            'author': entry.author if 'author' in entry else 'Unknown',
            'url': entry.link
        })
    return articles

def refresh_feeds(db_path, feed_url=None):
    if feed_url:
        feed_urls = [feed_url]
    else:
        feed_urls = get_feeds()
    
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        for feed_url in feed_urls:
            articles = fetch_feed(feed_url)
            for article in articles:
                try:
                    c.execute("""
                        INSERT INTO articles (title, pubTime, author, url)
                        VALUES (?, ?, ?, ?)
                    """, (article['title'], article['pubTime'], article['author'], article['url']))
                except sqlite3.IntegrityError:
                    pass  # Skip duplicates
            c.execute("""
                INSERT OR REPLACE INTO refresh_log (feed_url, last_refresh)
                VALUES (?, ?)
            """, (feed_url, datetime.now().isoformat()))
        conn.commit()
