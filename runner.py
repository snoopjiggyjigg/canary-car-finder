import logging
from time import perf_counter

from optimizer import provider_requests, search_summary
from providers import get_providers
from reports import write_reports
from search_cache import SearchCache, cache_mode_label


def run_search(settings, mode, progress_callback=None, stop_callback=None, pause_callback=None):
    providers = get_providers(settings)
    cache = SearchCache()
    plans = []
    duplicates_removed = 0
    for provider in providers:
        requests, duplicates = provider_requests(settings, mode, provider)
        plans.append((provider, requests))
        duplicates_removed += duplicates

    rows = []
    total = sum(len(requests) for _, requests in plans)
    completed = 0
    started_at = perf_counter()
    stats = _initial_stats(settings, total, duplicates_removed)
    summary = _summary(settings, mode, len(providers), stats, started_at)
    write_reports(rows, _progress("running", "Starting", completed, total, "Preparing provider searches", summary))

    for provider, requests in plans:
        live_requests = []
        for request in requests:
            _wait_if_paused(pause_callback, stop_callback)
            if stop_callback and stop_callback():
                logging.info("Search stopped by user")
                summary = _summary(settings, mode, len(providers), stats, started_at)
                return rows, write_reports(
                    rows,
                    _progress("stopped", "Stopped", completed, total, "Search stopped by user", summary),
                )

            cached = cache.get(provider.name, request, settings)
            if cached:
                stats.update(_current_search(provider.name, request))
                if _matches_filters(cached, settings):
                    rows.append(cached)
                completed += 1
                stats["cache_hits"] += 1
                stats["provider_searches_completed"] = completed
                stats["estimated_time_saved_seconds"] += _estimated_seconds_per_search(provider.name)
                _update_best(stats, cached)
                summary = _summary(settings, mode, len(providers), stats, started_at)
                _emit_progress(
                    progress_callback,
                    completed,
                    total,
                    f"Loaded {provider.name} {_route(request)} from cache",
                    summary,
                )
                write_reports(
                    rows,
                    _progress("running", f"Running {provider.name}", completed, total, "Loaded cached result", summary),
                )
            else:
                live_requests.append(request)

        if not live_requests:
            continue

        try:
            stats["browser_sessions_opened"] += 1
            write_reports(
                rows,
                _progress("running", f"Running {provider.name}", completed, total, f"Opening {provider.name}", summary),
            )
            provider.start()
            for index, request in enumerate(live_requests, start=1):
                _wait_if_paused(pause_callback, stop_callback)
                if stop_callback and stop_callback():
                    logging.info("Search stopped by user")
                    summary = _summary(settings, mode, len(providers), stats, started_at)
                    return rows, write_reports(
                        rows,
                        _progress("stopped", "Stopped", completed, total, "Search stopped by user", summary),
                    )

                pickup = request.pickup
                dropoff = request.dropoff
                route = _route(request)
                stats.update(_current_search(provider.name, request))
                summary = _summary(settings, mode, len(providers), stats, started_at)
                _emit_progress(
                    progress_callback,
                    completed + 1,
                    total,
                    f"Checking {provider.name} {route}",
                    summary,
                )
                write_reports(
                    rows,
                    _progress(
                        "running",
                        f"Running {provider.name}",
                        completed,
                        total,
                        f"Checking {provider.name} {route}",
                        summary,
                    ),
                )

                result = provider.search(pickup, dropoff, request.pickup_time, request.return_time, index)
                result["_result_source"] = "LIVE"
                cache.set(provider.name, request, settings, result)
                if _matches_filters(result, settings):
                    rows.append(result)
                completed += 1
                stats["live_searches"] += 1
                stats["new_provider_searches"] = stats["live_searches"]
                stats["provider_searches_completed"] = completed
                _update_best(stats, result)
                summary = _summary(settings, mode, len(providers), stats, started_at)

                price = result.get("price")
                if price:
                    message = f"Found EUR {price:.2f} for {route}"
                else:
                    message = result.get("status", "No price")
                _emit_progress(progress_callback, completed, total, message, summary)
                write_reports(
                    rows,
                    _progress(
                        "running",
                        f"Running {provider.name}",
                        completed,
                        total,
                        result.get("status", "Search completed"),
                        summary,
                    ),
                )
        finally:
            provider.close()

    stats["provider_searches_completed"] = completed
    summary = _summary(settings, mode, len(providers), stats, started_at)
    summary["search_duration_seconds"] = round(perf_counter() - started_at, 2)
    return rows, write_reports(
        rows,
        _progress("complete", "Complete", completed, total, "All provider searches finished", summary),
    )


def estimate_search(settings, mode):
    providers = get_providers(settings)
    duplicates_removed = 0
    provider_searches = 0
    for provider in providers:
        requests, duplicates = provider_requests(settings, mode, provider)
        duplicates_removed += duplicates
        provider_searches += len(requests)
    summary = search_summary(settings, mode, len(providers), duplicates_removed, provider_searches)
    seconds = _estimated_duration_seconds(provider_searches)
    summary.update(
        {
            "provider_searches_estimated": provider_searches,
            "estimated_duration_seconds": seconds,
            "estimated_duration_text": _duration_range(seconds),
            "cache_mode": cache_mode_label(settings),
        }
    )
    return summary


def _progress(status, label, completed, total, message, summary=None):
    return {
        "status": status,
        "label": label,
        "completed": completed,
        "total": total,
        "message": message,
        "summary": summary or {},
    }


def _summary(settings, mode, provider_count, stats, started_at):
    summary = search_summary(
        settings,
        mode,
        provider_count,
        stats["duplicate_searches_removed"],
        stats["provider_searches_completed"],
    )
    elapsed = perf_counter() - started_at
    remaining = max(stats["total_provider_searches"] - stats["provider_searches_completed"], 0)
    live_done = stats["live_searches"]
    average_live = elapsed / live_done if live_done else 0
    summary.update(stats)
    summary.update(
        {
            "cache_mode": cache_mode_label(settings),
            "elapsed_seconds": round(elapsed, 2),
            "estimated_remaining_seconds": round(remaining * average_live, 2) if average_live else None,
            "cache_hit_rate": _cache_hit_rate(stats),
        }
    )
    return summary


def _initial_stats(settings, total, duplicates_removed):
    return {
        "cache_mode": cache_mode_label(settings),
        "cache_hits": 0,
        "live_searches": 0,
        "new_provider_searches": 0,
        "duplicate_searches_removed": duplicates_removed,
        "total_provider_searches": total,
        "provider_searches_completed": 0,
        "browser_sessions_opened": 0,
        "estimated_time_saved_seconds": 0,
        "current_provider": "N/A",
        "current_holiday": "N/A",
        "current_time_combination": "N/A",
        "best_price_so_far": None,
        "cheapest_provider_so_far": "N/A",
    }


def _emit_progress(callback, completed, total, message, summary):
    if callback:
        callback(completed, total, message, summary)


def _wait_if_paused(pause_callback, stop_callback):
    if not pause_callback:
        return
    while pause_callback():
        if stop_callback and stop_callback():
            return
        from time import sleep

        sleep(0.2)


def _update_best(stats, result):
    if not result.get("success") or not result.get("price"):
        return
    price = float(result["price"])
    best = stats.get("best_price_so_far")
    if best is None or price < float(best):
        stats["best_price_so_far"] = price
        stats["cheapest_provider_so_far"] = result.get("provider", "N/A")


def _route(request):
    return (
        f"{_display_date(request.pickup)} -> {_display_date(request.dropoff)} "
        f"{request.actual_pickup_time}-{request.actual_return_time}"
    )


def _current_search(provider_name, request):
    return {
        "current_provider": provider_name,
        "current_holiday": f"{_display_date(request.pickup)} to {_display_date(request.dropoff)}",
        "current_time_combination": f"{request.actual_pickup_time} to {request.actual_return_time}",
    }


def _cache_hit_rate(stats):
    completed = stats["provider_searches_completed"]
    if not completed:
        return 0
    return round((stats["cache_hits"] / completed) * 100)


def _estimated_seconds_per_search(provider_name):
    if provider_name in {"PlusCar", "Payless Car"}:
        return 18
    return 8


def _estimated_duration_seconds(provider_searches):
    return provider_searches * 2


def _duration_range(seconds):
    low = int(seconds * 0.8)
    high = int(seconds * 1.2)
    return f"{_duration_text(low)} to {_duration_text(high)}"


def _duration_text(seconds):
    minutes = max(round(seconds / 60), 1)
    if minutes < 60:
        return f"{minutes} minutes"
    hours = minutes // 60
    remainder = minutes % 60
    return f"{hours}h {remainder}m"


def _matches_filters(row, settings):
    seats_filter = getattr(settings, "vehicle_seats", "Any")
    if seats_filter and seats_filter != "Any":
        seats = row.get("_seats")
        if seats is not None and int(seats) < int(seats_filter.rstrip("+")):
            return False

    transmission_filter = getattr(settings, "transmission", "Any")
    if transmission_filter and transmission_filter != "Any":
        transmission = row.get("_transmission")
        if transmission and transmission != transmission_filter:
            return False

    type_filter = getattr(settings, "vehicle_type", "Any")
    if type_filter and type_filter != "Any":
        vehicle_type = row.get("_vehicle_type")
        if vehicle_type and vehicle_type != type_filter:
            return False

    return True


def _display_date(value):
    return value.strftime("%d/%m/%Y")
