# Canary Car Finder v1.3

Local-only desktop tool. No hosting. No subscriptions. No cloud.

This version is focused on four trusted Canary Islands providers.

## What it does

- Opens a desktop app
- Lets you set:
  - date range
  - min/max hire days
  - pickup/return times
  - headless or visible browser
- Searches trusted Fuerteventura Airport providers
- Finds prices from `Total: xxx €`
- Shows live progress
- Saves:
  - HTML report
  - CSV results
  - logs
  - debug screenshots if anything breaks

## How to use

1. Clone or download this repository.
2. Double-click `install_windows.bat` once.
3. Double-click `start_app.bat`.
4. Click **Run test search** first.
5. If that works, click **Run small batch**.
6. If that works, click **Run full search**.

## Results

Open:

`results/report.html`

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

## v1.2 update

- Scrapes PlusCar vehicle cards directly: `article.swi_product`.
- Reads `.swi_product_title`, `.swi_product_price`, and `.swi_product_total_price`.
- Chooses the cheapest vehicle from the visible results grid without opening each car.

## v1.3 update

- Better winner card.
- Shows PlusCar site daily rate separately from effective elapsed-day average.
- Adds rental day estimate based on PlusCar's displayed pricing.
- Cleaner report columns.
