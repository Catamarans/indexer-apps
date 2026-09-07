import os
import psycopg2
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# Fetch the secure database URL from Render
DB_URL = os.environ.get("DATABASE_URL")

def init_db():
    """Creates the links table when the app starts."""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id SERIAL PRIMARY KEY,
                target_url TEXT NOT NULL,
                status TEXT DEFAULT 'pending'
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("Database connected and table verified.")
    except Exception as e:
        print(f"Database error: {e}")

@app.on_event("startup")
async def startup_event():
    if DB_URL:
        init_db()

@app.get("/feed", response_class=HTMLResponse)
async def discovery_feed():
    """This is the page Googlebot will read."""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        # Only show links that haven't been crawled yet
        cur.execute("SELECT target_url FROM links WHERE status = 'pending' LIMIT 50;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        if not rows:
            return "<html><body><h1>Discovery Feed</h1><p>No URLs to index right now.</p></body></html>"
            
        html = "<html><body><h1>Discovery Feed</h1><ul>"
        for row in rows:
            html += f'<li><a href="{row[0]}">{row[0]}</a></li>'
        html += "</ul></body></html>"
        
        return html
    except Exception as e:
        return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"

@app.get("/", response_class=HTMLResponse)
async def home():
    """The main control panel for adding links."""
    return """
    <html><body>
    <h1>Certs Expert - Indexing Control Panel</h1>
    <form action="/add" method="get">
      <input type="text" name="url" placeholder="Enter backlink URL (e.g., https://...)" style="width:400px;" required>
      <button type="submit">Inject URL</button>
    </form>
    </body></html>
    """

@app.get("/add", response_class=HTMLResponse)
async def add_url(url: str):
    """Inserts the URL into the PostgreSQL database."""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("INSERT INTO links (target_url) VALUES (%s)", (url,))
        conn.commit()
        cur.close()
        conn.close()
        return f"<html><body><h2>Success!</h2><p>Injected {url} into the queue.</p><a href='/'>Add Another</a> | <a href='/feed'>View Discovery Feed</a></body></html>"
    except Exception as e:
        return f"<html><body><h2>Error</h2><p>{str(e)}</p></body></html>"
