import os
import json
import psycopg2
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from google.oauth2 import service_account
import google.auth.transport.requests

app = FastAPI()
DB_URL = os.environ.get("DATABASE_URL")
GOOGLE_JSON_STR = os.environ.get("GOOGLE_JSON")

def init_db():
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
    except Exception as e:
        print(f"Database error: {e}")

@app.on_event("startup")
async def startup_event():
    if DB_URL:
        init_db()

@app.get("/feed", response_class=HTMLResponse)
async def discovery_feed():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
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
    return """
    <html><body style="font-family: Arial, sans-serif; padding: 20px;">
    <h1>Certs Expert - Indexing Control Panel</h1>
    <form action="/add" method="get">
      <input type="text" name="url" placeholder="Enter backlink URL (e.g., https://...)" style="width:400px; padding: 8px;" required>
      <button type="submit" style="padding: 8px 15px; background: #007bff; color: white; border: none; cursor: pointer;">Inject URL & Ping Google</button>
    </form>
    </body></html>
    """

@app.get("/add", response_class=HTMLResponse)
async def add_url(url: str):
    try:
        # 1. Insert URL into Database
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("INSERT INTO links (target_url) VALUES (%s)", (url,))
        conn.commit()
        cur.close()
        conn.close()
        
        # 2. Instantly Ping Google Indexing API
        feed_url = "https://indexer-apps.onrender.com/feed"
        api_result = "Ping failed to execute."
        
        if not GOOGLE_JSON_STR:
            api_result = "Error: GOOGLE_JSON is missing from Render Environment."
        else:
            creds_info = json.loads(GOOGLE_JSON_STR)
            credentials = service_account.Credentials.from_service_account_info(
                creds_info, scopes=["https://www.googleapis.com/auth/indexing"]
            )
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            
            endpoint = "https://indexing.googleapis.com/v3/urlNotifications:publish"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {credentials.token}"
            }
            payload = {
                "url": feed_url,
                "type": "URL_UPDATED"
            }
            response = requests.post(endpoint, json=payload, headers=headers)
            api_result = f"Status Code: {response.status_code} <br> Response: {response.text}"
            
        return f"""
        <html><body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: green;">Success!</h2>
            <p>Injected <b>{url}</b> into the queue.</p>
            <div style="background: #f4f4f4; padding: 15px; border-left: 4px solid #007bff; margin-top: 20px;">
                <h3 style="margin-top: 0;">Google API Response:</h3>
                <p style="font-family: monospace;">{api_result}</p>
            </div>
            <br>
            <a href='/'>Add Another</a> | <a href='/feed' target="_blank">View Discovery Feed</a>
        </body></html>
        """
    except Exception as e:
        return f"<html><body><h2>Error</h2><p>{str(e)}</p></body></html>"
