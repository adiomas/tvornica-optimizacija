"""Desktop launcher — starts Streamlit server and opens a native window."""
import os
import socket
import subprocess
import sys
import threading
import time

import webview


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def get_app_path():
    """Resolve app.py path — works both in dev and PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "app.py")
    return os.path.join(os.path.dirname(__file__), "app.py")


def start_streamlit_dev(port):
    """Dev mode: launch Streamlit via subprocess (normal Python)."""
    env = os.environ.copy()
    env["STREAMLIT_SERVER_PORT"] = str(port)
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"

    subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", get_app_path(),
         "--server.port", str(port),
         "--server.headless", "true",
         "--browser.gatherUsageStats", "false",
         "--server.fileWatcherType", "none"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def start_streamlit_frozen(port):
    """Frozen mode: run Streamlit in-process to avoid infinite subprocess loop.

    In PyInstaller, sys.executable points to the .exe itself.
    Calling subprocess.Popen([sys.executable, ...]) would re-run this launcher,
    spawning infinite processes. Instead, we call Streamlit's CLI directly.
    """
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"

    sys.argv = [
        "streamlit", "run", get_app_path(),
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.fileWatcherType", "none",
    ]

    from streamlit.web.cli import main
    main()


def wait_for_server(port, timeout=30):
    """Wait until Streamlit server is responsive."""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/_stcore/health")
            return True
        except Exception:
            time.sleep(0.5)
    return False


if __name__ == "__main__":
    port = find_free_port()

    if getattr(sys, "frozen", False):
        # Frozen (PyInstaller): run Streamlit in-process via thread
        threading.Thread(target=start_streamlit_frozen, args=(port,), daemon=True).start()
    else:
        # Dev: launch Streamlit as subprocess
        threading.Thread(target=start_streamlit_dev, args=(port,), daemon=True).start()

    if not wait_for_server(port):
        print("Streamlit server failed to start.")
        sys.exit(1)

    webview.create_window(
        "TZH Promet vs Banka",
        f"http://localhost:{port}",
        width=1200,
        height=850,
        min_size=(800, 600),
    )
    webview.start()
