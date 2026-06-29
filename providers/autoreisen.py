import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from .base import CarProvider

RESULTS = Path("results")
DEBUG = RESULTS / "debug"
EURO = chr(8364)
BASE_URL = "https://www.autoreisen.com"
HOME_URL = f"{BASE_URL}/car-hire/fuerteventura/airport/"
RATES_URL = f"{BASE_URL}/car-hire/rates-fleet.php"
FUERTEVENTURA_AIRPORT = "19"
SAME_OFFICE = "9999"
PRICE_RE = re.compile(re.escape(EURO) + r"\s*([0-9]+(?:[,.][0-9]{2})?)")


def money(raw: str) -> float:
    return float(raw.replace(".", "").replace(",", "."))


class AutoReisenProvider(CarProvider):
    name = "AutoReisen"
    logo_url = f"{BASE_URL}/images/logo.png"

    def start(self):
        RESULTS.mkdir(exist_ok=True)
        DEBUG.mkdir(parents=True, exist_ok=True)

    def close(self):
        pass

    def search(self, pickup, dropoff, pickup_time, return_time, index):
        days_elapsed = (dropoff - pickup).days
        try:
            html = self._quote_html(pickup, dropoff, pickup_time, return_time)
            (DEBUG / f"autoreisen_{index:03d}_results.html").write_text(html, encoding="utf-8")
            vehicles = AutoReisenFleetParser().parse(html)
            best = vehicles[0] if vehicles else None
            price = best["price"] if best else None
            daily = round(price / days_elapsed, 2) if price and days_elapsed else None
            return self.result(
                pickup,
                dropoff,
                pickup_time,
                return_time,
                days_elapsed,
                success=price is not None,
                vehicle=best["vehicle"] if best else None,
                vehicle_image=best["image_url"] if best else None,
                daily=daily,
                price=price,
                vehicles_found=len(vehicles),
                url=best["booking_url"] if best else RATES_URL,
                status=f"OK {EURO}{price:.2f}" if price else "No vehicle price found",
            )
        except Exception as exc:
            return self.result(
                pickup,
                dropoff,
                pickup_time,
                return_time,
                days_elapsed,
                success=False,
                vehicle=None,
                vehicle_image=None,
                daily=None,
                price=None,
                vehicles_found=0,
                url=RATES_URL,
                status=f"ERROR: {type(exc).__name__}: {str(exc)[:160]}",
            )

    def _quote_html(self, pickup, dropoff, pickup_time, return_time):
        body = urlencode(
            {
                "ofi_rec": FUERTEVENTURA_AIRPORT,
                "ofi_dev": SAME_OFFICE,
                "dia_inicio": pickup.strftime("%d"),
                "mes_inicio": pickup.strftime("%m-%Y"),
                "hora_inicio": _nearest_supported_time(pickup_time),
                "dia_final": dropoff.strftime("%d"),
                "mes_final": dropoff.strftime("%m-%Y"),
                "hora_final": _nearest_supported_time(return_time),
                "carnet": "",
                "redata": "0",
            }
        ).encode("utf-8")
        request = Request(
            RATES_URL,
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": HOME_URL,
                "User-Agent": "CanaryCarFinder/1.0",
            },
        )
        with urlopen(request, timeout=45) as response:
            return response.read().decode("utf-8", errors="replace")


class AutoReisenFleetParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.vehicles = []
        self.current = None
        self.capture_title = False
        self.capture_price = False
        self.in_price_block = False

    def parse(self, html):
        self.feed(html)
        return sorted(self.vehicles, key=lambda vehicle: vehicle["price"])

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = _classes(attrs)

        if tag == "article" and "car-feature" in classes:
            self.current = {"vehicle": None, "image_url": None, "price": None, "booking_url": RATES_URL}

        if not self.current:
            return

        if tag == "strong" and "title" in classes:
            self.capture_title = True
        elif tag == "div" and "price-block" in classes:
            self.in_price_block = True
        elif tag == "span" and self.in_price_block:
            self.capture_price = True
        elif tag == "img" and not self.current.get("image_url"):
            src = attrs.get("src")
            if src and "coche_" in src:
                self.current["image_url"] = urljoin(BASE_URL, src)
        elif tag == "a" and self.in_price_block:
            href = attrs.get("href")
            if href:
                self.current["booking_url"] = urljoin(BASE_URL, href)

    def handle_data(self, data):
        if not self.current:
            return

        text = data.strip()
        if not text:
            return

        if self.capture_title:
            self.current["vehicle"] = text
        elif self.capture_price:
            match = PRICE_RE.search(text)
            if match:
                self.current["price"] = money(match.group(1))

    def handle_endtag(self, tag):
        if self.current and tag == "article":
            if self.current.get("vehicle") and self.current.get("price") is not None:
                self.vehicles.append(self.current)
            self.current = None
            self.in_price_block = False
            self.capture_title = False
            self.capture_price = False

        if tag == "strong":
            self.capture_title = False
        elif tag == "span":
            self.capture_price = False
        elif tag == "div" and self.in_price_block:
            self.in_price_block = False


def _classes(attrs):
    return set((attrs.get("class") or "").split())


def _nearest_supported_time(value):
    hour, minute = [int(part) for part in value.split(":", 1)]
    if minute == 0:
        return f"{hour:02d}:00"
    if hour >= 23:
        return "23:59"
    return f"{hour + 1:02d}:00"
