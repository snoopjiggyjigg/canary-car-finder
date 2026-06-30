from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from .base import CarProvider

RESULTS = Path("results")
DEBUG = RESULTS / "debug"
BASE_URL = "https://www.payless.es"
BOOKING_URL = f"{BASE_URL}/en/action/booking1"
FUERTEVENTURA_AIRPORT = "F"


def money(raw: str) -> float:
    return float(raw.replace(".", "").replace(",", "."))


class PaylessProvider(CarProvider):
    name = "Payless Car"
    logo_url = f"{BASE_URL}/images/logo.png"

    def __init__(self, settings):
        self.settings = settings
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start(self):
        RESULTS.mkdir(exist_ok=True)
        DEBUG.mkdir(parents=True, exist_ok=True)
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.settings.headless,
            slow_mo=80 if self.settings.visible_browser else 0,
        )
        self.context = self.browser.new_context(viewport={"width": 1400, "height": 950})
        self.page = self.context.new_page()
        self.page.set_default_timeout(25000)

    def close(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def adjust_times(self, pickup_time, return_time):
        return _supported_time_text(pickup_time), _supported_time_text(return_time)

    def search(self, pickup, dropoff, pickup_time, return_time, index):
        days_elapsed = (dropoff - pickup).days
        actual_pickup_time, actual_return_time = self.adjust_times(pickup_time, return_time)
        try:
            self._search_site(pickup, dropoff, actual_pickup_time, actual_return_time)
            self.page.screenshot(path=str(DEBUG / f"payless_{index:03d}_results.png"), full_page=True)
            html = self.page.content()
            (DEBUG / f"payless_{index:03d}_results.html").write_text(html, encoding="utf-8")
            parser = PaylessFleetParser()
            vehicles = parser.parse(html)
            best = vehicles[0] if vehicles else None
            price = best["price"] if best else None
            rental_days = parser.rental_days
            daily = round(price / rental_days, 2) if price and rental_days else None
            return self.result(
                pickup,
                dropoff,
                actual_pickup_time,
                actual_return_time,
                days_elapsed,
                success=price is not None,
                vehicle=best["vehicle"] if best else None,
                vehicle_image=best["image_url"] if best else None,
                daily=daily,
                price=price,
                vehicles_found=len(vehicles),
                url=BOOKING_URL,
                status=f"OK EUR {price:.2f}" if price else "No vehicle price found",
                requested_pickup_time=pickup_time,
                requested_return_time=return_time,
            )
        except Exception as exc:
            try:
                self.page.screenshot(path=str(DEBUG / f"payless_{index:03d}_error.png"), full_page=True)
                (DEBUG / f"payless_{index:03d}_error.html").write_text(self.page.content(), encoding="utf-8")
            except Exception:
                pass
            return self.result(
                pickup,
                dropoff,
                actual_pickup_time,
                actual_return_time,
                days_elapsed,
                success=False,
                vehicle=None,
                vehicle_image=None,
                daily=None,
                price=None,
                vehicles_found=0,
                url=BOOKING_URL,
                status=f"ERROR: {type(exc).__name__}: {str(exc)[:160]}",
                requested_pickup_time=pickup_time,
                requested_return_time=return_time,
            )

    def _search_site(self, pickup, dropoff, pickup_time, return_time):
        self.page.goto(BOOKING_URL, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1200)
        self.page.select_option("#reservaOficinaEnt", FUERTEVENTURA_AIRPORT)
        self.page.select_option("#reservaOficinaDev", FUERTEVENTURA_AIRPORT)
        self.page.evaluate(
            """([pickupDate, dropoffDate]) => {
                document.querySelector("#fechaIni").value = pickupDate;
                document.querySelector("#fechaFin").value = dropoffDate;
            }""",
            [pickup.strftime("%d/%m/%Y"), dropoff.strftime("%d/%m/%Y")],
        )
        pickup_hour, pickup_minute = _supported_time(pickup_time)
        return_hour, return_minute = _supported_time(return_time)
        self.page.select_option("#horaIni", pickup_hour)
        self.page.select_option("#minutoIni", pickup_minute)
        self.page.select_option("#horaFin", return_hour)
        self.page.select_option("#minutoFin", return_minute)
        self.page.get_by_role("link", name="Continue").click()
        self.page.wait_for_url("**/booking2", timeout=25000)
        self.page.locator(".itemModelo").first.wait_for(timeout=25000)


class PaylessFleetParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.vehicles = []
        self.current = None
        self.div_depth = 0
        self.capture_price = False
        self.capture_name = False
        self.rental_days = None
        self._recent_text = ""

    def parse(self, html):
        self.feed(html)
        return sorted(self.vehicles, key=lambda vehicle: vehicle["price"])

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = _classes(attrs)

        if tag == "div" and "itemModelo" in classes:
            self.current = {"vehicle": None, "image_url": None, "price": None}
            self.div_depth = 1
            return

        if self.current and tag == "div":
            self.div_depth += 1

        if not self.current:
            return

        if tag == "span" and "precioSinFormato" in classes:
            self.capture_price = True
        elif tag == "span" and "nombreModeloSeleccionado" in classes:
            self.capture_name = True
        elif tag == "img" and not self.current.get("image_url"):
            src = attrs.get("src")
            if src:
                self.current["image_url"] = urljoin(BASE_URL, src)

    def handle_data(self, data):
        text = " ".join(data.split())
        if not text:
            return

        self._recent_text = f"{self._recent_text} {text}"[-300:]
        if self.rental_days is None:
            marker = "Final price for "
            if marker in self._recent_text and " days" in self._recent_text:
                after_marker = self._recent_text.split(marker, 1)[1]
                days = after_marker.split(" days", 1)[0].strip()
                if days.isdigit():
                    self.rental_days = int(days)

        if not self.current:
            return

        if self.capture_price:
            self.current["price"] = money(text)
        elif self.capture_name:
            self.current["vehicle"] = text

    def handle_endtag(self, tag):
        if self.current and tag == "div":
            self.div_depth -= 1
            if self.div_depth == 0:
                if self.current.get("vehicle") and self.current.get("price") is not None:
                    self.vehicles.append(self.current)
                self.current = None
                self.capture_price = False
                self.capture_name = False
                return

        if tag == "span":
            self.capture_price = False
            self.capture_name = False


def _classes(attrs):
    return set((attrs.get("class") or "").split())


def _supported_time(value):
    hour, minute = value.split(":", 1)
    minute_int = int(minute)
    if minute_int < 15:
        supported_minute = "00"
    elif minute_int < 30:
        supported_minute = "15"
    elif minute_int < 45:
        supported_minute = "30"
    else:
        supported_minute = "45"
    return hour, supported_minute


def _supported_time_text(value):
    hour, minute = _supported_time(value)
    return f"{int(hour):02d}:{minute}"
