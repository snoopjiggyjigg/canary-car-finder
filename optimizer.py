from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class SearchRequest:
    pickup: object
    dropoff: object
    pickup_time: str
    return_time: str
    actual_pickup_time: str
    actual_return_time: str


def date_windows(settings, mode):
    if mode == "test":
        return [(settings.start_date, settings.start_date + timedelta(days=5))]

    if mode == "single":
        return [(settings.start_date, settings.end_date)]

    windows = []
    pickup = settings.start_date
    while pickup < settings.end_date:
        dropoff = pickup + timedelta(days=settings.min_days)
        while dropoff <= settings.end_date and (dropoff - pickup).days <= settings.max_days:
            windows.append((pickup, dropoff))
            dropoff += timedelta(days=1)
        pickup += timedelta(days=1)
    return windows


def time_pairs(settings):
    pickup_times = _setting_list(settings, "pickup_times", settings.pickup_time)
    return_times = _setting_list(settings, "return_times", settings.return_time)
    return [(pickup_time, return_time) for pickup_time in pickup_times for return_time in return_times]


def raw_combinations(settings, mode):
    return [
        (pickup, dropoff, pickup_time, return_time)
        for pickup, dropoff in date_windows(settings, mode)
        for pickup_time, return_time in time_pairs(settings)
    ]


def provider_requests(settings, mode, provider):
    requests = []
    seen = set()
    duplicates = 0

    for pickup, dropoff, pickup_time, return_time in raw_combinations(settings, mode):
        actual_pickup, actual_return = provider.adjust_times(pickup_time, return_time)
        key = (pickup, dropoff, actual_pickup, actual_return)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        requests.append(SearchRequest(pickup, dropoff, pickup_time, return_time, actual_pickup, actual_return))

    return requests, duplicates


def search_summary(settings, mode, provider_count=0, duplicates_removed=0, provider_searches=0):
    dates = date_windows(settings, mode)
    times = time_pairs(settings)
    pickup_options = list(dict.fromkeys(pickup for pickup, _ in times))
    return_options = list(dict.fromkeys(return_time for _, return_time in times))
    total = len(dates) * len(times)
    return {
        "holiday_window": f"{_display_date(settings.start_date)} to {_display_date(settings.end_date)}",
        "trip_length_range": f"{settings.min_days} to {settings.max_days} days",
        "pickup_time_options": ", ".join(pickup_options),
        "return_time_options": ", ".join(return_options),
        "date_combinations_generated": len(dates),
        "time_combinations_generated": len(times),
        "total_combinations_generated": total,
        "provider_count": provider_count,
        "duplicate_searches_removed": duplicates_removed,
        "provider_searches_completed": provider_searches,
    }


def _setting_list(settings, name, fallback):
    values = getattr(settings, name, None)
    if not values:
        return [fallback]
    return list(dict.fromkeys(values))


def _display_date(value):
    return value.strftime("%d/%m/%Y")
