import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


CACHE_PATH = Path("cache/search_cache.json")
CACHE_MODES = {
    "Always check fresh prices": 0,
    "Reuse prices from today": 24,
    "Reuse prices from this week": 24 * 7,
}
LEGACY_CACHE_MODES = {
    "Live Search": "Always check fresh prices",
    "Smart Search": "Reuse prices from today",
    "Fast Search": "Reuse prices from this week",
}


class SearchCache:
    def __init__(self, path=CACHE_PATH):
        self.path = Path(path)
        self.records = self._load()

    def get(self, provider_name, request, settings):
        max_age_hours = cache_lifetime_hours(settings)
        if max_age_hours <= 0:
            return None

        key = cache_key(provider_name, request, settings)
        record = self.records.get(key)
        if not record or not _is_fresh(record.get("timestamp"), max_age_hours):
            return None

        row = deepcopy(record.get("row") or {})
        if not row:
            return None
        row["_result_source"] = "CACHE"
        row["_cache_timestamp"] = record.get("timestamp")
        return row

    def set(self, provider_name, request, settings, row):
        key = cache_key(provider_name, request, settings)
        cached_row = deepcopy(row)
        cached_row["_result_source"] = "LIVE"
        cached_row["_cache_timestamp"] = _now_iso()
        self.records[key] = {
            "timestamp": cached_row["_cache_timestamp"],
            "provider": provider_name,
            "row": cached_row,
        }
        self.save()

    def save(self):
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text(json.dumps(self.records, indent=2, sort_keys=True), encoding="utf-8")

    def _load(self):
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}


def cache_key(provider_name, request, settings):
    payload = {
        "provider": provider_name,
        "pickup": str(request.pickup),
        "dropoff": str(request.dropoff),
        "actual_pickup_time": request.actual_pickup_time,
        "actual_return_time": request.actual_return_time,
        "transmission": getattr(settings, "transmission", "Any"),
        "vehicle_seats": getattr(settings, "vehicle_seats", "Any"),
        "vehicle_type": getattr(settings, "vehicle_type", "Any"),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cache_lifetime_hours(settings):
    return CACHE_MODES.get(_cache_mode(getattr(settings, "cache_mode", "Always check fresh prices")), 0)


def cache_mode_label(settings):
    return _cache_mode(getattr(settings, "cache_mode", "Always check fresh prices"))


def _cache_mode(value):
    return LEGACY_CACHE_MODES.get(value, value)


def _is_fresh(timestamp, max_age_hours):
    try:
        cached_at = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    except ValueError:
        return False
    age = datetime.now(timezone.utc) - cached_at
    return age.total_seconds() <= max_age_hours * 3600


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
