import json
from pathlib import Path
from dataclasses import dataclass
from datetime import date
import sys

SETTINGS_PATH = Path("config/default_settings.json")

@dataclass
class AppSettings:
    start_date: date
    end_date: date
    min_days: int
    max_days: int
    pickup_time: str
    return_time: str
    final_return_time: str
    visible_browser: bool
    pluscar_airport_option: str

    @property
    def headless(self) -> bool:
        return not self.visible_browser

def load_settings() -> AppSettings:
    data = json.loads(_resource_path(SETTINGS_PATH).read_text(encoding="utf-8"))
    return AppSettings(
        start_date=date.fromisoformat(data["start_date"]),
        end_date=date.fromisoformat(data["end_date"]),
        min_days=int(data["min_days"]),
        max_days=int(data["max_days"]),
        pickup_time=data["pickup_time"],
        return_time=data["return_time"],
        final_return_time=data["final_return_time"],
        visible_browser=bool(data["visible_browser"]),
        pluscar_airport_option=str(data["pluscar_airport_option"]),
    )

def save_settings(settings: AppSettings):
    data = {
        "start_date": settings.start_date.isoformat(),
        "end_date": settings.end_date.isoformat(),
        "min_days": settings.min_days,
        "max_days": settings.max_days,
        "pickup_time": settings.pickup_time,
        "return_time": settings.return_time,
        "final_return_time": settings.final_return_time,
        "visible_browser": settings.visible_browser,
        "pluscar_airport_option": settings.pluscar_airport_option,
    }
    SETTINGS_PATH.parent.mkdir(exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _resource_path(path):
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / path
    return path
