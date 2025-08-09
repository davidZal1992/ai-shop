#!/usr/bin/env python3
"""
Clean restart script for the crawler server
"""
import subprocess
import time
import sys
import signal
import os

def kill_existing_processes():
    """Kill any existing server processes"""
    try:
        # Kill python debug processes
        subprocess.run(["pkill", "-f", "python debug_main.py"], check=False)
        subprocess.run(["pkill", "-f", "uvicorn"], check=False)
        time.sleep(1)
        print("✅ Killed existing processes")
    except Exception as e:
        print(f"⚠️ Error killing processes: {e}")

def start_server():
    """Start the server"""
    try:
        print("🚀 Starting crawler server...")
        process = subprocess.Popen([
            sys.executable, "debug_main.py"
        ], cwd="/Users/dzaltsman/PycharmProjects/crwaler-server")
        
        print(f"📍 Server started with PID: {process.pid}")
        print("📍 Server: http://localhost:8000")
        print("📖 API docs: http://localhost:8000/docs")
        print("🔍 Browser will be visible for testing!")
        print("⏹️  Press Ctrl+C to stop")
        
        # Wait for the process
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n⏹️  Stopping server...")
            process.terminate()
            time.sleep(2)
            if process.poll() is None:
                process.kill()
            print("✅ Server stopped")
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    kill_existing_processes()
    start_server()
