import logging
from time import perf_counter

from optimizer import provider_requests, search_summary
from providers import get_providers
from reports import write_reports


def run_search(settings, mode, progress_callback=None, stop_callback=None):
    providers = get_providers(settings)
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
    summary = search_summary(settings, mode, len(providers), duplicates_removed, completed)
    write_reports(rows, _progress("running", "Starting", completed, total, "Preparing provider searches", summary))

    for provider, requests in plans:
        try:
            write_reports(
                rows,
                _progress("running", f"Running {provider.name}", completed, total, f"Opening {provider.name}", summary),
            )
            provider.start()
            for index, request in enumerate(requests, start=1):
                if stop_callback and stop_callback():
                    logging.info("Search stopped by user")
                    summary = search_summary(settings, mode, len(providers), duplicates_removed, completed)
                    return rows, write_reports(
                        rows,
                        _progress("stopped", "Stopped", completed, total, "Search stopped by user", summary),
                    )

                pickup = request.pickup
                dropoff = request.dropoff
                route = f"{_display_date(pickup)} -> {_display_date(dropoff)}"
                if progress_callback:
                    progress_callback(completed + 1, total, f"Checking {provider.name} {route}")
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
                if _matches_filters(result, settings):
                    rows.append(result)
                completed += 1
                summary = search_summary(settings, mode, len(providers), duplicates_removed, completed)

                if progress_callback:
                    price = result.get("price")
                    if price:
                        progress_callback(completed, total, f"Found EUR {price:.2f} for {route}")
                    else:
                        progress_callback(completed, total, result.get("status", "No price"))
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

    summary = search_summary(settings, mode, len(providers), duplicates_removed, completed)
    summary["search_duration_seconds"] = round(perf_counter() - started_at, 2)
    return rows, write_reports(
        rows,
        _progress("complete", "Complete", completed, total, "All provider searches finished", summary),
    )


def _progress(status, label, completed, total, message, summary=None):
    return {
        "status": status,
        "label": label,
        "completed": completed,
        "total": total,
        "message": message,
        "summary": summary or {},
    }


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
