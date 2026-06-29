import logging

from providers import get_providers
from reports import write_reports
from utils import generate_combinations


def run_search(settings, mode, progress_callback=None, stop_callback=None):
    combos = generate_combinations(settings, mode)
    providers = get_providers(settings)
    rows = []
    total = len(combos) * len(providers)
    completed = 0
    write_reports(rows, _progress("running", "Starting", completed, total, "Preparing provider searches"))

    for provider in providers:
        try:
            write_reports(
                rows,
                _progress("running", f"Running {provider.name}", completed, total, f"Opening {provider.name}"),
            )
            provider.start()
            for index, (pickup, dropoff, ptime, rtime) in enumerate(combos, start=1):
                if stop_callback and stop_callback():
                    logging.info("Search stopped by user")
                    return rows, write_reports(
                        rows,
                        _progress("stopped", "Stopped", completed, total, "Search stopped by user"),
                    )

                if progress_callback:
                    progress_callback(completed + 1, total, f"Checking {provider.name} {pickup} -> {dropoff}")
                write_reports(
                    rows,
                    _progress(
                        "running",
                        f"Running {provider.name}",
                        completed,
                        total,
                        f"Checking {provider.name} {pickup} -> {dropoff}",
                    ),
                )

                result = provider.search(pickup, dropoff, ptime, rtime, index)
                rows.append(result)
                completed += 1

                if progress_callback:
                    price = result.get("price")
                    if price:
                        progress_callback(completed, total, f"Found EUR {price:.2f} for {pickup} -> {dropoff}")
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
                    ),
                )
        finally:
            provider.close()

    return rows, write_reports(rows, _progress("complete", "Complete", completed, total, "All provider searches finished"))


def _progress(status, label, completed, total, message):
    return {
        "status": status,
        "label": label,
        "completed": completed,
        "total": total,
        "message": message,
    }
