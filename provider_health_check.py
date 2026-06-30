import argparse
import html
import json
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from app_config import APP_VERSION
from providers import AutoReisenProvider, CicarProvider, PaylessProvider, PlusCarProvider
from settings import load_settings


RESULTS = Path("results")
DEBUG = RESULTS / "debug"
REPORT = RESULTS / "provider_health_report.html"
SUMMARY_JSON = RESULTS / "provider_health_summary.json"
PICKUP = date(2026, 8, 4)
DROPOFF = date(2026, 8, 11)
PICKUP_TIME = "10:30"
RETURN_TIME = "17:30"


@dataclass
class ProviderCheck:
    name: str
    passed: bool
    opened: bool
    searched: bool
    vehicles_found: int
    best_vehicle: str
    best_price: float | None
    booking_url: str
    status: str
    error: str
    timestamp: str
    debug_dir: Path | None = None


def main():
    parser = argparse.ArgumentParser(description="Validate all Canary car hire providers.")
    parser.add_argument("--no-report", action="store_true", help="Do not write the HTML report.")
    args = parser.parse_args()

    RESULTS.mkdir(exist_ok=True)
    DEBUG.mkdir(parents=True, exist_ok=True)

    settings = load_settings()
    settings.visible_browser = False

    providers = [
        PlusCarProvider(settings),
        AutoReisenProvider(),
        CicarProvider(),
        PaylessProvider(settings),
    ]

    checks = []
    print("")
    print("-----------------------------------")
    print("Provider Health Check")
    print("-----------------------------------")
    for index, provider in enumerate(providers, start=1):
        check = run_provider_check(provider, index)
        checks.append(check)
        print_provider_summary(check)

    if not args.no_report:
        write_report(checks)
        write_summary(checks)
        print(f"HTML report: {REPORT}")

    passed = sum(1 for check in checks if check.passed)
    total = len(checks)
    print("")
    print("Overall")
    print(f"{passed}/{total} providers healthy")
    return 0 if passed == total else 1


def run_provider_check(provider, index):
    name = provider.name
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console_messages = []
    opened = False
    searched = False
    result = None
    error = ""

    debug_dir = None
    try:
        provider.start()
        opened = True
        attach_console_capture(provider, console_messages)
        result = provider.search(PICKUP, DROPOFF, PICKUP_TIME, RETURN_TIME, 900 + index)
        searched = True
    except Exception as exc:
        error = f"{type(exc).__name__}: {str(exc)[:220]}"
    finally:
        passed, failure_reason = evaluate_result(result, error)
        if not passed:
            error = error or failure_reason
            debug_dir = save_failure_debug(provider, name, console_messages, result, error)
        try:
            provider.close()
        except Exception:
            pass

    return ProviderCheck(
        name=name,
        passed=passed,
        opened=opened,
        searched=searched,
        vehicles_found=int((result or {}).get("vehicles_found") or 0),
        best_vehicle=str((result or {}).get("vehicle") or ""),
        best_price=(result or {}).get("price"),
        booking_url=str((result or {}).get("url") or ""),
        status=str((result or {}).get("status") or ""),
        error=error,
        timestamp=timestamp,
        debug_dir=debug_dir,
    )


def attach_console_capture(provider, console_messages):
    page = getattr(provider, "page", None)
    if not page:
        return
    try:
        page.on("console", lambda message: console_messages.append(f"{message.type}: {message.text}"))
        page.on("pageerror", lambda error: console_messages.append(f"pageerror: {error}"))
    except Exception:
        pass


def evaluate_result(result, error):
    if error:
        return False, error
    if not result:
        return False, "Provider did not return a result."
    if not result.get("success"):
        return False, result.get("status") or "Provider returned an unsuccessful result."
    if int(result.get("vehicles_found") or 0) < 1:
        return False, "No vehicles found."
    if result.get("price") is None:
        return False, "No price extracted."
    if not result.get("url"):
        return False, "No booking URL generated."
    status = str(result.get("status") or "")
    if status.upper().startswith("ERROR"):
        return False, status
    return True, ""


def save_failure_debug(provider, name, console_messages, result, error):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_dir = DEBUG / safe_name(name) / stamp
    debug_dir.mkdir(parents=True, exist_ok=True)

    page = getattr(provider, "page", None)
    if page:
        try:
            page.screenshot(path=str(debug_dir / "screenshot.png"), full_page=True)
        except Exception:
            pass
        try:
            (debug_dir / "page.html").write_text(page.content(), encoding="utf-8")
        except Exception:
            pass
        try:
            (debug_dir / "final_url.txt").write_text(page.url or "", encoding="utf-8")
        except Exception:
            pass
        try:
            (debug_dir / "page_title.txt").write_text(page.title() or "", encoding="utf-8")
        except Exception:
            pass
    else:
        copy_latest_provider_html(name, debug_dir)
        (debug_dir / "final_url.txt").write_text(str((result or {}).get("url") or ""), encoding="utf-8")
        (debug_dir / "page_title.txt").write_text("", encoding="utf-8")

    console_text = "\n".join(console_messages)
    if error:
        console_text = f"{console_text}\nERROR: {error}".strip()
    (debug_dir / "console.txt").write_text(console_text, encoding="utf-8")
    return debug_dir


def copy_latest_provider_html(name, debug_dir):
    prefix = safe_name(name)
    candidates = sorted(
        DEBUG.glob(f"{prefix}_*_results.html"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        shutil.copy2(candidates[0], debug_dir / "page.html")
    else:
        (debug_dir / "page.html").write_text("", encoding="utf-8")


def print_provider_summary(check):
    marker = "PASS" if check.passed else "FAIL"
    print("")
    print("--------------------")
    print(f"{check.name}")
    print(f"Vehicles: {check.vehicles_found}")
    if check.best_vehicle:
        print(f"Best: {check.best_vehicle}")
    if check.best_price is not None:
        print(f"EUR {check.best_price:.2f}")
    print(marker)
    if not check.passed:
        print(f"Reason: {check.error}")
        if check.debug_dir:
            print(f"Debug: {check.debug_dir}")


def write_report(checks):
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = "\n".join(report_row(check) for check in checks)
    REPORT.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Provider Health Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #102030; background: #f7fbfd; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color: #52616f; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 8px 24px rgba(16, 32, 48, .08); }}
    th, td {{ text-align: left; padding: 12px 14px; border-bottom: 1px solid #e6eef3; vertical-align: top; }}
    th {{ background: #eaf6fb; }}
    .pass {{ color: #0f7b45; font-weight: bold; }}
    .fail {{ color: #b42318; font-weight: bold; }}
    a {{ color: #0b6898; }}
    .small {{ color: #52616f; font-size: 13px; }}
  </style>
</head>
<body>
  <h1>Provider Health Report</h1>
  <div class="meta">Generated {html.escape(generated)} | Build version {html.escape(APP_VERSION)}</div>
  <table>
    <thead>
      <tr>
        <th>Provider</th>
        <th>Status</th>
        <th>Vehicles Found</th>
        <th>Best Price</th>
        <th>Best Vehicle</th>
        <th>Timestamp</th>
        <th>Diagnostics</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>
""",
        encoding="utf-8",
    )


def write_summary(checks):
    passed = sum(1 for check in checks if check.passed)
    data = {
        "version": APP_VERSION,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(checks),
        "passed": passed,
        "failed": len(checks) - passed,
        "providers": [
            {
                "name": check.name,
                "status": "PASS" if check.passed else "FAIL",
                "vehicles_found": check.vehicles_found,
                "best_vehicle": check.best_vehicle,
                "best_price": check.best_price,
                "booking_url": check.booking_url,
                "error": check.error,
                "debug_dir": str(check.debug_dir) if check.debug_dir else "",
            }
            for check in checks
        ],
    }
    SUMMARY_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")


def report_row(check):
    status_class = "pass" if check.passed else "fail"
    status = "PASS" if check.passed else "FAIL"
    price = f"EUR {check.best_price:.2f}" if check.best_price is not None else ""
    diagnostics = ""
    if check.debug_dir:
        screenshot = check.debug_dir / "screenshot.png"
        page = check.debug_dir / "page.html"
        links = []
        if screenshot.exists():
            screenshot_href = report_href(screenshot)
            links.append(
                f"<a href='{html.escape(screenshot_href)}'>"
                f"<img src='{html.escape(screenshot_href)}' alt='Failure screenshot' style='max-width:160px;display:block;margin-bottom:6px'>"
                "Screenshot</a>"
            )
        if page.exists():
            links.append(f"<a href='{html.escape(report_href(page))}'>HTML</a>")
        diagnostics = " | ".join(links) or html.escape(str(check.debug_dir))
    if check.error:
        diagnostics = f"{diagnostics}<div class='small'>{html.escape(check.error)}</div>"
    return f"""<tr>
  <td>{html.escape(check.name)}</td>
  <td class="{status_class}">{status}</td>
  <td>{check.vehicles_found}</td>
  <td>{html.escape(price)}</td>
  <td>{html.escape(check.best_vehicle)}</td>
  <td>{html.escape(check.timestamp)}</td>
  <td>{diagnostics}</td>
</tr>"""


def safe_name(value):
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")


def report_href(path):
    try:
        return path.relative_to(REPORT.parent).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
