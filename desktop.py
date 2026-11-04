
import os
import sys
import time
import threading
import secrets
import socket
import webbrowser

from pathlib import Path
from flask import redirect, url_for
from app import create_app, db


APP_NAME = "Chad Civil Registry"
HOST = "127.0.0.1"
PORT = 5000


def get_data_dir():
    base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    data_dir = base / "ChadCivilRegistry"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


DATA_DIR = get_data_dir()
os.environ["DATABASE_URL"] = (
    f"sqlite:///{(DATA_DIR / 'civil_registry.db').as_posix()}"
)

secret_file = DATA_DIR / "secret_key"

if secret_file.exists():
    secret_key = secret_file.read_text(encoding="utf-8").strip()
else:
    secret_key = secrets.token_urlsafe(48)
    secret_file.write_text(secret_key, encoding="utf-8")

os.environ["SECRET_KEY"] = secret_key

app = create_app("production")


@app.route("/")
def index():
    return redirect(url_for("auth.login"))


def run_server():
    with app.app_context():
        db.create_all()

    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


def wait_for_server(url, timeout=15):
    import urllib.request

    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except Exception:
            time.sleep(0.3)

    return False


def main():
    # Avoid starting a second copy on the same port.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((HOST, PORT))
        except OSError:
            print(
                f"{APP_NAME} may already be running on port {PORT}."
            )
            webbrowser.open(f"http://{HOST}:{PORT}/")
            return

    server_thread = threading.Thread(
        target=run_server,
        daemon=True,
    )
    server_thread.start()

    url = f"http://{HOST}:{PORT}/"

    if not wait_for_server(url):
        raise RuntimeError(
            f"{APP_NAME} could not start. "
            f"Check whether port {PORT} is already in use."
        )

    webbrowser.open(url)

    # Keep the launcher alive while the server is running.
    server_thread.join()


if __name__ == "__main__":
    main()
