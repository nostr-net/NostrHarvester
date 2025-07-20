from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

def mount_static_files(app: FastAPI):
    """Mount static files to serve the web interface"""
    static_dir = "/app/web"
    
    # Serve index.html at root
    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(static_dir, "index.html"))
    
    # Serve static files
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")