from html import escape
from pathlib import Path

import pandas as pd

from app_config import load_app_config

RESULTS = Path("results")
EXPORT_COLUMNS = [
    "provider",
    "pickup",
    "dropoff",
    "pickup_time",
    "return_time",
    "days_elapsed",
    "success",
    "vehicle",
    "site_daily_rate",
    "price",
    "effective_daily",
    "site_rental_days",
    "vehicles_found",
    "url",
    "status",
]


def write_reports(rows, progress=None):
    RESULTS.mkdir(exist_ok=True)
    df = pd.DataFrame(rows)
    csv_path = RESULTS / "results.csv"
    xlsx_path = RESULTS / "results.xlsx"
    html_path = RESULTS / "report.html"

    export_columns = [column for column in EXPORT_COLUMNS if column in df.columns]
    export_df = df[export_columns] if export_columns else df
    export_df.to_csv(csv_path, index=False)
    try:
        export_df.to_excel(xlsx_path, index=False)
    except Exception:
        pass

    report_df = df
    if not report_df.empty:
        report_df = report_df.sort_values(["success", "price"], ascending=[False, True], na_position="last")

    html_path.write_text(_render_html(report_df, progress), encoding="utf-8")
    return csv_path, xlsx_path, html_path


def _render_html(df, progress):
    refresh = "<meta http-equiv='refresh' content='5'>" if _is_running(progress) else ""
    app_config = load_app_config()
    return f"""
    <!doctype html>
    <html lang='en'>
    <head>
      <meta charset='utf-8'>
      <meta name='viewport' content='width=device-width, initial-scale=1'>
      {refresh}
      <title>Canary Car Finder</title>
      <style>
        :root {{
          --ink:#16211f;
          --muted:#68716f;
          --line:#dde5e1;
          --soft:#f3f7f5;
          --panel:#ffffff;
          --accent:#0b7a75;
          --accent-2:#e5b94e;
          --coral:#d96d5f;
          --danger:#b64b4b;
          --shadow:0 16px 44px rgba(29, 45, 43, .12);
        }}
        * {{ box-sizing:border-box; }}
        body {{
          margin:0;
          color:var(--ink);
          background:linear-gradient(180deg, #eef6f3 0, #fbfcfb 360px);
          font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
        }}
        .shell {{ width:min(1180px, calc(100% - 32px)); margin:0 auto; padding:30px 0 46px; }}
        .topbar {{ display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:26px; }}
        .brand {{ display:flex; align-items:center; gap:12px; min-width:0; }}
        .mark {{ width:44px; height:44px; display:grid; place-items:center; border-radius:8px; background:var(--accent); color:white; font-weight:900; }}
        h1 {{ margin:0; font-size:clamp(28px, 4vw, 46px); line-height:1.02; letter-spacing:0; }}
        .subtitle {{ margin:7px 0 0; color:var(--muted); font-size:15px; }}
        .status-pill {{ border:1px solid var(--line); background:white; border-radius:999px; padding:9px 13px; font-weight:800; white-space:nowrap; }}
        .progress-panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; box-shadow:var(--shadow); padding:18px; margin-bottom:22px; }}
        .progress-head {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; margin-bottom:12px; }}
        .progress-title {{ font-weight:900; font-size:18px; }}
        .progress-copy {{ color:var(--muted); margin-top:4px; }}
        .meter {{ height:12px; overflow:hidden; background:#e8efec; border-radius:999px; }}
        .meter span {{ display:block; height:100%; width:var(--progress); background:linear-gradient(90deg, var(--accent), #21a391); border-radius:inherit; transition:width .25s ease; }}
        .stats {{ display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:12px; margin:18px 0 24px; }}
        .stat {{ background:rgba(255,255,255,.78); border:1px solid var(--line); border-radius:8px; padding:15px; }}
        .stat-label {{ color:var(--muted); font-size:12px; font-weight:800; text-transform:uppercase; }}
        .stat-value {{ margin-top:6px; font-size:24px; font-weight:900; }}
        .hero-card {{ display:grid; grid-template-columns:minmax(0, 1.35fr) minmax(280px, .65fr); gap:18px; align-items:stretch; margin-bottom:24px; }}
        .winner {{ background:#102623; color:white; border-radius:8px; padding:26px; box-shadow:var(--shadow); min-height:260px; display:flex; flex-direction:column; justify-content:space-between; }}
        .winner .eyebrow {{ color:#b9e4dc; font-size:13px; font-weight:900; text-transform:uppercase; }}
        .winner h2 {{ margin:10px 0 8px; font-size:30px; letter-spacing:0; }}
        .winner-meta {{ color:#d9e8e4; line-height:1.55; }}
        .winner-price {{ font-size:54px; font-weight:950; margin-top:18px; }}
        .side-panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:20px; }}
        .side-panel h2 {{ margin:0 0 12px; font-size:20px; }}
        .side-panel p {{ margin:0; color:var(--muted); line-height:1.5; }}
        .section-title {{ display:flex; align-items:end; justify-content:space-between; gap:12px; margin:22px 0 12px; }}
        .section-title h2 {{ margin:0; font-size:24px; }}
        .cards {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:16px; }}
        .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden; box-shadow:0 8px 24px rgba(29, 45, 43, .08); display:flex; flex-direction:column; min-height:100%; }}
        .media {{ position:relative; aspect-ratio:16/10; background:#dce7e3; display:grid; place-items:center; overflow:hidden; }}
        .media img {{ width:100%; height:100%; object-fit:cover; display:block; }}
        .placeholder {{ color:#58706b; font-size:44px; font-weight:950; }}
        .logo {{ position:absolute; top:12px; left:12px; width:42px; height:42px; border-radius:8px; background:white; border:1px solid rgba(0,0,0,.08); display:grid; place-items:center; overflow:hidden; box-shadow:0 6px 18px rgba(0,0,0,.16); }}
        .logo img {{ width:100%; height:100%; object-fit:contain; padding:6px; }}
        .logo span {{ font-weight:950; color:var(--accent); }}
        .badge {{ position:absolute; right:12px; top:12px; background:var(--accent-2); color:#2d2407; padding:7px 10px; border-radius:999px; font-size:12px; font-weight:900; }}
        .card-body {{ padding:16px; display:flex; flex-direction:column; gap:12px; flex:1; }}
        .card h3 {{ margin:0; font-size:20px; }}
        .route {{ color:var(--muted); font-size:14px; line-height:1.45; }}
        .price-line {{ display:flex; align-items:flex-end; justify-content:space-between; gap:12px; margin-top:auto; }}
        .price {{ font-size:34px; font-weight:950; }}
        .daily {{ color:var(--muted); font-size:13px; text-align:right; }}
        .comparison {{ border-top:1px solid var(--line); padding-top:12px; font-weight:900; color:var(--accent); }}
        .comparison.more {{ color:#835b00; }}
        .comparison.failed {{ color:var(--danger); }}
        .support {{ margin-top:24px; background:#fff7e8; border:1px solid #ead8b3; border-radius:8px; padding:22px; display:flex; align-items:center; justify-content:space-between; gap:18px; }}
        .support h2 {{ margin:0 0 6px; font-size:22px; }}
        .support p {{ margin:0; color:var(--muted); line-height:1.5; }}
        .support a {{ display:inline-block; background:var(--coral); color:white; text-decoration:none; font-weight:900; padding:12px 16px; border-radius:8px; white-space:nowrap; }}
        .table-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:8px; background:white; }}
        table {{ border-collapse:collapse; width:100%; min-width:980px; }}
        th, td {{ border-bottom:1px solid var(--line); padding:10px; text-align:left; font-size:13px; vertical-align:top; }}
        th {{ background:#eef4f1; font-size:12px; text-transform:uppercase; color:#4f5d59; }}
        tr:last-child td {{ border-bottom:0; }}
        @media (max-width:760px) {{
          .topbar, .progress-head, .section-title, .price-line {{ align-items:flex-start; flex-direction:column; }}
          .stats {{ grid-template-columns:repeat(2, minmax(0, 1fr)); }}
          .hero-card {{ grid-template-columns:1fr; }}
          .support {{ align-items:flex-start; flex-direction:column; }}
          .winner-price {{ font-size:42px; }}
        }}
      </style>
    </head>
    <body>
      <main class='shell'>
        <div class='topbar'>
          <div class='brand'>
            <div class='mark'>CC</div>
            <div>
              <h1>Canary Car Finder</h1>
              <p class='subtitle'>Live rental search results, sorted by the best confirmed price.</p>
            </div>
          </div>
          {_status_pill(progress)}
        </div>
        {_progress_html(progress)}
        {_stats_html(df)}
        {_hero_html(df)}
        <div class='section-title'>
          <h2>Booking Options</h2>
          <span class='subtitle'>{len(df)} searches recorded</span>
        </div>
        <section class='cards'>
          {_cards_html(df)}
        </section>
        <div class='section-title'>
          <h2>All Results</h2>
          <span class='subtitle'>CSV and Excel exports use this same source data.</span>
        </div>
        <div class='table-wrap'>
          {_table_html(df)}
        </div>
        {_support_html(df, app_config)}
      </main>
    </body>
    </html>
    """


def _is_running(progress):
    return progress and progress.get("status") == "running"


def _status_pill(progress):
    label = "Waiting to run"
    if progress:
        label = progress.get("label") or progress.get("status", label).title()
    return f"<div class='status-pill'>{escape(str(label))}</div>"


def _progress_html(progress):
    if not progress:
        return ""

    completed = int(progress.get("completed", 0))
    total = int(progress.get("total", 0))
    percent = round((completed / total) * 100) if total else 0
    message = escape(str(progress.get("message", "Preparing search")))
    return f"""
      <section class='progress-panel'>
        <div class='progress-head'>
          <div>
            <div class='progress-title'>{percent}% complete</div>
            <div class='progress-copy'>{message}</div>
          </div>
          <strong>{completed} / {total}</strong>
        </div>
        <div class='meter' style='--progress:{percent}%'><span></span></div>
      </section>
    """


def _stats_html(df):
    successful = _successful(df)
    best_price = successful["price"].min() if not successful.empty else None
    providers = df["provider"].nunique() if "provider" in df.columns and not df.empty else 0
    vehicles = successful["vehicles_found"].sum() if "vehicles_found" in successful.columns and not successful.empty else 0
    return f"""
      <section class='stats'>
        {_stat("Best Price", _format_euro(best_price))}
        {_stat("Successful Searches", str(len(successful)))}
        {_stat("Providers", str(providers))}
        {_stat("Vehicles Seen", str(int(vehicles)))}
      </section>
    """


def _stat(label, value):
    return f"<div class='stat'><div class='stat-label'>{escape(label)}</div><div class='stat-value'>{value}</div></div>"


def _hero_html(df):
    successful = _successful(df)
    if successful.empty:
        return """
          <section class='hero-card'>
            <div class='winner'>
              <div>
                <div class='eyebrow'>Search in progress</div>
                <h2>No confirmed prices yet</h2>
                <p class='winner-meta'>Results will appear here as each provider completes a search.</p>
              </div>
              <div class='winner-price'>--</div>
            </div>
            <aside class='side-panel'><h2>Dashboard</h2><p>The report refreshes while searches are running and keeps CSV/XLSX exports unchanged.</p></aside>
          </section>
        """

    best = successful.iloc[0]
    return f"""
      <section class='hero-card'>
        <div class='winner'>
          <div>
            <div class='eyebrow'>Cheapest confirmed option</div>
            <h2>{escape(_text(best.get("vehicle"), "Vehicle unavailable"))}</h2>
            <p class='winner-meta'>{escape(_text(best.get("provider"), "Provider"))} from {escape(_text(best.get("pickup"), ""))} {escape(_text(best.get("pickup_time"), ""))} to {escape(_text(best.get("dropoff"), ""))} {escape(_text(best.get("return_time"), ""))}</p>
          </div>
          <div class='winner-price'>{_format_euro(best.get("price"))}</div>
        </div>
        <aside class='side-panel'>
          <h2>Why this leads</h2>
          <p>Cards below compare every successful search against this cheapest option, with higher prices called out immediately.</p>
        </aside>
      </section>
    """


def _cards_html(df):
    if df.empty:
        return "<article class='card'><div class='card-body'><h3>No results yet</h3><p class='route'>The first completed provider search will create a booking card here.</p></div></article>"

    successful = _successful(df)
    cheapest = successful["price"].min() if not successful.empty else None
    next_cheapest = None
    if len(successful) > 1:
        next_cheapest = successful.iloc[1].get("price")
    return "\n".join(_card_html(row, cheapest, next_cheapest) for _, row in df.iterrows())


def _card_html(row, cheapest, next_cheapest):
    success = row.get("success") == True
    price = row.get("price")
    provider = _text(row.get("provider"), "Provider")
    vehicle = _text(row.get("vehicle"), "Vehicle unavailable")
    image = row.get("_vehicle_image")
    logo = row.get("_provider_logo")
    badge = "<div class='badge'>Best price</div>" if success and price == cheapest else ""
    comparison = _comparison(price, cheapest, next_cheapest, success)
    return f"""
      <article class='card'>
        <div class='media'>
          {_image_html(image, vehicle)}
          {_logo_html(logo, provider)}
          {badge}
        </div>
        <div class='card-body'>
          <div>
            <h3>{escape(vehicle)}</h3>
            <div class='route'>{escape(provider)} &middot; {escape(_text(row.get("pickup"), ""))} {escape(_text(row.get("pickup_time"), ""))} to {escape(_text(row.get("dropoff"), ""))} {escape(_text(row.get("return_time"), ""))}</div>
          </div>
          <div class='price-line'>
            <div class='price'>{_format_euro(price) if success else "No price"}</div>
            <div class='daily'>Daily<br>{_format_euro(row.get("effective_daily"))}</div>
          </div>
          {comparison}
        </div>
      </article>
    """


def _image_html(src, alt):
    if pd.isna(src) or not src:
        return f"<div class='placeholder'>{escape(_initials(alt))}</div>"
    return f"<img src='{escape(str(src), quote=True)}' alt='{escape(alt, quote=True)}'>"


def _logo_html(src, provider):
    if pd.isna(src) or not src:
        return f"<div class='logo'><span>{escape(_initials(provider))}</span></div>"
    return f"<div class='logo'><img src='{escape(str(src), quote=True)}' alt='{escape(provider, quote=True)} logo'></div>"


def _comparison(price, cheapest, next_cheapest, success):
    if not success:
        return "<div class='comparison failed'>Search did not return a price</div>"
    if pd.isna(cheapest) or pd.isna(price):
        return "<div class='comparison'>Awaiting comparison</div>"
    delta = float(price) - float(cheapest)
    if delta <= 0.009:
        if not pd.isna(next_cheapest) and float(next_cheapest) - float(price) > 0.009:
            return f"<div class='comparison'>Saves {_format_euro(float(next_cheapest) - float(price))} vs next option</div>"
        return "<div class='comparison'>Cheapest option found</div>"
    return f"<div class='comparison more'>Cheapest saves {_format_euro(delta)} vs this option</div>"


def _table_html(df):
    export_columns = [column for column in EXPORT_COLUMNS if column in df.columns]
    table_df = df[export_columns] if export_columns else df
    return table_df.to_html(index=False, escape=False)


def _support_html(df, app_config):
    donation_url = app_config.get("donation_url")
    button = ""
    if donation_url:
        button = f"<a href='{escape(str(donation_url), quote=True)}'>🍺 Buy me an Estrella</a>"

    message = (
        "If Canary Car Finder helped you find a cheaper hire car, consider buying me an Estrella. "
        "Every donation helps keep the application free and supports future improvements."
    )
    saving = _saving_vs_most_expensive(df)
    if saving and saving > 0.009:
        message = f"You saved {_format_euro(saving)} today. Fancy buying me one Estrella? 🍺"

    return f"""
      <section class='support'>
        <div>
          <h2>🍺 Saved money?</h2>
          <p>{message}</p>
        </div>
        {button}
      </section>
    """


def _successful(df):
    if df.empty or "success" not in df.columns:
        return pd.DataFrame()
    successful = df[df["success"] == True]
    if successful.empty:
        return successful
    return successful.sort_values(["price"], ascending=True, na_position="last")


def _saving_vs_most_expensive(df):
    successful = _successful(df)
    if successful.empty or "price" not in successful.columns or len(successful) < 2:
        return None
    return float(successful["price"].max()) - float(successful["price"].min())


def _format_euro(value):
    return "N/A" if pd.isna(value) else f"&euro;{float(value):.2f}"


def _text(value, fallback):
    return fallback if pd.isna(value) or value is None else str(value)


def _initials(value):
    words = [part for part in str(value).replace("-", " ").split() if part]
    return "".join(word[0].upper() for word in words[:2]) or "CC"
