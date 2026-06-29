import re
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from .base import CarProvider

RESULTS = Path("results")
DEBUG = RESULTS / "debug"
EURO = chr(8364)

DAILY_RE = re.compile(r"([0-9]+(?:[,.][0-9]{2})?)\s*" + re.escape(EURO) + r"\s*for\s*day", re.I)
TOTAL_DAYS_RE = re.compile(
    r"([0-9]+(?:[,.][0-9]{2})?)\s*" + re.escape(EURO) + r"\s*for\s*[0-9]+\s*days?",
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
        self.page.goto("https://www.pluscarcanarias.com/en/home/", wait_until="domcontentloaded")
        self.page.wait_for_timeout(800)
        self.accept_cookies()
        self.page.get_by_label("Pick up at Office").select_option(self.settings.pluscar_airport_option)

    def accept_cookies(self):
        for name in ["Permitir todas", re.compile("permitir todas", re.I), re.compile("accept|allow", re.I)]:
            try:
                self.page.get_by_role("button", name=name).click(timeout=2500)
                self.page.wait_for_timeout(500)
                return
            except Exception:
                pass

    def scrape_vehicles(self):
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
            if "/en/home" not in self.page.url:
                self.go_home()

            self.page.get_by_role("textbox", name="Pick-up date").fill(pickup.isoformat())
            self.page.get_by_label("Hora recogida").select_option(pickup_time)
            try:
                self.page.get_by_text("+").click(timeout=1500)
            except Exception:
                pass
            self.page.get_by_role("textbox", name="Return date").fill(dropoff.isoformat())
            self.page.locator("#hora_fin").select_option(return_time)
            self.page.screenshot(path=str(DEBUG / f"{index:03d}_filled.png"), full_page=True)
            self.page.get_by_role("button", name="Search").click()
            self.page.locator("article.swi_product").first.wait_for(timeout=20000)
            self.page.screenshot(path=str(DEBUG / f"{index:03d}_results.png"), full_page=True)
            (DEBUG / f"{index:03d}_results.html").write_text(self.page.content(), encoding="utf-8")

            vehicles = self.scrape_vehicles()
            best = vehicles[0] if vehicles else None
            price = best["price"] if best else None
            daily = best["daily_price"] if best else None
            return self._result(
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
            return self._result(
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
                url=self.page.url if self.page else "",
                status=f"ERROR: {type(exc).__name__}: {str(exc)[:160]}",
            )

    def _result(
        self,
        pickup,
        dropoff,
        pickup_time,
        return_time,
        days_elapsed,
        success,
        vehicle,
        vehicle_image,
        daily,
        price,
        vehicles_found,
        url,
        status,
    ):
        return {
            "provider": self.name,
            "pickup": str(pickup),
            "dropoff": str(dropoff),
            "pickup_time": pickup_time,
            "return_time": return_time,
            "days_elapsed": days_elapsed,
            "success": success,
            "vehicle": vehicle,
            "_vehicle_image": vehicle_image,
            "_provider_logo": self.logo_url,
            "site_daily_rate": daily,
            "price": price,
            "effective_daily": round(price / days_elapsed, 2) if price else None,
            "site_rental_days": round(price / daily, 2) if price and daily else None,
            "vehicles_found": vehicles_found,
            "url": url,
            "status": status,
        }

    def _vehicle_image(self, card):
        try:
            src = card.locator("img").first.get_attribute("src", timeout=1000)
            return urljoin(self.page.url, src) if src else None
        except Exception:
            return None
