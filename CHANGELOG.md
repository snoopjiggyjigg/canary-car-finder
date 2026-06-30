# v1.4.0

- Renamed the app to Canary Islands Car Hire Optimiser.
- Centralised app name and version display.
- Improved first-screen guidance for holidaymakers.
- Improved report recommendation wording and presentation.
- Updated support and holiday-home links.
- Polished user-facing wording across the desktop app and report.
- Redesigned search choices as Quick Search, Smart Search and Thorough Search.
- Added clearer runtime estimates for long searches.
- Added a live search dashboard with pause and stop controls.
- Improved recommendation badges in the HTML report.
- Improved the Windows release build so `build_windows.bat` creates a complete versioned release folder and ZIP.

# v1.1.0

- Added polished CustomTkinter Windows desktop app
- Added saved search preferences
- Added About dialog and app metadata
- Added Buy me an Estrella support section
- Added PyInstaller packaging
- Created local release build
- Confirmed all four providers run successfully from the GUI

# v1.0.0

## Initial Release

### Features

* Provider architecture
* PlusCar integration
* AutoReisen integration
* Cicar integration
* Payless Car integration
* Live progress dashboard
* Modern HTML report
* CSV export
* Excel export
* Vehicle images
* Provider logos
* Booking links

### Technical

* Modular provider architecture
* Shared provider normalisation
* Report separation
* Smoke tests
* Git branching workflow
* Codex development workflow

### Project Principles

* Supports only four trusted providers:

  * PlusCar
  * AutoReisen
  * Cicar
  * Payless Car
* No additional providers are planned for Version 1.x.
* Future development should focus on performance, usability, historical pricing, search intelligence and user experience rather than expanding provider coverage.
