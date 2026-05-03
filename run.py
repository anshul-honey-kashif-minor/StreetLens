import subprocess
import sys
import time
from pathlib import Path

def main():
    print("Starting StreetLens Backend and Frontend...")
    
    project_root = Path(__file__).parent.resolve()
    
    # Start FastAPI backend
    print("[RUN] Starting FastAPI backend on port 8000...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--port", "8000", "--host", "127.0.0.1"],
        cwd=project_root
    )
    
    time.sleep(2) # Give backend a moment to start
    
    # Start Flask frontend
    print("[RUN] Starting Flask frontend...")
    frontend_process = subprocess.Popen(
        [sys.executable, str(project_root / "frontend" / "app.py")],
        cwd=project_root
    )
    
    try:
        # Wait for both processes
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n[RUN] Shutting down StreetLens...")
        backend_process.terminate()
        frontend_process.terminate()
        backend_process.wait()
        frontend_process.wait()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
