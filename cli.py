import argparse
import webbrowser
from settings import load_settings
from utils import setup_logging
from runner import run_search

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["test", "small", "full"], default="test")
    parser.add_argument("--hidden", action="store_true", help="Run browser hidden/headless")
    args = parser.parse_args()

    setup_logging()
    settings = load_settings()
    if args.hidden:
        settings.visible_browser = False

    def progress(i, total, msg):
        print(f"[{i}/{total}] {msg}")

    rows, reports = run_search(settings, args.mode, progress_callback=progress)
    _, _, html = reports
    print(f"Report: {html.resolve()}")
    webbrowser.open(html.resolve().as_uri())

if __name__ == "__main__":
    main()
