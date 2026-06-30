# Canary Islands Car Hire Optimiser Roadmap

## Version 1.0 Architecture

Canary Islands Car Hire Optimiser is a local-only Python application for comparing trusted car hire providers at Fuerteventura Airport.

The app is organised around a provider-based architecture:

- `providers/base.py` defines the shared `CarProvider` interface and normalised `result(...)` shape.
- `providers/` contains one provider implementation per supported company.
- `providers/__init__.py` registers the active providers used by searches.
- `runner.py` coordinates date combinations, provider execution, live progress updates, and report refreshes.
- `reports.py` writes CSV, Excel, and the HTML dashboard from the same normalised result rows.
- `settings.py` loads local configuration from `config/default_settings.json`.
- `utils.py` contains shared logging and date-combination helpers.

Version 1.0 intentionally supports only these four trusted providers:

- PlusCar
- AutoReisen
- Cicar
- Payless Car

No additional providers are planned for Version 1.x.

## Completed Features

- Provider-based architecture with interchangeable provider result rows.
- PlusCar provider.
- AutoReisen provider.
- Cicar provider.
- Payless Car provider.
- Live progress reporting while searches run.
- Booking-style HTML dashboard with cards, provider logos where available, vehicle images where available, prominent pricing, and savings comparisons.
- CSV export with stable columns.
- Excel export with stable columns.
- Debug HTML and screenshots for provider troubleshooting.
- Local configuration for date ranges, hire duration limits, pickup/return times, and browser visibility.
- Headless/visible browser support for providers that require browser automation.

## Version 1.1

Focus: usability and day-to-day reliability.

- Improve the start workflow and documentation for non-technical use.
- Add clearer error states in the dashboard when a provider fails.
- Add a search summary showing which providers ran, which failed, and why.
- Improve progress messaging for long searches.
- Add basic validation for date range, min/max days, and return time settings.
- Make generated reports easier to open from Windows.

## Version 1.2

Focus: search intelligence and performance.

- Add smarter search presets for common trip lengths.
- Add ranking controls for total price, effective daily price, provider, vehicle class, and availability.
- Reduce repeated provider setup where safe.
- Add optional retry/backoff for transient provider failures.
- Improve provider-specific diagnostics without changing export schemas.
- Add lightweight caching for repeated searches with identical inputs.

## Version 2.0

Focus: historical pricing and richer user experience.

- Store historical search results locally.
- Add price trend views by provider, date range, vehicle, and trip length.
- Highlight price changes since previous searches.
- Add saved search profiles.
- Add richer dashboard filtering and comparison tools.
- Consider a dedicated desktop UI if the local CLI/report workflow becomes limiting.

## Future Work Direction

Future work should focus on usability, search intelligence, performance, historical pricing, and user experience rather than adding more providers.

The goal is not to scrape every rental company. The goal is to make a small, trusted set of providers easier to compare, monitor, and understand.

## Project Principles

### Trusted Providers Only

Car hire pricing is sensitive to fees, insurance terms, deposits, fuel rules, availability, and booking conditions. Canary Islands Car Hire Optimiser intentionally includes only providers that are trusted enough to compare directly and consistently.

A smaller provider set keeps results understandable. It also makes it easier to notice when a provider changes its website, pricing structure, or booking flow.

### Stable Outputs Matter

CSV and Excel exports should remain stable wherever possible. The HTML dashboard can evolve quickly, but exported data should stay predictable for spreadsheets, historical comparisons, and future automation.

### Avoid Feature Creep

Every new feature should make the search experience clearer, faster, or more reliable. New providers, new workflows, or new abstractions should not be added just because they are possible.

The project should stay small enough to understand, repair, and trust.

### Prefer Practical Automation

Provider implementations should use the simplest reliable path for each website. Some providers can be queried with direct HTTP requests, while others need browser automation. The architecture supports both, but each provider should remain easy to debug.
