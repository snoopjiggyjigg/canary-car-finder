from pathlib import Path
import logging
import sys

from optimizer import raw_combinations

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
    combos = raw_combinations(settings, mode)

    if mode == "small":
        return combos[:10]
    return combos
