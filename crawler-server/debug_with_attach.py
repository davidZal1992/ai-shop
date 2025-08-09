"""
Start server with debugpy for VS Code to attach
"""
import debugpy
import uvicorn

if __name__ == "__main__":
    print("🐛 Starting server with debugpy...")
    print("📍 Server: http://localhost:8000")
    print("🔗 Debug port: 5678")
    print("🔍 In VS Code: Run '🔗 Attach to Server' config")
    print("-" * 50)
    
    # Start debugpy server
    debugpy.listen(5678)
    print("⏳ Waiting for VS Code to attach...")
    debugpy.wait_for_client()  # Wait for VS Code to attach
    print("✅ VS Code attached! Breakpoints will work now.")
    
    # Start the FastAPI server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload when debugging
        log_level="debug"
    )
