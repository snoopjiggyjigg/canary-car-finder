import re
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from .base import CarProvider

RESULTS = Path("results")
DEBUG = RESULTS / "debug"
EURO = chr(8364)
HOME_URL = "https://www.pluscarcanarias.com/inicio/"
RESULTS_PATH = "/vehiculos-disponibles-v2/"

DAILY_RE = re.compile(
    r"([0-9]+(?:[,.][0-9]{2})?)\s*"
    + re.escape(EURO)
    + r"\s*(?:for\s*day|por\s*d[ií]a|/\s*d[ií]a)",
    re.I,
)
TOTAL_DAYS_RE = re.compile(
    r"([0-9]+(?:[,.][0-9]{2})?)\s*"
    + re.escape(EURO)
    + r"\s*(?:for|por)\s*[0-9]+\s*(?:days?|d[ií]as?)",
    re.I,
)


def money(raw: str) -> float:
    return float(raw.replace(",", "."))


class PlusCarProvider(CarProvider):
    name = "PlusCar"
    logo_url = "https://www.pluscarcanarias.com/favicon.ico"

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
        self.page.set_default_timeout(20000)
        self.go_home()

    def close(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def go_home(self):
        self.page.goto(HOME_URL, wait_until="domcontentloaded")
        self.page.wait_for_timeout(800)
        self.accept_cookies()
        self.page.locator("#oficina_recogida").select_option(self.settings.pluscar_airport_option)

    def accept_cookies(self):
        for name in ["Permitir todas", re.compile("permitir todas", re.I), re.compile("accept|allow", re.I)]:
            try:
                self.page.get_by_role("button", name=name).click(timeout=2500)
                self.page.wait_for_timeout(500)
                return
            except Exception:
                pass

    def scrape_vehicles(self, rental_days=None):
        vehicles = []
        cards = self.page.locator("article.swi_product")
        for i in range(cards.count()):
            card = cards.nth(i)
            try:
                text = card.inner_text(timeout=2500)
                title = "Unknown vehicle"
                try:
                    title = card.locator(".swi_product_title").inner_text(timeout=1000).strip()
                except Exception:
                    for line in [x.strip() for x in text.splitlines() if x.strip()]:
                        if EURO not in line and "See more" not in line:
                            title = line
                            break

                daily = None
                total = None
                daily_match = DAILY_RE.search(text)
                total_match = TOTAL_DAYS_RE.search(text)
                if daily_match:
                    daily = money(daily_match.group(1))
                if total_match:
                    total = money(total_match.group(1))
                if total is None and daily is not None and rental_days:
                    total = round(daily * rental_days, 2)

                if total is not None:
                    vehicles.append(
                        {
                            "vehicle": title,
                            "image_url": self._vehicle_image(card),
                            "daily_price": daily,
                            "price": total,
                        }
                    )
            except Exception:
                continue
        return sorted(vehicles, key=lambda v: v["price"])

    def search(self, pickup, dropoff, pickup_time, return_time, index):
        days_elapsed = (dropoff - pickup).days
        try:
            if "/inicio" not in self.page.url:
                self.go_home()

            self.page.locator("#fecha_inicio").fill(pickup.isoformat())
            self.page.locator("#hora_inicio").select_option(pickup_time)
            try:
                self.page.get_by_text("+").click(timeout=1500)
            except Exception:
                pass
            self.page.locator("#fecha_fin").fill(dropoff.isoformat())
            self.page.locator("#hora_fin").select_option(return_time)
            self.page.screenshot(path=str(DEBUG / f"{index:03d}_filled.png"), full_page=True)
            self.page.locator(".swi_select_ofi_btn").click()
            self._validate_results_page(index)
            self.page.locator("article.swi_product").first.wait_for(timeout=20000)
            self.page.screenshot(path=str(DEBUG / f"{index:03d}_results.png"), full_page=True)
            (DEBUG / f"{index:03d}_results.html").write_text(self.page.content(), encoding="utf-8")

            vehicles = self.scrape_vehicles(self._provider_rental_days())
            best = vehicles[0] if vehicles else None
            price = best["price"] if best else None
            daily = best["daily_price"] if best else None
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
                url=self.page.url,
                status=f"OK {EURO}{price:.2f}" if price else "No vehicle price found",
            )
        except Exception as exc:
            try:
                self.page.screenshot(path=str(DEBUG / f"{index:03d}_error.png"), full_page=True)
                (DEBUG / f"{index:03d}_error.html").write_text(self.page.content(), encoding="utf-8")
            except Exception:
                pass
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
                url=self.page.url if self.page else HOME_URL,
                status=f"ERROR: {type(exc).__name__}: {str(exc)[:160]}",
            )

    def _validate_results_page(self, index):
        try:
            self.page.wait_for_url(f"**{RESULTS_PATH}", timeout=12000)
        except Exception:
            self._save_unexpected_url_debug(index)
            raise RuntimeError(f"PlusCar did not reach expected results page. Final URL: {self.page.url}")

    def _save_unexpected_url_debug(self, index):
        prefix = DEBUG / f"{index:03d}_unexpected_url"
        try:
            self.page.screenshot(path=str(prefix.with_suffix(".png")), full_page=True)
        except Exception:
            pass
        try:
            prefix.with_suffix(".html").write_text(self.page.content(), encoding="utf-8")
        except Exception:
            pass
        try:
            prefix.with_suffix(".txt").write_text(f"Final URL: {self.page.url}\n", encoding="utf-8")
        except Exception:
            pass

    def _provider_rental_days(self):
        try:
            return self.page.evaluate(
                """() => {
                    const reserva = JSON.parse(sessionStorage.getItem("swi_reserva") || "{}");
                    return Number(reserva.num_dias) || null;
                }"""
            )
        except Exception:
            return None

    def _vehicle_image(self, card):
        try:
            src = card.locator("img").first.get_attribute("src", timeout=1000)
            return urljoin(self.page.url, src) if src else None
        except Exception:
            return None
