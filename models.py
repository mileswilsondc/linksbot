import sqlite3
from datetime import datetime

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
        c.execute("""
        CREATE TABLE IF NOT EXISTS feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_url TEXT UNIQUE
        )
        """)
    conn.commit()

def get_feeds():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT feed_url FROM feeds")
        feeds = [row[0] for row in c.fetchall()]
    return feeds

def add_feed(feed_url):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO feeds (feed_url) VALUES (?)", (feed_url,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Feed already exists

def remove_feed(feed_url):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM feeds WHERE feed_url = ?", (feed_url,))
        conn.commit()

def get_refresh_log():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT feed_url, last_refresh FROM refresh_log ORDER BY last_refresh DESC")
        logs = c.fetchall()
    return logs
