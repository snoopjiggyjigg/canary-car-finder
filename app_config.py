import json
from pathlib import Path
import sys


APP_CONFIG_PATH = Path("config/app_config.json")
APP_NAME = "Canary Islands Car Hire Optimiser"
APP_VERSION = "v1.5.0"

DEFAULT_APP_CONFIG = {
    "app_name": APP_NAME,
    "version": APP_VERSION,
    "github_url": "https://github.com/snoopjiggyjigg/canary-car-finder",
    "issue_url": "https://github.com/snoopjiggyjigg/canary-car-finder/issues",
    "donation_url": "https://ko-fi.com/jamieclarke",
    "holiday_home_url": "https://www.fuerteventurarental.co.uk/",
}


def load_app_config():
    path = _resource_path(APP_CONFIG_PATH)
    if not path.exists():
        return DEFAULT_APP_CONFIG.copy()

    data = json.loads(path.read_text(encoding="utf-8"))
    config = DEFAULT_APP_CONFIG.copy()
    config.update({key: value for key, value in data.items() if value is not None})
    config["app_name"] = APP_NAME
    config["version"] = APP_VERSION
    return config


def _resource_path(path):
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / path
    return path
