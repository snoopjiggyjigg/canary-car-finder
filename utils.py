from datetime import timedelta
from pathlib import Path
import logging
import sys

def setup_logging():
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler("logs/canary-car-finder.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

def generate_combinations(settings, mode):
    if mode == "test":
        return [(settings.start_date, settings.start_date.replace(day=settings.start_date.day + 5), settings.pickup_time, settings.return_time)]

    combos = []
    pickup = settings.start_date
    while pickup < settings.end_date:
        dropoff = pickup + timedelta(days=settings.min_days)
        while dropoff <= settings.end_date and (dropoff - pickup).days <= settings.max_days:
            rtime = settings.final_return_time if dropoff == settings.end_date else settings.return_time
            combos.append((pickup, dropoff, settings.pickup_time, rtime))
            dropoff += timedelta(days=1)
        pickup += timedelta(days=1)

    if mode == "small":
        return combos[:10]
    return combos
