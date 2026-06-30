import json
from html import escape
from pathlib import Path

import pandas as pd

from app_config import load_app_config

RESULTS = Path("results")
PROVIDER_ORDER = {"PlusCar": 0, "AutoReisen": 1, "Cicar": 2, "Payless Car": 3}
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
        report_df = report_df.sort_values(
            ["success", "price", "effective_daily"],
            ascending=[False, True, True],
            na_position="last",
        )

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
        .shell {{ width:min(1180px, calc(100% - 36px)); margin:0 auto; padding:34px 0 54px; }}
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
        .meter span {{ display:block; height:100%; width:var(--progress); background:linear-gradient(90deg, var(--accent), #21a391); border-radius:inherit; transition:width .25s ease; position:relative; overflow:hidden; }}
        .meter span:after {{ content:""; position:absolute; inset:0; background:linear-gradient(90deg, transparent, rgba(255,255,255,.35), transparent); animation:shine 1.2s linear infinite; }}
        @keyframes shine {{ from {{ transform:translateX(-100%); }} to {{ transform:translateX(100%); }} }}
        .stats {{ display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:12px; margin:18px 0 24px; }}
        .stat {{ background:rgba(255,255,255,.78); border:1px solid var(--line); border-radius:8px; padding:15px; }}
        .stat-label {{ color:var(--muted); font-size:12px; font-weight:800; text-transform:uppercase; }}
        .stat-value {{ margin-top:6px; font-size:24px; font-weight:900; }}
        .filters {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; box-shadow:0 14px 36px rgba(29, 45, 43, .10); padding:16px; margin:20px 0 22px; }}
        .filter-grid {{ display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:12px; }}
        .filter-field label {{ display:block; color:var(--muted); font-size:12px; font-weight:900; text-transform:uppercase; margin-bottom:6px; }}
        .filter-field select, .filter-field input {{ width:100%; min-height:40px; border:1px solid var(--line); border-radius:8px; background:#fbfdfc; color:var(--ink); padding:8px 10px; font:inherit; }}
        .price-range {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; }}
        .filter-toggle {{ display:flex; align-items:center; gap:9px; color:var(--ink); font-weight:800; margin-top:12px; }}
        .filter-toggle input {{ width:18px; height:18px; accent-color:var(--accent); }}
        .live-summary {{ display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:10px; margin-top:14px; }}
        .live-summary div {{ background:var(--soft); border:1px solid var(--line); border-radius:8px; padding:11px; }}
        .live-summary span {{ display:block; color:var(--muted); font-size:11px; font-weight:900; text-transform:uppercase; }}
        .live-summary strong {{ display:block; margin-top:4px; font-size:18px; }}
        .is-hidden {{ display:none !important; }}
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
        .best-table {{ overflow:auto; border:1px solid var(--line); border-radius:8px; background:white; box-shadow:0 14px 36px rgba(29, 45, 43, .12); margin-bottom:28px; }}
        .best-table table {{ min-width:1060px; }}
        .book {{ display:inline-block; background:var(--accent); color:white; text-decoration:none; font-weight:900; padding:8px 11px; border-radius:8px; white-space:nowrap; }}
        .book-note {{ margin-top:7px; color:var(--muted); font-size:12px; line-height:1.4; }}
        .time-pair {{ display:inline-block; line-height:1.35; font-size:13px; color:var(--muted); }}
        .source {{ display:inline-block; border-radius:999px; padding:5px 9px; font-size:11px; font-weight:900; letter-spacing:.02em; }}
        .source.live {{ background:#e1f4ea; color:#0d6b3a; }}
        .source.cache {{ background:#e9eef8; color:#34508a; }}
        .calendar {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(120px, 1fr)); gap:10px; margin-bottom:24px; }}
        .calendar a {{ border:1px solid var(--line); border-radius:8px; padding:12px; color:var(--ink); text-decoration:none; background:white; }}
        .calendar .green {{ background:#e1f4ea; border-color:#9bd3b1; }}
        .calendar .yellow {{ background:#fff4ce; border-color:#e1c96e; }}
        .calendar .red {{ background:#ffe2dd; border-color:#e8a198; }}
        .cal-date {{ font-weight:900; }}
        .cal-price {{ color:var(--muted); margin-top:5px; font-size:13px; }}
        .cards {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:16px; }}
        .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; overflow:hidden; box-shadow:0 8px 24px rgba(29, 45, 43, .08); display:flex; flex-direction:column; min-height:100%; }}
        .card.cheapest {{ border-color:#0b7a75; box-shadow:0 12px 30px rgba(11,122,117,.18); }}
        .card.near10 {{ border-color:#64b783; }}
        .card.near25 {{ border-color:#e1b84f; }}
        .card.above25 {{ border-color:#dd8d84; }}
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
        .support.secondary {{ margin-top:14px; background:#f5faf9; border-color:var(--line); }}
        .support.secondary a {{ background:var(--accent); }}
        .table-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:8px; background:white; }}
        table {{ border-collapse:collapse; width:100%; min-width:980px; }}
        th, td {{ border-bottom:1px solid var(--line); padding:13px; text-align:left; font-size:14px; vertical-align:top; }}
        th {{ background:#eef4f1; font-size:12px; text-transform:uppercase; color:#4f5d59; }}
        tr:last-child td {{ border-bottom:0; }}
        @media (max-width:760px) {{
          .topbar, .progress-head, .section-title, .price-line {{ align-items:flex-start; flex-direction:column; }}
          .stats {{ grid-template-columns:repeat(2, minmax(0, 1fr)); }}
          .filter-grid, .live-summary {{ grid-template-columns:1fr; }}
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
        {_hero_html(df)}
        {_best_holidays_html(df)}
        {_filter_bar_html(df)}
        {_holiday_summary_html(df, progress)}
        {_stats_html(df)}
        {_price_calendar_html(df)}
        {_search_statistics_html(df)}
        <div class='section-title'>
          <h2>Complete Search Results</h2>
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
        {_final_search_summary_html(df, progress)}
        {_support_html(df, app_config)}
        {_holiday_home_html(app_config)}
      </main>
      {_filter_script(df)}
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
    summary = progress.get("summary") or {}
    return f"""
      <section class='progress-panel'>
        <div class='progress-head'>
          <div>
            <div class='progress-title'>{percent}% complete</div>
            <div class='progress-copy'>{message}</div>
            <div class='progress-copy'>
              Current provider: {escape(str(summary.get("current_provider", "N/A")))} /
              Holiday: {escape(str(summary.get("current_holiday", "N/A")))} /
              Time: {escape(str(summary.get("current_time_combination", "N/A")))}
            </div>
            <div class='progress-copy'>
              Cache hits: {summary.get("cache_hits", 0)} /
              Live searches: {summary.get("live_searches", 0)} /
              Remaining: {max(int(summary.get("total_provider_searches", total) or 0) - int(summary.get("provider_searches_completed", completed) or 0), 0)} /
              Hit rate: {summary.get("cache_hit_rate", 0)}%
            </div>
          </div>
          <strong>{completed} / {total}</strong>
        </div>
        <div class='meter' style='--progress:{percent}%'><span></span></div>
      </section>
    """


def _stats_html(df):
    successful = _successful(df)
    failed = len(df) - len(successful)
    best = successful.iloc[0] if not successful.empty else None
    best_provider = _best_provider(successful)
    cheapest_auto = _cheapest_by_transmission(successful, "Automatic")
    cheapest_manual = _cheapest_by_transmission(successful, "Manual")
    combinations = _combination_count(df)
    failed = len(df) - len(successful)
    return f"""
      <section class='stats'>
        {_live_stat("Best Overall Holiday", _result_label(best), "stat-best-holiday")}
        {_live_stat("Best Provider", best_provider, "stat-best-provider")}
        {_live_stat("Cheapest Automatic", _format_euro(cheapest_auto), "stat-cheapest-auto")}
        {_live_stat("Cheapest Manual", _format_euro(cheapest_manual), "stat-cheapest-manual")}
        {_live_stat("Average Price", _format_euro(successful["price"].mean() if not successful.empty else None), "stat-average-price")}
        {_live_stat("Highest Price", _format_euro(successful["price"].max() if not successful.empty else None), "stat-highest-price")}
        {_live_stat("Lowest Price", _format_euro(successful["price"].min() if not successful.empty else None), "stat-lowest-price")}
        {_stat("Combinations Tested", str(combinations))}
        {_live_stat("Successful Searches", str(len(successful)), "stat-successful-searches")}
        {_live_stat("Failed Searches", str(failed), "stat-failed-searches")}
      </section>
    """


def _stat(label, value):
    return f"<div class='stat'><div class='stat-label'>{escape(label)}</div><div class='stat-value'>{value}</div></div>"


def _live_stat(label, value, stat_id):
    return (
        f"<div class='stat'><div class='stat-label'>{escape(label)}</div>"
        f"<div class='stat-value' id='{escape(stat_id)}'>{value}</div></div>"
    )


def _filter_bar_html(df):
    successful = _successful(df)
    if successful.empty:
        return ""

    trip_lengths = _option_values(successful, "days_elapsed", formatter=lambda value: f"{int(value)} days")
    seats = _seat_filter_values(successful)
    transmissions = _option_values(successful, "_transmission")
    vehicle_types = _option_values(successful, "_vehicle_type")
    providers = _option_values(successful, "provider")
    low = successful["price"].min()
    high = successful["price"].max()

    return f"""
      <section class='filters' aria-label='Filter results'>
        <div class='section-title' style='margin-top:0'>
          <h2>Filter Results</h2>
          <span class='subtitle'>Instantly refine this report without running another search.</span>
        </div>
        <div class='filter-grid'>
          {_select_filter("Trip Length", "filter-trip", trip_lengths)}
          {_select_filter("Seats", "filter-seats", seats)}
          {_select_filter("Transmission", "filter-transmission", transmissions)}
          {_select_filter("Vehicle Type", "filter-type", vehicle_types)}
          {_select_filter("Provider", "filter-provider", providers)}
          <div class='filter-field'>
            <label>Price Range</label>
            <div class='price-range'>
              <input id='filter-min-price' type='number' min='0' step='0.01' placeholder='Min' value='{f"{float(low):.2f}" if not pd.isna(low) else ""}'>
              <input id='filter-max-price' type='number' min='0' step='0.01' placeholder='Max' value='{f"{float(high):.2f}" if not pd.isna(high) else ""}'>
            </div>
          </div>
          {_select_filter("Sort Order", "filter-sort", [
              ("price-asc", "Cheapest first"),
              ("daily-asc", "Lowest daily price"),
              ("trip-asc", "Shortest trip"),
              ("trip-desc", "Longest trip"),
              ("provider", "Provider"),
          ], include_all=False)}
        </div>
        <label class='filter-toggle'>
          <input id='filter-cheapest-holiday' type='checkbox'>
          <span>Show only the cheapest option for each holiday.</span>
        </label>
        <div class='live-summary'>
          <div><span>Matching results</span><strong id='live-count'>0</strong></div>
          <div><span>Cheapest visible option</span><strong id='live-cheapest'>N/A</strong></div>
          <div><span>Cheapest provider</span><strong id='live-provider'>N/A</strong></div>
          <div><span>Average visible price</span><strong id='live-average'>N/A</strong></div>
        </div>
      </section>
    """


def _select_filter(label, element_id, options, include_all=True):
    choices = ["<option value=''>Any</option>"] if include_all else []
    for value, text in options:
        choices.append(f"<option value='{escape(str(value), quote=True)}'>{escape(str(text))}</option>")
    return f"""
      <div class='filter-field'>
        <label for='{escape(element_id)}'>{escape(label)}</label>
        <select id='{escape(element_id)}'>{"".join(choices)}</select>
      </div>
    """


def _option_values(df, column, formatter=None):
    if column not in df.columns:
        return []
    values = []
    for value in df[column].dropna().unique():
        if value == "":
            continue
        label = formatter(value) if formatter else str(value)
        values.append((str(value), label))
    return sorted(values, key=lambda item: item[1])


def _seat_filter_values(df):
    if "_seats" not in df.columns:
        return []
    seats = sorted({int(value) for value in df["_seats"].dropna() if value})
    return [(str(value), f"{value}+ seats") for value in seats]


def _holiday_summary_html(df, progress):
    summary = (progress or {}).get("summary") or {}
    if not summary:
        return ""
    successful = _successful(df)
    failed = len(df) - len(successful)
    average = successful["price"].mean() if not successful.empty else None
    cheapest = successful["price"].min() if not successful.empty else None
    saving = float(average - cheapest) if average and cheapest else None
    return f"""
      <div class='section-title'><h2>Holiday Summary</h2><span class='subtitle'>Search scope and outcome</span></div>
      <section class='stats'>
        {_stat("Holiday Window", escape(str(summary.get("holiday_window", "N/A"))))}
        {_stat("Trip Length Range", escape(str(summary.get("trip_length_range", "N/A"))))}
        {_stat("Pickup Time Options", escape(str(summary.get("pickup_time_options", "N/A"))))}
        {_stat("Return Time Options", escape(str(summary.get("return_time_options", "N/A"))))}
        {_stat("Date Combinations", str(summary.get("date_combinations_generated", 0)))}
        {_stat("Time Combinations", str(summary.get("time_combinations_generated", 0)))}
        {_stat("Total Combinations", str(summary.get("total_combinations_generated", 0)))}
        {_stat("Duplicates Removed", str(summary.get("duplicate_searches_removed", 0)))}
        {_stat("Provider Searches", str(summary.get("provider_searches_completed", 0)))}
        {_stat("Cache Mode", escape(str(summary.get("cache_mode", "Live Search"))))}
        {_stat("Cache Hits", str(summary.get("cache_hits", 0)))}
        {_stat("Live Searches", str(summary.get("live_searches", 0)))}
        {_stat("Browser Sessions", str(summary.get("browser_sessions_opened", 0)))}
        {_stat("Estimated Time Saved", _duration(summary.get("estimated_time_saved_seconds")))}
        {_stat("Successful Searches", str(len(successful)))}
        {_stat("Failed Searches", str(failed))}
        {_stat("Search Duration", _duration(summary.get("search_duration_seconds")))}
        {_stat("Best Provider", _best_provider(successful))}
        {_stat("Cheapest Holiday", _result_label(successful.iloc[0] if not successful.empty else None))}
        {_stat("Average Price", _format_euro(average))}
        {_stat("Potential Saving Vs Average", _format_euro(saving))}
      </section>
    """


def _best_holidays_html(df):
    successful = _successful(df).head(20)
    if successful.empty:
        return """
          <div class='section-title'><h2>Top 20 Best Holidays</h2><span class='subtitle'>Awaiting successful prices</span></div>
          <div class='best-table'><table><tbody><tr><td>No ranked holidays yet.</td></tr></tbody></table></div>
        """

    rows = []
    prices = list(successful["price"])
    for index, (_, row) in enumerate(successful.iterrows(), start=1):
        next_price = prices[index] if index < len(prices) else None
        saving = float(next_price) - float(row.get("price")) if next_price is not None else None
        rows.append(
            f"""
            <tr id='result-{escape(_anchor(row))}' data-best-key='{escape(_row_key(row), quote=True)}'>
              <td>{index}</td>
              <td>{escape(_text(row.get("provider"), ""))}</td>
              <td>{_source_badge(row)}</td>
              <td>{escape(_text(row.get("vehicle"), "Vehicle unavailable"))}</td>
              <td>{_date_text(row.get("pickup"))}</td>
              <td>{_date_text(row.get("dropoff"))}</td>
              <td>{int(row.get("days_elapsed")) if not pd.isna(row.get("days_elapsed")) else "N/A"}</td>
              <td>{_time_html(row, "pickup")}</td>
              <td>{_time_html(row, "return")}</td>
              <td>{_format_euro(row.get("price"))}</td>
              <td>{_format_euro(row.get("effective_daily"))}</td>
              <td>{_format_euro(saving) if saving and saving > 0.009 else "N/A"}</td>
              <td>{_booking_link(row)}</td>
            </tr>
            """
        )
    return f"""
      <div class='section-title'><h2>Top 20 Best Holidays</h2><span class='subtitle'>Ranked by total price, daily price, then provider preference</span></div>
      <div class='best-table'>
        <table>
          <thead><tr><th>Rank</th><th>Provider</th><th>Source</th><th>Vehicle</th><th>Departure</th><th>Return</th><th>Trip</th><th>Pickup</th><th>Return time</th><th>Total</th><th>Daily</th><th>Saves vs next</th><th>Book</th></tr></thead>
          <tbody id='best-holidays-body'>{"".join(rows)}</tbody>
        </table>
      </div>
    """


def _price_calendar_html(df):
    successful = _successful(df)
    if successful.empty:
        return ""

    by_day = successful.groupby("pickup", as_index=False)["price"].min().sort_values("pickup")
    low = by_day["price"].min()
    high = by_day["price"].max()
    span = max(float(high - low), 0.01)
    cells = []
    for _, row in by_day.iterrows():
        ratio = (float(row["price"]) - float(low)) / span
        band = "green" if ratio <= 0.33 else "yellow" if ratio <= 0.66 else "red"
        pickup = _text(row.get("pickup"), "")
        cells.append(
            f"<a class='{band}' href='#depart-{_date_id(pickup)}'><div class='cal-date'>{_date_text(pickup)}</div><div class='cal-price'>{_format_euro(row.get('price'))}</div></a>"
        )
    return f"""
      <div class='section-title'><h2>Price Calendar</h2><span class='subtitle'>Cheapest result found by departure date</span></div>
      <section class='calendar'>{"".join(cells)}</section>
    """


def _search_statistics_html(df):
    successful = _successful(df)
    if df.empty:
        return ""

    provider_wins = _provider_win_counts(successful)
    win_text = ", ".join(f"{escape(provider)}: {count}" for provider, count in provider_wins.items()) or "N/A"
    cheapest_depart = _cheapest_departure(successful)
    cheapest_length = _cheapest_trip_length(successful)
    return f"""
      <div class='section-title'><h2>Search Statistics</h2><span class='subtitle'>Calculated from completed results</span></div>
      <section class='stats'>
        {_live_stat("Total Searches Performed", str(len(df)), "stat-total-searches")}
        {_live_stat("Average Provider Price", _format_euro(successful["price"].mean() if not successful.empty else None), "stat-average-provider-price")}
        {_live_stat("Cheapest Provider Overall", _best_provider(successful), "stat-cheapest-provider-overall")}
        {_stat("Provider Win Count", win_text)}
        {_live_stat("Cheapest Day To Depart", cheapest_depart, "stat-cheapest-departure")}
        {_live_stat("Cheapest Trip Length", cheapest_length, "stat-cheapest-trip-length")}
      </section>
    """


def _hero_html(df):
    successful = _successful(df)
    if successful.empty:
        return """
          <section class='hero-card'>
            <div class='winner'>
              <div>
                <div class='eyebrow'>Recommended Booking</div>
                <h2>No confirmed prices yet</h2>
                <p class='winner-meta'>Results will appear here as each provider completes a search.</p>
              </div>
              <div class='winner-price'>--</div>
            </div>
            <aside class='side-panel'><h2>Why this matters</h2><p>The report refreshes while searches are running and keeps CSV/XLSX exports unchanged.</p></aside>
          </section>
        """

    best = successful.iloc[0]
    return f"""
      <section class='hero-card'>
        <div class='winner'>
          <div>
            <div class='eyebrow'>Recommended Booking</div>
            <h2>{escape(_text(best.get("vehicle"), "Vehicle unavailable"))}</h2>
            <p class='winner-meta'>{escape(_text(best.get("provider"), "Provider"))} from {_date_text(best.get("pickup"))} {_time_html(best, "pickup")} to {_date_text(best.get("dropoff"))} {_time_html(best, "return")}</p>
          </div>
          <div class='winner-price'>{_format_euro(best.get("price"))}</div>
        </div>
        <aside class='side-panel'>
          <h2>Why this was chosen</h2>
          <p>{_recommendation_reason(best, successful)}</p>
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
    card_class, badge_text = _price_band(price, cheapest, success)
    badge = f"<div class='badge'>{escape(badge_text)}</div>" if badge_text else ""
    comparison = _comparison(price, cheapest, next_cheapest, success)
    return f"""
      <article class='card {card_class}' id='depart-{_date_id(row.get("pickup"))}' data-result-key='{escape(_row_key(row), quote=True)}'>
        <div class='media'>
          {_image_html(image, vehicle)}
          {_logo_html(logo, provider)}
          {badge}
        </div>
        <div class='card-body'>
          <div>
            <h3>{escape(vehicle)}</h3>
            <div class='route'>{_source_badge(row)} {escape(provider)} &middot; {_date_text(row.get("pickup"))} {_time_html(row, "pickup")} to {_date_text(row.get("dropoff"))} {_time_html(row, "return")}</div>
            <div class='route'>{_vehicle_meta(row)}</div>
          </div>
          <div class='price-line'>
            <div class='price'>{_format_euro(price) if success else "No price"}</div>
            <div class='daily'>Daily<br>{_format_euro(row.get("effective_daily"))}</div>
          </div>
          {comparison}
          {_booking_link(row)}
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


def _source_badge(row):
    source = _text(row.get("_result_source"), "LIVE").upper()
    badge_class = "cache" if source == "CACHE" else "live"
    return f"<span class='source {badge_class}'>{escape(source)}</span>"


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


def _price_band(price, cheapest, success):
    if not success or pd.isna(price) or pd.isna(cheapest):
        return "", ""
    delta = float(price) - float(cheapest)
    if delta <= 0.009:
        return "cheapest", "Cheapest"
    if delta <= 10:
        return "near10", "Within EUR 10"
    if delta <= 25:
        return "near25", "Within EUR 25"
    return "above25", "More than EUR 25 above"


def _vehicle_meta(row):
    parts = []
    seats = row.get("_seats")
    transmission = row.get("_transmission")
    vehicle_type = row.get("_vehicle_type")
    if not pd.isna(seats) and seats:
        parts.append(f"{int(seats)} seats")
    if not pd.isna(transmission) and transmission:
        parts.append(str(transmission))
    if not pd.isna(vehicle_type) and vehicle_type:
        parts.append(str(vehicle_type))
    return escape(" / ".join(parts) if parts else "Seats, transmission, and class unavailable")


def _booking_link(row):
    url = row.get("url")
    if pd.isna(url) or not url:
        return ""
    label, note = _booking_info(row)
    return (
        f"<a class='book' href='{escape(str(url), quote=True)}' target='_blank' rel='noopener noreferrer'>{escape(label)}</a>"
        f"<div class='book-note'>{escape(note)}</div>"
    )


def _booking_info(row):
    provider = _text(row.get("provider"), "")
    notes = {
        "PlusCar": "PlusCar uses an interactive search page. Your search details are shown above.",
        "AutoReisen": "AutoReisen prices are searched directly, but booking pages may not preserve submitted form state.",
        "Cicar": "This provider does not support direct booking links. Your search details are shown above.",
        "Payless Car": "This provider does not support direct booking links. Your search details are shown above.",
    }
    return "Continue on Provider", notes.get(
        provider,
        "This provider may not support direct booking links. Your search details are shown above.",
    )


def _recommendation_reason(best, successful):
    reasons = ["Cheapest overall"]
    if not successful.empty and best.get("effective_daily") == successful["effective_daily"].min():
        reasons.append("best daily price")
    transmission = best.get("_transmission")
    seats = best.get("_seats")
    vehicle_type = best.get("_vehicle_type")
    if not pd.isna(transmission) and transmission:
        reasons.append(str(transmission).lower())
    if not pd.isna(seats) and seats:
        reasons.append(f"{int(seats)} seats")
    if not pd.isna(vehicle_type) and vehicle_type:
        reasons.append(str(vehicle_type).lower())
    if _times_match_request(best):
        reasons.append("closest match to requested times")
    return escape(", ".join(reasons).capitalize() + ".")


def _times_match_request(row):
    return (
        _text(row.get("requested_pickup_time"), "") == _text(row.get("actual_pickup_time"), "")
        and _text(row.get("requested_return_time"), "") == _text(row.get("actual_return_time"), "")
    )


def _anchor(row):
    return "-".join(
        [
            _text(row.get("provider"), "provider").lower().replace(" ", "-"),
            _date_id(row.get("pickup")),
            _date_id(row.get("dropoff")),
        ]
    )


def _row_key(row):
    return "-".join(
        [
            _text(row.get("provider"), "provider").lower().replace(" ", "-"),
            _date_id(row.get("pickup")),
            _date_id(row.get("dropoff")),
            _safe_id(row.get("actual_pickup_time") or row.get("pickup_time")),
            _safe_id(row.get("actual_return_time") or row.get("return_time")),
            _safe_id(row.get("vehicle")),
            _safe_id(row.get("price")),
            _safe_id(row.name),
        ]
    )


def _safe_id(value):
    if pd.isna(value) or value is None:
        return "na"
    return "".join(character.lower() if character.isalnum() else "_" for character in str(value)).strip("_") or "na"


def _table_html(df):
    export_columns = [column for column in EXPORT_COLUMNS if column in df.columns]
    table_df = df[export_columns] if export_columns else df
    table_df = table_df.copy()
    for column in ["pickup", "dropoff"]:
        if column in table_df.columns:
            table_df[column] = table_df[column].map(_date_text)
    return table_df.to_html(index=False, escape=False)


def _final_search_summary_html(df, progress):
    summary = (progress or {}).get("summary") or {}
    if not summary:
        return ""
    duration = summary.get("search_duration_seconds") or summary.get("elapsed_seconds")
    completed = int(summary.get("provider_searches_completed", len(df)) or 0)
    speed = None
    if duration and completed:
        try:
            speed = float(duration) / completed
        except (TypeError, ValueError, ZeroDivisionError):
            speed = None
    manual_saved = summary.get("estimated_time_saved_seconds")
    provider_count = summary.get("provider_count", 4)
    return f"""
      <div class='section-title'><h2>Search Summary</h2><span class='subtitle'>What Canary Car Finder checked for you</span></div>
      <section class='stats'>
        {_stat("Holiday Combinations", str(summary.get("date_combinations_generated", 0)))}
        {_stat("Time Combinations", str(summary.get("time_combinations_generated", 0)))}
        {_stat("Duplicates Removed", str(summary.get("duplicate_searches_removed", 0)))}
        {_stat("Provider Searches", str(summary.get("total_provider_searches", completed)))}
        {_stat("Browser Sessions", str(summary.get("browser_sessions_opened", 0)))}
        {_stat("Cache Hits", str(summary.get("cache_hits", 0)))}
        {_stat("Time Taken", _duration(duration))}
        {_stat("Average Search Speed", f"{speed:.1f}s per price" if speed else "N/A")}
        {_stat("Estimated Manual Time Saved", _duration(manual_saved))}
      </section>
      <aside class='side-panel'>
        <h2>Real prices, less legwork</h2>
        <p>This search checked {completed} real prices across {provider_count} trusted providers so you did not have to.</p>
      </aside>
    """


def _support_html(df, app_config):
    donation_url = app_config.get("donation_url")
    button = ""
    if donation_url:
        button = (
            f"<a href='{escape(str(donation_url), quote=True)}' target='_blank' rel='noopener noreferrer'>"
            "🍺 Buy Jamie an Estrella</a>"
        )

    return f"""
      <section class='support'>
        <div>
          <h2>🍺 Enjoyed using Canary Car Hire Optimiser?</h2>
          <p>This app has:</p>
          <p>No adverts<br>No subscriptions<br>No affiliate links</p>
          <p>If it helped you save money on your holiday and you would like to support future improvements, buying me an Estrella is always appreciated.</p>
        </div>
        {button}
      </section>
    """


def _holiday_home_html(app_config):
    url = app_config.get("holiday_home_url")
    if not url:
        return ""
    return f"""
      <section class='support secondary'>
        <div>
          <h2>🏝 Staying in Fuerteventura?</h2>
          <p>If you are still looking for accommodation, take a look at our holiday home in Caleta de Fuste.</p>
        </div>
        <a href='{escape(str(url), quote=True)}' target='_blank' rel='noopener noreferrer'>View Holiday Home</a>
      </section>
    """


def _successful(df):
    if df.empty or "success" not in df.columns:
        return pd.DataFrame()
    successful = df[df["success"] == True]
    if successful.empty:
        return successful
    successful = successful.copy()
    successful["_provider_rank"] = successful["provider"].map(PROVIDER_ORDER).fillna(99)
    return successful.sort_values(
        ["price", "effective_daily", "_provider_rank"],
        ascending=[True, True, True],
        na_position="last",
    )


def _saving_vs_most_expensive(df):
    successful = _successful(df)
    if successful.empty or "price" not in successful.columns or len(successful) < 2:
        return None
    return float(successful["price"].max()) - float(successful["price"].min())


def _result_label(row):
    if row is None:
        return "N/A"
    return f"{escape(_text(row.get('provider'), 'Provider'))}<br>{_format_euro(row.get('price'))}"


def _best_provider(successful):
    if successful.empty:
        return "N/A"
    wins = _provider_win_counts(successful)
    if wins:
        return max(wins.items(), key=lambda item: item[1])[0]
    return _text(successful.iloc[0].get("provider"), "N/A")


def _cheapest_by_transmission(successful, transmission):
    if successful.empty or "_transmission" not in successful.columns:
        return None
    matching = successful[successful["_transmission"] == transmission]
    if matching.empty:
        return None
    return matching.iloc[0].get("price")


def _combination_count(df):
    if df.empty or "pickup" not in df.columns or "dropoff" not in df.columns:
        return 0
    return len(df[["pickup", "dropoff"]].drop_duplicates())


def _provider_win_counts(successful):
    if successful.empty:
        return {}
    winners = successful.sort_values(
        ["price", "effective_daily", "_provider_rank"],
        ascending=[True, True, True],
        na_position="last",
    )
    winners = winners.groupby(["pickup", "dropoff"], as_index=False).first()
    counts = winners["provider"].value_counts().to_dict()
    return {str(provider): int(count) for provider, count in counts.items()}


def _cheapest_departure(successful):
    if successful.empty:
        return "N/A"
    by_day = successful.groupby("pickup", as_index=False)["price"].min().sort_values("price")
    row = by_day.iloc[0]
    return f"{_date_text(row.get('pickup'))}<br>{_format_euro(row.get('price'))}"


def _cheapest_trip_length(successful):
    if successful.empty:
        return "N/A"
    by_length = successful.groupby("days_elapsed", as_index=False)["price"].min().sort_values("price")
    row = by_length.iloc[0]
    days = int(row.get("days_elapsed")) if not pd.isna(row.get("days_elapsed")) else "N/A"
    return f"{days} days<br>{_format_euro(row.get('price'))}"


def _format_euro(value):
    return "N/A" if pd.isna(value) else f"&euro;{float(value):.2f}"


def _date_text(value):
    if pd.isna(value) or value is None:
        return "N/A"
    try:
        return pd.Timestamp(value).strftime("%d/%m/%Y")
    except Exception:
        return escape(str(value))


def _date_id(value):
    if pd.isna(value) or value is None:
        return "date-na"
    try:
        return pd.Timestamp(value).strftime("%d%m%Y")
    except Exception:
        return "".join(character for character in str(value) if character.isalnum()) or "date-na"


def _duration(seconds):
    if seconds is None:
        return "N/A"
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        return "N/A"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remainder = int(seconds % 60)
    return f"{minutes}m {remainder}s"


def _text(value, fallback):
    return fallback if pd.isna(value) or value is None else str(value)


def _time_html(row, kind):
    actual = _text(row.get(f"actual_{kind}_time"), _text(row.get(f"{kind}_time"), ""))
    requested = _text(row.get(f"requested_{kind}_time"), actual)
    if not actual and not requested:
        return "N/A"
    return (
        f"<span class='time-pair'>Requested {escape(requested or 'N/A')}<br>"
        f"Actual searched {escape(actual or 'N/A')}</span>"
    )


def _initials(value):
    words = [part for part in str(value).replace("-", " ").split() if part]
    return "".join(word[0].upper() for word in words[:2]) or "CC"


def _filter_script(df):
    successful = _successful(df)
    if successful.empty:
        return ""
    payload = json.dumps(_filter_rows(successful), ensure_ascii=False).replace("</", "<\\/")
    return f"""
      <script type='application/json' id='report-data'>{payload}</script>
      <script>
      (() => {{
        const dataNode = document.getElementById('report-data');
        if (!dataNode) return;
        const rows = JSON.parse(dataNode.textContent);
        const cards = new Map([...document.querySelectorAll('[data-result-key]')].map(card => [card.dataset.resultKey, card]));
        const cardsContainer = document.querySelector('.cards');
        const bestBody = document.getElementById('best-holidays-body');
        const providerOrder = {json.dumps(PROVIDER_ORDER)};
        const controls = {{
          trip: document.getElementById('filter-trip'),
          seats: document.getElementById('filter-seats'),
          transmission: document.getElementById('filter-transmission'),
          type: document.getElementById('filter-type'),
          provider: document.getElementById('filter-provider'),
          minPrice: document.getElementById('filter-min-price'),
          maxPrice: document.getElementById('filter-max-price'),
          sort: document.getElementById('filter-sort'),
          cheapestHoliday: document.getElementById('filter-cheapest-holiday')
        }};

        const money = value => Number.isFinite(value) ? `&euro;${{value.toFixed(2)}}` : 'N/A';
        const numberValue = input => {{
          const value = parseFloat(input?.value || '');
          return Number.isFinite(value) ? value : null;
        }};
        const text = value => value || 'N/A';
        const compareRows = (a, b, sortMode = 'price-asc') => {{
          if (sortMode === 'daily-asc') return (a.daily ?? Infinity) - (b.daily ?? Infinity) || baseCompare(a, b);
          if (sortMode === 'trip-asc') return (a.days ?? Infinity) - (b.days ?? Infinity) || baseCompare(a, b);
          if (sortMode === 'trip-desc') return (b.days ?? -Infinity) - (a.days ?? -Infinity) || baseCompare(a, b);
          if (sortMode === 'provider') return a.provider.localeCompare(b.provider) || baseCompare(a, b);
          return baseCompare(a, b);
        }};
        const baseCompare = (a, b) => (
          (a.price ?? Infinity) - (b.price ?? Infinity) ||
          (a.daily ?? Infinity) - (b.daily ?? Infinity) ||
          ((providerOrder[a.provider] ?? 99) - (providerOrder[b.provider] ?? 99))
        );
        const visibleRows = () => {{
          const trip = controls.trip?.value || '';
          const seats = numberValue(controls.seats);
          const transmission = controls.transmission?.value || '';
          const type = controls.type?.value || '';
          const provider = controls.provider?.value || '';
          const minPrice = numberValue(controls.minPrice);
          const maxPrice = numberValue(controls.maxPrice);
          let filtered = rows.filter(row => {{
            if (trip && String(row.days) !== trip) return false;
            if (seats !== null && (!Number.isFinite(row.seats) || row.seats < seats)) return false;
            if (transmission && row.transmission !== transmission) return false;
            if (type && row.vehicleType !== type) return false;
            if (provider && row.provider !== provider) return false;
            if (minPrice !== null && (!Number.isFinite(row.price) || row.price < minPrice)) return false;
            if (maxPrice !== null && (!Number.isFinite(row.price) || row.price > maxPrice)) return false;
            return true;
          }});
          filtered = filtered.sort((a, b) => compareRows(a, b, controls.sort?.value || 'price-asc'));
          if (controls.cheapestHoliday?.checked) {{
            const seen = new Set();
            filtered = filtered.filter(row => {{
              if (seen.has(row.holidayKey)) return false;
              seen.add(row.holidayKey);
              return true;
            }});
          }}
          return filtered;
        }};
        const setHtml = (id, value) => {{
          const node = document.getElementById(id);
          if (node) node.innerHTML = value;
        }};
        const cheapestProvider = visible => visible[0]?.provider || 'N/A';
        const winCountProvider = visible => {{
          if (!visible.length) return 'N/A';
          const byHoliday = new Map();
          visible.forEach(row => {{
            const current = byHoliday.get(row.holidayKey);
            if (!current || baseCompare(row, current) < 0) byHoliday.set(row.holidayKey, row);
          }});
          const counts = new Map();
          byHoliday.forEach(row => counts.set(row.provider, (counts.get(row.provider) || 0) + 1));
          return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]?.[0] || 'N/A';
        }};
        const cheapestByTransmission = (visible, transmission) => visible.find(row => row.transmission === transmission)?.price;
        const cheapestDeparture = visible => {{
          if (!visible.length) return 'N/A';
          const best = visible.reduce((winner, row) => !winner || row.price < winner.price ? row : winner, null);
          return `${{best.pickupDisplay}}<br>${{money(best.price)}}`;
        }};
        const cheapestTripLength = visible => {{
          if (!visible.length) return 'N/A';
          const byLength = new Map();
          visible.forEach(row => {{
            const current = byLength.get(row.days);
            if (!current || row.price < current.price) byLength.set(row.days, row);
          }});
          const best = [...byLength.values()].sort(baseCompare)[0];
          return best ? `${{best.days}} days<br>${{money(best.price)}}` : 'N/A';
        }};
        const renderBest = visible => {{
          if (!bestBody) return;
          const best = visible.slice(0, 20);
          if (!best.length) {{
            bestBody.innerHTML = '<tr><td colspan="13">No results match these filters.</td></tr>';
            return;
          }}
          bestBody.innerHTML = best.map((row, index) => {{
            const next = best[index + 1];
            const saving = next && Number.isFinite(next.price) ? next.price - row.price : null;
            return `<tr data-best-key="${{row.key}}">
              <td>${{index + 1}}</td>
              <td>${{escapeHtml(row.provider)}}</td>
              <td><span class="source ${{row.source === 'CACHE' ? 'cache' : 'live'}}">${{escapeHtml(row.source)}}</span></td>
              <td>${{escapeHtml(row.vehicle)}}</td>
              <td>${{row.pickupDisplay}}</td>
              <td>${{row.dropoffDisplay}}</td>
              <td>${{row.days ?? 'N/A'}}</td>
              <td>${{timeHtml(row.requestedPickupTime, row.actualPickupTime)}}</td>
              <td>${{timeHtml(row.requestedReturnTime, row.actualReturnTime)}}</td>
              <td>${{money(row.price)}}</td>
              <td>${{money(row.daily)}}</td>
              <td>${{saving && saving > 0.009 ? money(saving) : 'N/A'}}</td>
              <td>${{bookingHtml(row)}}</td>
            </tr>`;
          }}).join('');
        }};
        const updateCards = visible => {{
          if (!cardsContainer) return;
          const visibleKeys = new Set(visible.map(row => row.key));
          cards.forEach((card, key) => card.classList.toggle('is-hidden', !visibleKeys.has(key)));
          const cheapest = visible[0]?.price;
          const nextCheapest = visible[1]?.price;
          visible.forEach(row => {{
            const card = cards.get(row.key);
            if (card) {{
              refreshCardBand(card, row, cheapest, nextCheapest);
              cardsContainer.appendChild(card);
            }}
          }});
        }};
        const refreshCardBand = (card, row, cheapest, nextCheapest) => {{
          card.classList.remove('cheapest', 'near10', 'near25', 'above25');
          let badgeText = '';
          let comparison = 'Awaiting comparison';
          let comparisonClass = 'comparison';
          if (Number.isFinite(row.price) && Number.isFinite(cheapest)) {{
            const delta = row.price - cheapest;
            if (delta <= 0.009) {{
              card.classList.add('cheapest');
              badgeText = 'Cheapest';
              comparison = Number.isFinite(nextCheapest) && nextCheapest - row.price > 0.009
                ? `Saves ${{money(nextCheapest - row.price)}} vs next option`
                : 'Cheapest option found';
            }} else if (delta <= 10) {{
              card.classList.add('near10');
              badgeText = 'Within EUR 10';
              comparison = `Cheapest saves ${{money(delta)}} vs this option`;
              comparisonClass = 'comparison more';
            }} else if (delta <= 25) {{
              card.classList.add('near25');
              badgeText = 'Within EUR 25';
              comparison = `Cheapest saves ${{money(delta)}} vs this option`;
              comparisonClass = 'comparison more';
            }} else {{
              card.classList.add('above25');
              badgeText = 'More than EUR 25 above';
              comparison = `Cheapest saves ${{money(delta)}} vs this option`;
              comparisonClass = 'comparison more';
            }}
          }}
          let badge = card.querySelector('.badge');
          if (!badge) {{
            badge = document.createElement('div');
            badge.className = 'badge';
            card.querySelector('.media')?.appendChild(badge);
          }}
          badge.textContent = badgeText;
          badge.classList.toggle('is-hidden', !badgeText);
          const comparisonNode = card.querySelector('.comparison');
          if (comparisonNode) {{
            comparisonNode.className = comparisonClass;
            comparisonNode.innerHTML = comparison;
          }}
        }};
        const updateStats = visible => {{
          const count = visible.length;
          const average = count ? visible.reduce((total, row) => total + row.price, 0) / count : null;
          const highest = count ? Math.max(...visible.map(row => row.price)) : null;
          const lowest = count ? Math.min(...visible.map(row => row.price)) : null;
          const failedCount = rows.length - count;
          setHtml('live-count', String(count));
          setHtml('live-cheapest', count ? `${{visible[0].provider}}<br>${{money(visible[0].price)}}` : 'N/A');
          setHtml('live-provider', cheapestProvider(visible));
          setHtml('live-average', money(average));
          setHtml('stat-best-holiday', count ? `${{escapeHtml(visible[0].provider)}}<br>${{money(visible[0].price)}}` : 'N/A');
          setHtml('stat-best-provider', winCountProvider(visible));
          setHtml('stat-cheapest-auto', money(cheapestByTransmission(visible, 'Automatic')));
          setHtml('stat-cheapest-manual', money(cheapestByTransmission(visible, 'Manual')));
          setHtml('stat-average-price', money(average));
          setHtml('stat-highest-price', money(highest));
          setHtml('stat-lowest-price', money(lowest));
          setHtml('stat-successful-searches', String(count));
          setHtml('stat-failed-searches', String(failedCount));
          setHtml('stat-total-searches', String(count));
          setHtml('stat-average-provider-price', money(average));
          setHtml('stat-cheapest-provider-overall', winCountProvider(visible));
          setHtml('stat-cheapest-departure', cheapestDeparture(visible));
          setHtml('stat-cheapest-trip-length', cheapestTripLength(visible));
        }};
        const applyFilters = () => {{
          const visible = visibleRows();
          renderBest(visible);
          updateCards(visible);
          updateStats(visible);
        }};
        const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, char => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[char]));
        const escapeAttr = value => escapeHtml(value).replace(/`/g, '&#96;');
        const timeHtml = (requested, actual) => `<span class="time-pair">Requested ${{escapeHtml(requested || 'N/A')}}<br>Actual searched ${{escapeHtml(actual || 'N/A')}}</span>`;
        const bookingHtml = row => row.url
          ? `<a class="book" href="${{escapeAttr(row.url)}}" target="_blank" rel="noopener noreferrer">${{escapeHtml(row.bookingLabel)}}</a><div class="book-note">${{escapeHtml(row.bookingNote)}}</div>`
          : '';
        Object.values(controls).forEach(control => control?.addEventListener('input', applyFilters));
        Object.values(controls).forEach(control => control?.addEventListener('change', applyFilters));
        applyFilters();
      }})();
      </script>
    """


def _filter_rows(df):
    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "key": _row_key(row),
                "holidayKey": "|".join(
                    [
                        _text(row.get("pickup"), ""),
                        _text(row.get("dropoff"), ""),
                        _text(row.get("requested_pickup_time"), _text(row.get("pickup_time"), "")),
                        _text(row.get("requested_return_time"), _text(row.get("return_time"), "")),
                    ]
                ),
                "provider": _text(row.get("provider"), "Provider"),
                "source": _text(row.get("_result_source"), "LIVE").upper(),
                "vehicle": _text(row.get("vehicle"), "Vehicle unavailable"),
                "pickup": _text(row.get("pickup"), ""),
                "dropoff": _text(row.get("dropoff"), ""),
                "pickupDisplay": _date_text(row.get("pickup")),
                "dropoffDisplay": _date_text(row.get("dropoff")),
                "days": _json_number(row.get("days_elapsed"), integer=True),
                "seats": _json_number(row.get("_seats"), integer=True),
                "transmission": "" if pd.isna(row.get("_transmission")) else str(row.get("_transmission")),
                "vehicleType": "" if pd.isna(row.get("_vehicle_type")) else str(row.get("_vehicle_type")),
                "price": _json_number(row.get("price")),
                "daily": _json_number(row.get("effective_daily")),
                "requestedPickupTime": _text(row.get("requested_pickup_time"), _text(row.get("pickup_time"), "")),
                "actualPickupTime": _text(row.get("actual_pickup_time"), _text(row.get("pickup_time"), "")),
                "requestedReturnTime": _text(row.get("requested_return_time"), _text(row.get("return_time"), "")),
                "actualReturnTime": _text(row.get("actual_return_time"), _text(row.get("return_time"), "")),
                "url": "" if pd.isna(row.get("url")) else str(row.get("url")),
                "bookingLabel": _booking_info(row)[0],
                "bookingNote": _booking_info(row)[1],
            }
        )
    return rows


def _json_number(value, integer=False):
    if pd.isna(value) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if integer else number
