# Canary Islands Car Hire Optimiser

Local Windows app for comparing trusted Canary Islands car hire prices. No hosting, no subscriptions, no cloud service.

Planning a holiday to the Canary Islands? Compare prices for one specific holiday, or let the app try lots of date, holiday-length and collection-time choices to help find the cheapest car hire option.

## Trusted Providers

The app intentionally supports only these four trusted providers:

- PlusCar
- AutoReisen
- Cicar
- Payless Car

No additional providers are planned for Version 1.x. Future work focuses on usability, speed, clearer reports and better holiday planning rather than adding more companies.

## What It Does

- Runs as a Windows desktop app.
- Lets you compare exact dates or search flexible holiday choices.
- Checks collection and return times, including nearby times when you choose that option.
- Shows live progress while prices are being checked.
- Opens a clear HTML report when the search finishes.
- Highlights a recommended booking and the 20 cheapest options.
- Lets you narrow results by seats, transmission, car type, provider, price and holiday length.
- Saves CSV and Excel exports with stable columns.
- Remembers your previous choices automatically.

## How To Use

1. Clone or download this repository.
2. Double-click `install_windows.bat` once.
3. Double-click `start_app.bat`.
4. Choose your dates, collection times and car preferences.
5. Choose `Compare My Dates` or `Find My Cheapest Hire During My Holiday`.
6. Click `Find my car`.

The app opens `results/report.html` automatically after a completed search.

## Results

The report is designed to answer one question first:

What should I book?

It includes a recommended booking, the cheapest options, filters, price summaries, provider notes and the full price list.

CSV and Excel exports are saved in `results/`.

## Support

The support button uses the configurable `donation_url` in `config/app_config.json`.

## Windows Packaging

To create a distributable Windows build:

```text
build_windows.bat
```

The packaged application is written to:

```text
release/Canary-Islands-Car-Hire-Optimiser-v<version>/
```

The build script reads the version from `app_config.py`, validates the providers, validates the generated executable, and creates a matching ZIP file automatically.

## Provider Validation

Before every release, run:

```text
build_windows.bat
```

The build process automatically runs `provider_health_check.py` before packaging. It checks PlusCar, AutoReisen, Cicar and Payless Car using a standard Fuerteventura Airport search.

The validation confirms that each provider opens, completes a search, finds at least one vehicle, extracts a price and returns a booking URL. The HTML report is saved to:

```text
results/provider_health_report.html
```

If a provider fails, diagnostics are saved under:

```text
results/debug/<provider>/<timestamp>/
```

The release build pauses and asks whether to continue. For public releases, treat any provider failure as a release blocker unless you have manually confirmed the issue is temporary or external.

## Roadmap

See `ROADMAP.md`.
