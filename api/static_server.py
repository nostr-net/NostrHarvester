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
    
    # Serve app.js explicitly
    @app.get("/app.js")
    async def serve_app_js():
        return FileResponse(os.path.join(static_dir, "app.js"))
    
    # Don't mount static files on "/" as it catches all routes including /api/*