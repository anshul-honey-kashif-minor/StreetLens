import subprocess
import sys

def start_fastapi():
    return subprocess.Popen(
        ["uvicorn", "app:app", "--reload"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )

def start_flask():
    return subprocess.Popen(
        ["python", "-m", "frontend.app"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )

if __name__ == "__main__":
    fastapi = start_fastapi()
    flask = start_flask()

    try:
        fastapi.wait()
        flask.wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        fastapi.terminate()
        flask.terminate()