import json
from pathlib import Path
import sys


APP_CONFIG_PATH = Path("config/app_config.json")

DEFAULT_APP_CONFIG = {
    "version": "1.0.0",
    "github_url": "https://github.com/snoopjiggyjigg/canary-car-finder",
    "issue_url": "https://github.com/snoopjiggyjigg/canary-car-finder/issues",
    "donation_url": "https://github.com/sponsors/snoopjiggyjigg",
}


def load_app_config():
    path = _resource_path(APP_CONFIG_PATH)
    if not path.exists():
        return DEFAULT_APP_CONFIG.copy()

    data = json.loads(path.read_text(encoding="utf-8"))
    config = DEFAULT_APP_CONFIG.copy()
    config.update({key: value for key, value in data.items() if value is not None})
    return config


def _resource_path(path):
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / path
    return path
