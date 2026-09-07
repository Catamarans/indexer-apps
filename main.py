from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/feed", response_class=HTMLResponse)
async def discovery_feed():
    return "<html><body><h1>Discovery Feed</h1><p>Waiting for database connection...</p></body></html>"