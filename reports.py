from pathlib import Path

import pandas as pd

RESULTS = Path("results")


def write_reports(rows):
    RESULTS.mkdir(exist_ok=True)
    df = pd.DataFrame(rows)
    csv_path = RESULTS / "results.csv"
    xlsx_path = RESULTS / "results.xlsx"
    html_path = RESULTS / "report.html"

    df.to_csv(csv_path, index=False)
    try:
        df.to_excel(xlsx_path, index=False)
    except Exception:
        pass

    report_df = df
    if not report_df.empty:
        report_df = report_df.sort_values(["success", "price"], ascending=[False, True], na_position="last")

    html_path.write_text(_render_html(report_df), encoding="utf-8")
    return csv_path, xlsx_path, html_path


def _render_html(df):
    return f"""
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
    <h1>&#127965; Canary Car Finder</h1>
    {_winner_html(df)}
    <h2>All results</h2>
    {df.to_html(index=False, escape=False)}
    </body></html>
    """


def _winner_html(df):
    good = df[df["success"] == True] if not df.empty else pd.DataFrame()
    if good.empty:
        return ""

    best = good.iloc[0]
    site_daily = _format_euro(best.get("site_daily_rate"))
    effective_daily = _format_euro(best.get("effective_daily"))
    return f"""
        <section class='winner'>
          <div class='eyebrow'>&#127942; Cheapest found</div>
          <h2>{best['provider']} &middot; {best.get('vehicle', '')}</h2>
          <p>{best['pickup']} {best['pickup_time']} &rarr; {best['dropoff']} {best['return_time']}</p>
          <div class='price'>&euro;{best['price']:.2f}</div>
          <p>Site daily: {site_daily} &middot; Effective daily: {effective_daily} &middot; Vehicles found: {best['vehicles_found']}</p>
        </section>
        """


def _format_euro(value):
    return "N/A" if pd.isna(value) else f"&euro;{value:.2f}"
