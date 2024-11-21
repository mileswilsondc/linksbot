from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, timedelta
from rss_feed_handler import refresh_feeds
from models import init_db, get_feeds, add_feed, remove_feed, get_refresh_log
import os

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'your_development_secret_key')

DB_PATH = 'articles.db'

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            pubTime TEXT,
            author TEXT,
            url TEXT UNIQUE,
            classification TEXT DEFAULT NULL
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS refresh_log (
            feed_url TEXT UNIQUE,
            last_refresh TEXT
        )
        """)
    conn.commit()

def parse_pubTime(pubTime):
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S GMT',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S'
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(pubTime, fmt)
            return dt.replace(tzinfo=None)
        except ValueError:
            continue
    raise ValueError(f"time data '{pubTime}' does not match any known format")

def relative_time(dt):
    now = datetime.now()
    diff = now - dt

    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = diff.seconds // 60
        return f"{minutes} min{'s' if minutes > 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} day{'s' if days > 1 else ''} ago"
    else:
        weeks = diff.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"

@app.route('/articles')
def display_articles():
    # Check if 'verbose=true' is in the URL parameters
    verbose = request.args.get('verbose', 'false').lower() == 'true'
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        if verbose:
            # Select all articles, including those marked as 'irrelevant'
            query = """
                SELECT title, pubTime, author, url, classification 
                FROM articles 
            """
            c.execute(query)
        else:
            # Exclude articles with classification 'irrelevant'
            query = """
                SELECT title, pubTime, author, url, classification 
                FROM articles 
                WHERE classification != 'irrelevant' OR classification IS NULL
            """
            c.execute(query)
        
        articles = c.fetchall()
        # Convert each row to a dictionary and modify pubTime
        articles = [dict(article) for article in articles]
        for article in articles:
            article['pubTime'] = relative_time(parse_pubTime(article['pubTime']))
    
    return render_template('articles.html', articles=articles, verbose=verbose)

@app.route('/refresh', methods=['GET', 'POST'])
def refresh():
    if request.method == 'POST':
        refresh_feeds(DB_PATH)
        flash('Feeds have been refreshed!', 'success')
        return redirect(url_for('refresh'))

    logs = get_refresh_log()

    # Process logs to include relative times
    processed_logs = []
    for log in logs:
        feed_url = log[0]
        last_refresh_str = log[1]

        # Parse the last_refresh_str into a datetime object
        last_refresh_dt = datetime.fromisoformat(last_refresh_str)
        relative_last_refresh = relative_time(last_refresh_dt)

        # Append the processed log
        processed_logs.append((feed_url, relative_last_refresh))

    return render_template('refresh_log.html', logs=processed_logs)

@app.route('/refresh_feed', methods=['POST'])
def refresh_feed():
    feed_url = request.form.get('feed_url')
    if feed_url:
        refresh_feeds(DB_PATH, feed_url)
        flash(f'Feed {feed_url} has been refreshed!', 'success')
    else:
        flash('No feed URL provided.', 'error')
    return redirect(url_for('refresh'))

@app.route('/classify', methods=['GET', 'POST'])
def classify():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT id, title, author, url
            FROM articles
            WHERE classification IS NULL
            ORDER BY pubTime ASC LIMIT 1
        """)
        article = c.fetchone()
        
        # Fetch the count of unclassified articles
        c.execute("SELECT COUNT(*) FROM articles WHERE classification IS NULL")
        unclassified_count = c.fetchone()[0]
        
    if request.method == 'POST':
        classification = request.form.get('classification')
        article_id = request.form.get('article_id')
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("UPDATE articles SET classification = ? WHERE id = ?", (classification, article_id))
            conn.commit()
        return redirect(url_for('classify'))
    return render_template('classify.html', article=article, unclassified_count=unclassified_count)

@app.route('/feeds', methods=['GET', 'POST'])
def manage_feeds():
    if request.method == 'POST':
        action = request.form.get('action')
        feed_url = request.form.get('feed_url', '').strip()
        
        if action == 'add':
            if add_feed(feed_url):
                flash('Feed added successfully!', 'success')
            else:
                flash('Feed already exists or invalid URL.', 'danger')
        elif action == 'remove':
            remove_feed(feed_url)
            flash('Feed removed successfully!', 'success')
        elif action == 'refresh_all':
            refresh_feeds(DB_PATH)
            flash('Feeds have been refreshed!', 'success')
        elif action == 'refresh_feed':
            if feed_url:
                refresh_feeds(DB_PATH, feed_url)
                flash(f'Feed {feed_url} has been refreshed!', 'success')
            else:
                flash('No feed URL provided.', 'error')
        return redirect(url_for('manage_feeds'))

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            SELECT feeds.feed_url, refresh_log.last_refresh
            FROM feeds
            LEFT JOIN refresh_log ON feeds.feed_url = refresh_log.feed_url
        """)
        feeds = c.fetchall()

    processed_feeds = []
    for feed in feeds:
        feed_url = feed[0]
        last_refresh_str = feed[1]
        if last_refresh_str:
            last_refresh_dt = datetime.fromisoformat(last_refresh_str)
            relative_last_refresh = relative_time(last_refresh_dt)
        else:
            relative_last_refresh = 'Never'
        processed_feeds.append({'feed_url': feed_url, 'last_refresh': relative_last_refresh})
    return render_template('manage_feeds.html', feeds=processed_feeds)

@app.route('/')
def index():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT title, url FROM articles ORDER BY pubTime DESC LIMIT 6")
        articles = c.fetchall()
    return render_template('index.html', articles=articles)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
