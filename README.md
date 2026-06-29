# Canary Car Finder v1.0

Local-only desktop tool. No hosting. No subscriptions. No cloud.

This version is focused on four trusted Canary Islands providers.

## What it does

- Runs a modern Windows desktop app
- Lets you set:
  - pickup/return dates
  - pickup/return times
  - transmission preference
  - headless or visible browser
- Searches trusted Fuerteventura Airport providers
- Finds and compares provider prices
- Shows live progress
- Remembers the previous search automatically
- Opens the HTML report when the search completes
- Saves:
  - HTML report
  - CSV results
  - Excel results
  - logs
  - debug screenshots if anything breaks

## How to use

1. Clone or download this repository.
2. Double-click `install_windows.bat` once.
3. Double-click `start_app.bat`.
4. Choose pickup/return dates and times.
5. Choose a transmission preference.
6. Click **Search**.

For the command-line workflow:

```bash
python cli.py --mode test
```

## Results

Open:

`results/report.html`

The desktop app opens this report automatically after a completed search.

## Support link

The "Buy me an Estrella" button uses the configurable `donation_url` in:

`config/app_config.json`

## Windows packaging

To create a distributable Windows build:

```text
build_windows.bat
```

The packaged application is written to:

`release/CanaryCarFinder`

## Current providers

- PlusCar
- AutoReisen
- Cicar
- Payless Car

## v1 provider scope

- PlusCar
- AutoReisen
- Cicar
- Payless Car

Canary Car Finder v1 intentionally supports only these four trusted providers. No additional providers are planned for v1.

## Roadmap

See `ROADMAP.md`.
