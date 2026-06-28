import logging
from providers.pluscar import PlusCarProvider
from reports import write_reports
from utils import generate_combinations

def run_search(settings, mode, progress_callback=None, stop_callback=None):
    combos = generate_combinations(settings, mode)
    rows = []

    provider = PlusCarProvider(settings)

    try:
        provider.start()
        total = len(combos)

        for index, (pickup, dropoff, ptime, rtime) in enumerate(combos, start=1):
            if stop_callback and stop_callback():
                logging.info("Search stopped by user")
                break

            if progress_callback:
                progress_callback(index, total, f"Checking PlusCar {pickup} → {dropoff}")

            result = provider.search(pickup, dropoff, ptime, rtime, index)
            rows.append(result)
            write_reports(rows)

            if progress_callback:
                price = result.get("price")
                if price:
                    progress_callback(index, total, f"Found €{price:.2f} for {pickup} → {dropoff}")
                else:
                    progress_callback(index, total, result.get("status", "No price"))

    finally:
        provider.close()

    return rows, write_reports(rows)
