#!/usr/bin/env python3
"""Helper to run the PPTAgent backend in a reproducible way.

Responsibilities:
- Check Python version
- Check that editable package is importable
- Check that customized python-pptx is installed (version tag)
- Start uvicorn programmatically and stream logs

This script is intended to be called by `run_backend.sh` so the user
doesn't need to remember multiple commands.
"""
import sys
import subprocess
import shutil
import importlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_python():
    if sys.version_info < (3, 11):
        print(f"ERROR: Python>=3.11 is required, found {sys.version}")
        sys.exit(1)


def check_importable_package():
    try:
        import pptagent  # noqa: F401
        print("[ok] pptagent package importable")
    except Exception as e:
        print("ERROR: pptagent is not importable. Please run: pip install -e .")
        print(f"Import error: {e}")
        sys.exit(1)


def check_python_pptx():
    try:
        import pptx
        v = getattr(pptx, "__version__", "")
        print(f"[ok] python-pptx installed: {v}")
        if "+PPTAgent" not in v:
            print("WARNING: python-pptx does not appear to be the customized PPTAgent build.")
            print("You may want to install the fork used by this project:")
            print("  pip install git+https://github.com/Force1ess/python-pptx@219513d7d81a61961fc541578c1857d08b43aa2a")
    except Exception as e:
        print("ERROR: python-pptx not installed or import failed.")
        print("Install the customized package via:")
        print("  pip install git+https://github.com/Force1ess/python-pptx@219513d7d81a61961fc541578c1857d08b43aa2a")
        print(f"Import error: {e}")
        sys.exit(1)


def start_uvicorn():
    # Prefer programmatic run via uvicorn.run to preserve logs in this process
    try:
        import uvicorn
        from pptagent_ui.backend import app

        host = os.environ.get("BACKEND_HOST", "0.0.0.0")
        port = int(os.environ.get("BACKEND_PORT", "9297"))
        print(f"Starting uvicorn on {host}:{port} (ctrl-c to stop)")
        uvicorn.run(app, host=host, port=port)
    except Exception as e:
        print(f"Failed to start uvicorn: {e}")
        raise


def main():
    check_python()
    # Add repo root to sys.path so imports work even if not installed
    sys.path.insert(0, str(ROOT))
    check_importable_package()
    check_python_pptx()
    start_uvicorn()


if __name__ == "__main__":
    main()
