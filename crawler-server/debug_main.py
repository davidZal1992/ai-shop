"""
Debug entry point for VS Code debugging
Run this file or use the VS Code debug configuration
"""
import uvicorn

if __name__ == "__main__":
    print("🐛 Starting Crawler Server in DEBUG mode...")
    print("📍 Server: http://localhost:8000")
    print("📖 API docs: http://localhost:8000/docs")
    print("🔍 Set breakpoints in main.py and debug!")
    print("-" * 50)
    
    # Use string import for reload to work
    uvicorn.run(
        "main:app",  # Import string instead of object
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload for debugging to prevent browser issues
        log_level="debug",
        access_log=True
    )
