#!/usr/bin/env python3
"""
Capture README dashboard preview (short GIF) from a local mock server.

Prerequisites:
  pip install playwright pillow
  playwright install chromium

Usage (from repo root):
  python3 scripts/capture_readme_assets.py

Starts run.py on a fixed localhost port, waits for Dash, screenshots twice, writes:
  docs/images/dashboard-mock.gif
"""

from __future__ import annotations

import http.client
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "docs" / "images"
DEFAULT_PORT = 18765


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_http_ready(host: str, port: int, timeout_sec: float = 60.0) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            conn = http.client.HTTPConnection(host, port, timeout=2)
            conn.request("GET", "/")
            conn.getresponse()
            conn.close()
            return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError(f"Server not ready at http://{host}:{port}")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1
    try:
        from PIL import Image
    except ImportError:
        print("Install: pip install pillow", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gif_out = OUT_DIR / "dashboard-mock.gif"

    env = os.environ.copy()
    env["UGV_MON_USE_LIVE"] = "false"

    port = DEFAULT_PORT
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            port = _pick_port()

    with tempfile.TemporaryDirectory() as tmp:
        frame_a = Path(tmp) / "frame_a.png"
        frame_b = Path(tmp) / "frame_b.png"

        proc = subprocess.Popen(
            [sys.executable, str(REPO_ROOT / "run.py"), "--mode", "mock", "--port", str(port)],
            cwd=str(REPO_ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            _wait_http_ready("127.0.0.1", port)

            url = f"http://127.0.0.1:{port}/"
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                # Dash keeps long-polling; avoid networkidle timeouts
                page.goto(url, wait_until="load", timeout=120_000)
                time.sleep(3.0)
                page.screenshot(path=str(frame_a), full_page=True)
                time.sleep(3.5)
                page.screenshot(path=str(frame_b), full_page=True)
                browser.close()

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

        if not frame_a.is_file() or not frame_b.is_file():
            print("Screenshot failed (missing frames).", file=sys.stderr)
            return 1

        with Image.open(frame_a) as img_a, Image.open(frame_b) as img_b:
            img_a.save(
                gif_out,
                save_all=True,
                append_images=[img_b],
                duration=900,
                loop=0,
                optimize=True,
            )

    print(f"Wrote {gif_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
