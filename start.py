#!/usr/bin/env python3
"""
Skew Hunter Web App - Entry Point

This script starts both the FastAPI backend and serves the React frontend.
"""

import os
import sys
import subprocess
import time
import webbrowser
import signal
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).parent / "backend"
FRONTEND_DIR = Path(__file__).parent / "frontend"
sys.path.insert(0, str(BACKEND_DIR))


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import uvicorn
        import fastapi
    except ImportError:
        print("Installing backend dependencies...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r",
            str(BACKEND_DIR / "requirements.txt")
        ], check=True)


def start_backend(port: int = 8000):
    """Start the FastAPI backend server."""
    import uvicorn
    from main import app

    print(f"\n🚀 Starting Skew Hunter Backend on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def start_frontend_dev(port: int = 5173):
    """Start the Vite development server (for development only)."""
    print(f"\n🎨 Starting Frontend Dev Server on port {port}...")
    os.chdir(FRONTEND_DIR)
    subprocess.run(["npm", "run", "dev"], shell=True)


def build_frontend():
    """Build the frontend for production."""
    print("\n📦 Building frontend...")
    os.chdir(FRONTEND_DIR)

    # Install dependencies if needed
    if not (FRONTEND_DIR / "node_modules").exists():
        print("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], shell=True, check=True)

    # Build
    subprocess.run(["npm", "run", "build"], shell=True, check=True)
    print("✅ Frontend built successfully!")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Skew Hunter Web App")
    parser.add_argument(
        "--mode",
        choices=["dev", "prod", "build"],
        default="prod",
        help="Run mode: dev (separate servers), prod (backend only), build (build frontend)"
    )
    parser.add_argument("--port", type=int, default=8000, help="Backend port")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")

    args = parser.parse_args()

    # Check dependencies
    check_dependencies()

    if args.mode == "build":
        build_frontend()
        return

    if args.mode == "dev":
        print("\n" + "="*60)
        print("  SKEW HUNTER - Development Mode")
        print("="*60)
        print("\nStarting in development mode...")
        print("Backend will run on http://localhost:8000")
        print("Frontend will run on http://localhost:5173")
        print("\nPress Ctrl+C to stop all servers\n")

        # Start backend in background
        backend_process = subprocess.Popen([
            sys.executable, "-c",
            f"import sys; sys.path.insert(0, '{BACKEND_DIR}'); "
            f"import uvicorn; from main import app; "
            f"uvicorn.run(app, host='0.0.0.0', port={args.port}, log_level='info')"
        ])

        time.sleep(2)  # Wait for backend to start

        # Start frontend
        try:
            os.chdir(FRONTEND_DIR)
            subprocess.run(["npm", "run", "dev"], shell=True)
        except KeyboardInterrupt:
            pass
        finally:
            backend_process.terminate()
            backend_process.wait()

    else:  # prod mode
        print("\n" + "="*60)
        print("  SKEW HUNTER - Production Mode")
        print("="*60)

        # Check if frontend is built
        dist_dir = FRONTEND_DIR / "dist"
        if not dist_dir.exists():
            print("\n⚠️  Frontend not built. Building now...")
            build_frontend()

        print(f"\n🌐 Server running at http://localhost:{args.port}")
        print("Press Ctrl+C to stop\n")

        if not args.no_browser:
            # Open browser after a short delay
            def open_browser():
                time.sleep(2)
                webbrowser.open(f"http://localhost:{args.port}")

            import threading
            threading.Thread(target=open_browser, daemon=True).start()

        # Start backend (which will serve the built frontend)
        os.chdir(BACKEND_DIR)
        start_backend(args.port)


if __name__ == "__main__":
    main()
