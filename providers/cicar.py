import re
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.parse import urlencode, urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener

from .base import CarProvider

RESULTS = Path("results")
DEBUG = RESULTS / "debug"
BASE_URL = "https://www.cicar.com"
HOME_URL = f"{BASE_URL}/en"
AJAX_URL = f"{BASE_URL}/EN/action/ajaxBooking1"
BOOKING_URL = f"{BASE_URL}/EN/action/booking2"
FUERTEVENTURA_ZONE = "FUE"
FUERTEVENTURA_AIRPORT = "F3"


def money(raw: str) -> float:
    return float(raw.replace(".", "").replace(",", "."))


class CicarProvider(CarProvider):
    name = "Cicar"
    logo_url = f"{BASE_URL}/html/images/logo-cicar.png"

    def __init__(self):
        self.opener = None

    def start(self):
        RESULTS.mkdir(exist_ok=True)
        DEBUG.mkdir(parents=True, exist_ok=True)
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self._request(HOME_URL)

    def close(self):
        self.opener = None

    def search(self, pickup, dropoff, pickup_time, return_time, index):
        days_elapsed = (dropoff - pickup).days
        actual_pickup_time = _supported_time(pickup_time)
        actual_return_time = _supported_time(return_time)
        try:
            html = self._quote_html(pickup, dropoff, actual_pickup_time, actual_return_time)
            (DEBUG / f"cicar_{index:03d}_results.html").write_text(html, encoding="utf-8")
            parser = CicarFleetParser()
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
                url=best["booking_url"] if best else BOOKING_URL,
                status=f"OK EUR {price:.2f}" if price else "No vehicle price found",
                requested_pickup_time=pickup_time,
                requested_return_time=return_time,
            )
        except Exception as exc:
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

    def _quote_html(self, pickup, dropoff, pickup_time, return_time):
        body = self._body(pickup, dropoff, pickup_time, return_time)
        check = self._post(AJAX_URL, body)
        if check.strip() != "OK":
            raise RuntimeError(f"Cicar rejected search: {check[:160]}")
        return self._post(BOOKING_URL, body)

    def _body(self, pickup, dropoff, pickup_time, return_time):
        pickup_hour, pickup_minute = pickup_time.split(":", 1)
        return_hour, return_minute = return_time.split(":", 1)
        return {
            "zona": FUERTEVENTURA_ZONE,
            "zonadev": FUERTEVENTURA_ZONE,
            "reservaIsla": "Fuerteventura",
            "reservaOficinaEnt": FUERTEVENTURA_AIRPORT,
            "reservaOficinaDev": FUERTEVENTURA_AIRPORT,
            "fechaIni": pickup.strftime("%d/%m/%Y"),
            "horaIni": pickup_hour,
            "minutoIni": _supported_minute(pickup_minute),
            "fechaFin": dropoff.strftime("%d/%m/%Y"),
            "horaFin": return_hour,
            "minutoFin": _supported_minute(return_minute),
            "entregaHotelEnt": "off",
            "entregaHotelDev": "off",
        }

    def _post(self, url, body):
        data = urlencode(body).encode("utf-8")
        request = Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": HOME_URL,
                "User-Agent": "CanaryCarFinder/1.0",
            },
        )
        return self._request(request)

    def _request(self, request):
        with self.opener.open(request, timeout=60) as response:
            return response.read().decode("utf-8", errors="replace")


class CicarFleetParser(HTMLParser):
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

        if tag == "div" and "thumbnailcoche" in classes:
            self.current = {
                "vehicle": None,
                "image_url": None,
                "price": None,
                "booking_url": BOOKING_URL,
            }
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
        elif tag == "img" and "imagenModelo" in classes:
            src = attrs.get("src")
            if src:
                self.current["image_url"] = urljoin(BASE_URL, src)
        elif tag == "a":
            href = attrs.get("href")
            if href and "modelView" in href:
                self.current["booking_url"] = urljoin(BASE_URL, href)

    def handle_data(self, data):
        text = " ".join(data.split())
        if not text:
            return

        self._recent_text = f"{self._recent_text} {text}"[-300:]
        if self.rental_days is None:
            match = re.search(r"Final price for\s+([0-9]+)\s+days", self._recent_text, re.I)
            if match:
                self.rental_days = int(match.group(1))

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


def _supported_minute(value):
    return "30" if int(value) >= 30 else "00"


def _supported_time(value):
    hour, minute = value.split(":", 1)
    return f"{int(hour):02d}:{_supported_minute(minute)}"
