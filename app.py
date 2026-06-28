import argparse
import re
import webbrowser
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

DAILY_RE = re.compile(r"([0-9]+(?:[,.][0-9]{2})?)\s*€\s*for\s*day", re.I)
TOTAL_DAYS_RE = re.compile(r"([0-9]+(?:[,.][0-9]{2})?)\s*€\s*for\s*[0-9]+\s*days?", re.I)

RESULTS = Path("results")
DEBUG = RESULTS / "debug"
RESULTS.mkdir(exist_ok=True)
DEBUG.mkdir(parents=True, exist_ok=True)

@dataclass
class Settings:
    start_date: date = date(2026, 8, 4)
    end_date: date = date(2026, 8, 22)
    min_days: int = 4
    max_days: int = 18
    pickup_time: str = "10:30"
    return_time: str = "17:30"
    final_return_time: str = "20:00"
    visible_browser: bool = True
    pluscar_airport_option: str = "30"  # Fuerteventura Airport

    @property
    def headless(self) -> bool:
        return not self.visible_browser

def money(raw: str) -> float:
    return float(raw.replace(",", "."))

def generate_combinations(settings: Settings, mode: str):
    if mode == "test":
        return [(settings.start_date, settings.start_date + timedelta(days=5), settings.pickup_time, settings.return_time)]

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

class PlusCar:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start(self):
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
                        if "€" not in line and "See more" not in line:
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
                    vehicles.append({
                        "vehicle": title,
                        "daily_price": daily,
                        "price": total,
                    })
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
            return {
                "provider": "PlusCar",
                "pickup": str(pickup),
                "dropoff": str(dropoff),
                "pickup_time": pickup_time,
                "return_time": return_time,
                "days_elapsed": days_elapsed,
                "success": price is not None,
                "vehicle": best["vehicle"] if best else None,
                "site_daily_rate": daily,
                "price": price,
                "effective_daily": round(price / days_elapsed, 2) if price else None,
                "site_rental_days": round(price / daily, 2) if price and daily else None,
                "vehicles_found": len(vehicles),
                "url": self.page.url,
                "status": f"OK €{price:.2f}" if price else "No vehicle price found",
            }
        except Exception as exc:
            try:
                self.page.screenshot(path=str(DEBUG / f"{index:03d}_error.png"), full_page=True)
                (DEBUG / f"{index:03d}_error.html").write_text(self.page.content(), encoding="utf-8")
            except Exception:
                pass
            return {
                "provider": "PlusCar",
                "pickup": str(pickup),
                "dropoff": str(dropoff),
                "pickup_time": pickup_time,
                "return_time": return_time,
                "days_elapsed": days_elapsed,
                "success": False,
                "vehicle": None,
                "site_daily_rate": None,
                "price": None,
                "effective_daily": None,
                "site_rental_days": None,
                "vehicles_found": 0,
                "url": self.page.url if self.page else "",
                "status": f"ERROR: {type(exc).__name__}: {str(exc)[:160]}",
            }

def write_report(rows):
    df = pd.DataFrame(rows)
    csv_path = RESULTS / "results.csv"
    xlsx_path = RESULTS / "results.xlsx"
    html_path = RESULTS / "report.html"
    df.to_csv(csv_path, index=False)
    try:
        df.to_excel(xlsx_path, index=False)
    except Exception:
        pass

    if not df.empty:
        df = df.sort_values(["success", "price"], ascending=[False, True], na_position="last")

    winner = ""
    good = df[df["success"] == True] if not df.empty else pd.DataFrame()
    if not good.empty:
        best = good.iloc[0]
        winner = f"""
        <section class='winner'>
          <div class='eyebrow'>🏆 Cheapest found</div>
          <h2>{best['provider']} · {best.get('vehicle', '')}</h2>
          <p>{best['pickup']} {best['pickup_time']} → {best['dropoff']} {best['return_time']}</p>
          <div class='price'>€{best['price']:.2f}</div>
          <p>Site daily: €{best['site_daily_rate']:.2f} · Effective daily: €{best['effective_daily']:.2f} · Vehicles found: {best['vehicles_found']}</p>
        </section>
        """

    html = f"""
    <!doctype html><html><head><meta charset='utf-8'><title>Canary Car Finder</title>
    <style>
      body {{ font-family: Arial, sans-serif; background:#f7f3ea; margin:32px; color:#1d1d1d; }}
      h1 {{ font-size:42px; }}
      .winner {{ background:#fffdf7; border:3px solid #1d1d1d; border-radius:16px; padding:24px; box-shadow:8px 8px 0 #d8c7a0; margin-bottom:28px; }}
      .eyebrow {{ font-weight:800; font-size:20px; }}
      .price {{ font-size:56px; font-weight:900; margin:12px 0; }}
      table {{ border-collapse:collapse; width:100%; background:white; }}
      th, td {{ border:1px solid #ddd; padding:9px; font-size:14px; }}
      th {{ background:#e8ddc8; text-align:left; }}
    </style></head><body>
    <h1>🏝 Canary Car Finder</h1>
    {winner}
    <h2>All results</h2>
    {df.to_html(index=False, escape=False)}
    </body></html>
    """
    html_path.write_text(html, encoding="utf-8")
    return html_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["test", "small", "full"], default="test")
    parser.add_argument("--hidden", action="store_true", help="Run browser hidden/headless")
    args = parser.parse_args()

    settings = Settings(visible_browser=not args.hidden)
    combos = generate_combinations(settings, args.mode)
    rows = []
    provider = PlusCar(settings)

    print(f"Canary Car Finder · PlusCar · {args.mode} · {len(combos)} searches")
    try:
        provider.start()
        for index, (pickup, dropoff, ptime, rtime) in enumerate(combos, start=1):
            print(f"[{index}/{len(combos)}] {pickup} {ptime} -> {dropoff} {rtime}")
            result = provider.search(pickup, dropoff, ptime, rtime, index)
            rows.append(result)
            print("   " + result["status"])
            write_report(rows)
    finally:
        provider.close()

    report = write_report(rows).resolve()
    print(f"Report: {report}")
    webbrowser.open(report.as_uri())

if __name__ == "__main__":
    main()
