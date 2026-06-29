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

    for provider in providers:
        try:
            provider.start()
            for index, (pickup, dropoff, ptime, rtime) in enumerate(combos, start=1):
                if stop_callback and stop_callback():
                    logging.info("Search stopped by user")
                    return rows, write_reports(rows)

                completed += 1
                if progress_callback:
                    progress_callback(completed, total, f"Checking {provider.name} {pickup} -> {dropoff}")

                result = provider.search(pickup, dropoff, ptime, rtime, index)
                rows.append(result)
                write_reports(rows)

                if progress_callback:
                    price = result.get("price")
                    if price:
                        progress_callback(completed, total, f"Found EUR {price:.2f} for {pickup} -> {dropoff}")
                    else:
                        progress_callback(completed, total, result.get("status", "No price"))
        finally:
            provider.close()

    return rows, write_reports(rows)
