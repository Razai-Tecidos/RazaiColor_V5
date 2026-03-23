"""
Launcher script for PyInstaller-bundled Streamlit app.
This is the entry point that PyInstaller will use.
"""
import multiprocessing
import os
import sys


def get_base_path():
    """Return the base path whether running as script or frozen exe."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def main():
    multiprocessing.freeze_support()

    base_path = get_base_path()
    app_path = os.path.join(base_path, "app.py")

    # Ensure src is importable at runtime
    if base_path not in sys.path:
        sys.path.insert(0, base_path)

    if getattr(sys, "frozen", False):
        # ── Frozen exe: call Streamlit bootstrap directly (no subprocess) ──
        import threading
        import time
        import webbrowser

        # Configure streamlit via environment before importing it
        os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
        os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
        os.environ["STREAMLIT_SERVER_FILE_WATCHER_TYPE"] = "none"
        os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
        os.environ["STREAMLIT_SERVER_ENABLE_CORS"] = "false"
        os.environ["STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION"] = "false"

        # Force production mode via config API (env vars alone may fail
        # because PyInstaller extracts streamlit outside of site-packages,
        # making the default detection think this is a dev checkout).
        from streamlit import config
        config.set_option("global.developmentMode", False)
        config.set_option("server.headless", True)
        config.set_option("server.fileWatcherType", "none")
        config.set_option("browser.gatherUsageStats", False)
        config.set_option("server.enableCORS", False)
        config.set_option("server.enableXsrfProtection", False)

        def _open_browser():
            time.sleep(3)
            webbrowser.open("http://localhost:8501")

        threading.Thread(target=_open_browser, daemon=True).start()

        from streamlit.web import bootstrap

        flag_options = {
            "global.developmentMode": False,
            "server.headless": True,
            "server.fileWatcherType": "none",
            "browser.gatherUsageStats": False,
        }
        bootstrap.run(app_path, False, [], flag_options=flag_options)
    else:
        # ── Dev mode: launch via subprocess normally ──
        import subprocess
        args = [
            sys.executable, "-m", "streamlit", "run",
            app_path,
            "--server.headless=true",
            "--server.fileWatcherType=none",
            "--browser.gatherUsageStats=false",
            "--global.developmentMode=false",
        ]
        try:
            process = subprocess.run(args)
            sys.exit(process.returncode)
        except KeyboardInterrupt:
            sys.exit(0)


if __name__ == "__main__":
    main()
