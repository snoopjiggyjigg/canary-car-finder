import calendar
from copy import replace
from datetime import date
import json
import os
from pathlib import Path
import queue
import sys
import threading
from tkinter import messagebox
import webbrowser

if getattr(sys, "frozen", False):
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(Path(sys._MEIPASS) / "ms-playwright"))

from app_config import load_app_config
from runner import estimate_search, run_search
from search_cache import CACHE_MODES
from settings import load_settings
from utils import setup_logging

ctk = None


USER_SETTINGS_PATH = Path("config/user_settings.json")
TIME_OPTIONS = [f"{hour:02d}:{minute:02d}" for hour in range(6, 24) for minute in (0, 30)]
PICKUP_TIME_OPTIONS = TIME_OPTIONS
RETURN_TIME_OPTIONS = TIME_OPTIONS
TRANSMISSIONS = ["Any", "Manual", "Automatic"]
QUICK_SEARCH = "Quick Search"
SMART_SEARCH = "Smart Search (Recommended)"
THOROUGH_SEARCH = "Thorough Search"
COMPARE_EXACT_DATES = QUICK_SEARCH
FIND_CHEAPEST_HOLIDAY = SMART_SEARCH
SEARCH_PRESETS = [QUICK_SEARCH, SMART_SEARCH, THOROUGH_SEARCH]
CACHE_MODE_OPTIONS = list(CACHE_MODES.keys())
SEAT_OPTIONS = ["Any", "2+", "4+", "5+", "7+", "9+"]
VEHICLE_TYPES = ["Any", "Mini", "Economy", "Compact", "Family", "SUV", "Van"]
PROVIDERS = ["PlusCar", "AutoReisen", "Cicar", "Payless Car"]
USE_CHOSEN_TIMES = "Use exact times"
TRY_NEARBY_TIMES = "Use time windows"
TIME_MODES = [USE_CHOSEN_TIMES, TRY_NEARBY_TIMES]

COLORS = {
    "ocean": "#0b6f86",
    "deep_ocean": "#084b5f",
    "sky": "#eaf6f8",
    "sand": "#f7efe0",
    "sun": "#f2b84b",
    "coral": "#d96d5f",
    "ink": "#172a34",
    "muted": "#60717a",
    "line": "#d8e5e8",
    "panel": "#ffffff",
}


class CanaryCarFinderApp:
    def __init__(self):
        self.settings = load_settings()
        self.app_config = load_app_config()
        self.user_settings = self._load_user_settings()
        self.events = queue.Queue()
        self.worker = None
        self.search_running = False
        self.initializing = True
        self.stop_requested = threading.Event()
        self.pause_requested = threading.Event()
        self.after_id = None

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.app_name = self.app_config["app_name"]
        self.app_version = self.app_config["version"]
        self.root.title(f"{self.app_name} {self.app_version}")
        self.root.geometry("1160x800")
        self.root.minsize(1040, 760)
        self.root.configure(fg_color=COLORS["sky"])

        self.pickup_date_var = ctk.StringVar(
            value=self.user_settings.get("pickup_date", self.settings.start_date.isoformat())
        )
        self.return_date_var = ctk.StringVar(
            value=self.user_settings.get("return_date", self.settings.end_date.isoformat())
        )
        self.pickup_date_display_var = ctk.StringVar(value=_display_date(self.pickup_date_var.get()))
        self.return_date_display_var = ctk.StringVar(value=_display_date(self.return_date_var.get()))
        self.pickup_time_var = ctk.StringVar(value=self.user_settings.get("pickup_time", self.settings.pickup_time))
        self.return_time_var = ctk.StringVar(value=self.user_settings.get("return_time", self.settings.final_return_time))
        self.pickup_time_latest_var = ctk.StringVar(
            value=self.user_settings.get("pickup_time_latest", self.user_settings.get("pickup_time", self.settings.pickup_time))
        )
        self.return_time_latest_var = ctk.StringVar(
            value=self.user_settings.get("return_time_latest", self.user_settings.get("return_time", self.settings.final_return_time))
        )
        self.time_mode_var = ctk.StringVar(value=_saved_time_mode(self.user_settings.get("time_mode")))
        self.min_days_var = ctk.StringVar(value=str(self.user_settings.get("min_days", self.settings.min_days)))
        self.max_days_var = ctk.StringVar(value=str(self.user_settings.get("max_days", self.settings.max_days)))
        self.transmission_var = ctk.StringVar(value=self.user_settings.get("transmission", TRANSMISSIONS[0]))
        self.vehicle_seats_var = ctk.StringVar(value=self.user_settings.get("vehicle_seats", SEAT_OPTIONS[0]))
        self.vehicle_type_var = ctk.StringVar(value=self.user_settings.get("vehicle_type", VEHICLE_TYPES[0]))
        self.search_mode_var = ctk.StringVar(value=self._saved_preset())
        self.cache_mode_var = ctk.StringVar(value=_saved_recent_price_choice(self.user_settings.get("cache_mode")))
        self.visible_browser_var = ctk.BooleanVar(
            value=bool(self.user_settings.get("visible_browser", self.settings.visible_browser))
        )
        self.status_var = ctk.StringVar(value="Planning a holiday to the Canary Islands?")
        self.detail_var = ctk.StringVar(
            value=(
                "Compare prices from trusted local car hire companies, or let the app try lots of dates, "
                "holiday lengths and collection times to help find the cheapest option."
            )
        )
        self.count_var = ctk.StringVar(value="0 checked")
        self.fact_var = ctk.StringVar(value="Recent results can be reused to save you time.")
        self.current_provider_var = ctk.StringVar(value="Not started")
        self.current_combination_var = ctk.StringVar(value="Choose your dates and click Find my car.")
        self.best_price_var = ctk.StringVar(value="--")
        self.cheapest_provider_var = ctk.StringVar(value="--")
        self.remaining_time_var = ctk.StringVar(value="--")
        self.advanced_visible = False
        self.support_var = ctk.StringVar(
            value=(
                "No adverts, subscriptions or affiliate links. If it helped, buying Jamie an Estrella is appreciated."
            )
        )

        self._build_layout()
        self.initializing = False
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.after_id = self.root.after(100, self._process_events)

    def run(self):
        self.root.mainloop()

    def _build_layout(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self._build_body()
        self._build_footer()

    def _build_body(self):
        body = ctk.CTkFrame(self.root, fg_color=COLORS["sky"], corner_radius=0)
        body.grid(row=0, column=0, sticky="nsew")
        body.grid_columnconfigure(0, minsize=360, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(
            body,
            fg_color=COLORS["panel"],
            border_color=COLORS["line"],
            border_width=1,
            corner_radius=14,
            width=360,
        )
        sidebar.grid(row=0, column=0, padx=(28, 14), pady=28, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(0, weight=1)
        self.sidebar = sidebar

        form = ctk.CTkScrollableFrame(
            sidebar,
            fg_color=COLORS["panel"],
            corner_radius=0,
            border_width=0,
        )
        form.grid(row=0, column=0, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkFrame(form, fg_color="transparent")
        brand.grid(row=0, column=0, padx=24, pady=(16, 8), sticky="ew")
        brand.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            brand,
            text="CI",
            width=40,
            height=40,
            corner_radius=10,
            fg_color=COLORS["ocean"],
            text_color="white",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, rowspan=2, padx=(0, 12), sticky="nw")
        ctk.CTkLabel(
            brand,
            text="Canary Islands Car Hire Optimiser",
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=18, weight="bold"),
            wraplength=245,
            justify="left",
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            brand,
            text="Trusted local car hire",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=13),
        ).grid(row=1, column=1, sticky="w")

        self.preset_help_var = ctk.StringVar()
        self._section_label(form, "What would you like to do?", 1)
        self._preset_radios(form, 2)
        self.preset_help_var.set("")

        self.date_help_var = ctk.StringVar()
        self.length_help_var = ctk.StringVar()

        self._section_label(form, "Pickup location", 3)
        ctk.CTkLabel(
            form,
            text="Fuerteventura Airport",
            text_color=COLORS["ink"],
            fg_color="#fbfdfd",
            corner_radius=10,
            height=36,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=4, column=0, padx=24, pady=(0, 10), sticky="ew")

        self._section_label(form, "Hire dates", 5)
        self._date_pair(form, 6)
        self._section_label(form, "Hire length", 7)
        self._entry_pair(form, 8)
        action_frame = ctk.CTkFrame(sidebar, fg_color=COLORS["panel"], corner_radius=0)
        action_frame.grid(row=1, column=0, padx=16, pady=(4, 6), sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        self.search_button = ctk.CTkButton(
            action_frame,
            text="Find my car",
            height=42,
            corner_radius=12,
            fg_color=COLORS["sun"],
            hover_color="#d99b2e",
            text_color="#1f2d32",
            font=ctk.CTkFont(size=21, weight="bold"),
            command=self._start_search,
        )
        self.search_button.grid(row=0, column=0, padx=8, pady=(0, 6), sticky="ew")

        self.advanced_button = ctk.CTkButton(
            action_frame,
            text="Need more control? Show search options",
            height=34,
            fg_color="#edf6f7",
            hover_color=COLORS["sand"],
            text_color=COLORS["deep_ocean"],
            command=self._toggle_advanced,
        )
        self.advanced_button.grid(row=1, column=0, padx=8, pady=(0, 0), sticky="ew")

        self.advanced_frame = ctk.CTkFrame(form, fg_color="#f8fbfb", border_color=COLORS["line"], border_width=1, corner_radius=12)
        self.advanced_frame.grid(row=9, column=0, padx=24, pady=(0, 12), sticky="ew")
        self.advanced_frame.grid_columnconfigure(0, weight=1)
        self._section_label(self.advanced_frame, "Pickup and return time windows", 0)
        self._option(
            self.advanced_frame,
            "Time choice",
            self.time_mode_var,
            TIME_MODES,
            1,
            command=lambda _: self._refresh_time_mode(),
        )
        self.pickup_time_window_controls = self._time_window_selector(
            self.advanced_frame, "Pick up between", self.pickup_time_var, self.pickup_time_latest_var, 2
        )
        self.return_time_window_controls = self._time_window_selector(
            self.advanced_frame, "Return between", self.return_time_var, self.return_time_latest_var, 3
        )
        ctk.CTkLabel(
            self.advanced_frame,
            text="Choose earliest and latest times. The app adjusts them for each provider first, then skips duplicate searches before estimating the runtime.",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            wraplength=270,
            justify="left",
        ).grid(row=8, column=0, padx=26, pady=(0, 12), sticky="w")
        self._section_label(self.advanced_frame, "Car preferences", 9)
        self._option(self.advanced_frame, "Transmission", self.transmission_var, TRANSMISSIONS, 10)
        self._option(self.advanced_frame, "Vehicle seats", self.vehicle_seats_var, SEAT_OPTIONS, 11)
        self._option(self.advanced_frame, "Vehicle type", self.vehicle_type_var, VEHICLE_TYPES, 12)
        self._section_label(self.advanced_frame, "Speed and display", 19)
        self._option(self.advanced_frame, "Reuse recent results", self.cache_mode_var, CACHE_MODE_OPTIONS, 20)

        browser_toggle = ctk.CTkSwitch(
            self.advanced_frame,
            text="Show the provider websites while checking prices",
            variable=self.visible_browser_var,
            onvalue=True,
            offvalue=False,
            progress_color=COLORS["ocean"],
            button_color=COLORS["sun"],
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=13),
        )
        browser_toggle.grid(row=42, column=0, padx=26, pady=(10, 18), sticky="w")
        self.advanced_frame.grid_remove()

        self._apply_preset()
        self._refresh_time_mode()

        self._build_support_panel(form)

        content = ctk.CTkFrame(body, fg_color="transparent")
        content.grid(row=0, column=1, padx=(14, 28), pady=28, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        self._build_status_panel(content)

    def _build_status_panel(self, parent):
        status = ctk.CTkFrame(parent, fg_color=COLORS["panel"], border_color=COLORS["line"], border_width=1, corner_radius=14)
        status.grid(row=0, column=0, sticky="ew")
        status.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            status,
            text="What is happening now",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=26, pady=(24, 4), sticky="w")
        ctk.CTkLabel(
            status,
            textvariable=self.status_var,
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=26, weight="bold"),
        ).grid(row=1, column=0, padx=26, pady=(0, 6), sticky="w")
        ctk.CTkLabel(
            status,
            textvariable=self.detail_var,
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=14),
            wraplength=560,
        ).grid(row=2, column=0, padx=26, pady=(0, 18), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(status, height=16, progress_color=COLORS["ocean"])
        self.progress_bar.grid(row=3, column=0, padx=26, pady=(0, 8), sticky="ew")
        self.progress_bar.set(0)

        ctk.CTkLabel(status, textvariable=self.count_var, text_color=COLORS["muted"]).grid(
            row=4, column=0, padx=26, pady=(0, 22), sticky="w"
        )
        ctk.CTkLabel(
            status,
            textvariable=self.fact_var,
            text_color=COLORS["deep_ocean"],
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=560,
        ).grid(row=5, column=0, padx=26, pady=(0, 22), sticky="w")

        dashboard = ctk.CTkFrame(status, fg_color="#f8fbfb", border_color=COLORS["line"], border_width=1, corner_radius=14)
        dashboard.grid(row=6, column=0, padx=26, pady=(0, 20), sticky="ew")
        dashboard.grid_columnconfigure((0, 1), weight=1)
        self._dashboard_stat(dashboard, "Current provider", self.current_provider_var, 0, 0)
        self._dashboard_stat(dashboard, "Current search", self.current_combination_var, 0, 1)
        self._dashboard_stat(dashboard, "Best price so far", self.best_price_var, 1, 0)
        self._dashboard_stat(dashboard, "Cheapest provider", self.cheapest_provider_var, 1, 1)
        self._dashboard_stat(dashboard, "Estimated time left", self.remaining_time_var, 2, 0)

        controls = ctk.CTkFrame(dashboard, fg_color="transparent")
        controls.grid(row=2, column=1, padx=14, pady=(0, 14), sticky="ew")
        controls.grid_columnconfigure((0, 1), weight=1)
        self.pause_button = ctk.CTkButton(
            controls,
            text="Pause Search",
            height=34,
            state="disabled",
            fg_color="#edf6f7",
            hover_color=COLORS["sand"],
            text_color=COLORS["deep_ocean"],
            command=self._toggle_pause,
        )
        self.pause_button.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.stop_button = ctk.CTkButton(
            controls,
            text="Stop Search",
            height=34,
            state="disabled",
            fg_color=COLORS["coral"],
            hover_color="#bf574b",
            command=self._stop_search,
        )
        self.stop_button.grid(row=0, column=1, sticky="ew")

        self.log = ctk.CTkTextbox(
            parent,
            height=220,
            fg_color="#fdfefe",
            border_color=COLORS["line"],
            border_width=1,
            text_color=COLORS["ink"],
            wrap="word",
            corner_radius=14,
        )
        self.log.grid(row=1, column=0, pady=(18, 18), sticky="nsew")
        self.log.configure(state="disabled")

    def _build_support_panel(self, parent):
        support = ctk.CTkFrame(parent, fg_color=COLORS["sand"], corner_radius=14)
        support.grid(row=12, column=0, padx=24, pady=(8, 24), sticky="ew")
        support.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            support,
            text="Enjoying the app?",
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, padx=16, pady=(12, 6), sticky="w")
        ctk.CTkLabel(
            support,
            textvariable=self.support_var,
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            wraplength=250,
            justify="left",
        ).grid(row=1, column=0, padx=16, pady=(0, 10), sticky="w")
        ctk.CTkButton(
            support,
            text="Buy Jamie an Estrella",
            width=0,
            height=30,
            fg_color=COLORS["coral"],
            hover_color="#bf574b",
            command=self._open_donation,
        ).grid(row=2, column=0, padx=16, pady=(0, 12), sticky="ew")

    def _build_footer(self):
        footer = ctk.CTkFrame(self.root, fg_color=COLORS["sky"], corner_radius=0)
        footer.grid(row=1, column=0, sticky="ew")
        footer.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            footer,
            text=f"{self.app_name} {self.app_version}",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=0, padx=28, pady=(0, 16), sticky="w")
        utility = ctk.CTkFrame(footer, fg_color="transparent")
        utility.grid(row=0, column=2, padx=28, pady=(0, 16), sticky="e")
        ctk.CTkButton(
            utility,
            text="Help",
            width=76,
            height=30,
            fg_color="#edf6f7",
            hover_color=COLORS["sand"],
            text_color=COLORS["deep_ocean"],
            command=self._show_help,
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            utility,
            text="About",
            width=76,
            height=30,
            fg_color="#edf6f7",
            hover_color=COLORS["sand"],
            text_color=COLORS["deep_ocean"],
            command=self._show_about,
        ).grid(row=0, column=1)

    def _dashboard_stat(self, parent, label, variable, row, column):
        card = ctk.CTkFrame(parent, fg_color=COLORS["panel"], corner_radius=12)
        card.grid(row=row, column=column, padx=14, pady=(14, 10), sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text=label,
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, padx=14, pady=(12, 2), sticky="w")
        ctk.CTkLabel(
            card,
            textvariable=variable,
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=17, weight="bold"),
            wraplength=250,
            justify="left",
        ).grid(row=1, column=0, padx=14, pady=(0, 12), sticky="w")

    def _entry(self, parent, label, variable, row):
        ctk.CTkLabel(parent, text=label, text_color=COLORS["ink"], font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=row * 2 - 1, column=0, padx=26, pady=(4, 5), sticky="w"
        )
        field = ctk.CTkEntry(
            parent,
            textvariable=variable,
            height=42,
            corner_radius=10,
            border_color=COLORS["line"],
            fg_color="#fbfdfd",
        )
        field.grid(row=row * 2, column=0, padx=26, pady=(0, 14), sticky="ew")

    def _preset_radios(self, parent, row):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, padx=24, pady=(0, 8), sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        subtitles = {
            QUICK_SEARCH: "One exact set of dates and times. Fastest option.",
            SMART_SEARCH: "Nearby dates and pickup times. Best balance of speed and savings.",
            THOROUGH_SEARCH: "Hundreds of combinations. Slower, but most likely to find the lowest price.",
        }
        for index, value in enumerate(SEARCH_PRESETS):
            option = ctk.CTkFrame(frame, fg_color="#f8fbfb", border_color=COLORS["line"], border_width=1, corner_radius=10)
            option.grid(row=index, column=0, padx=0, pady=2, sticky="ew")
            option.grid_columnconfigure(0, weight=1)
            radio = ctk.CTkRadioButton(
                option,
                text=value,
                value=value,
                variable=self.search_mode_var,
                command=self._apply_preset,
                radiobutton_width=20,
                radiobutton_height=20,
                border_color=COLORS["ocean"],
                fg_color=COLORS["ocean"],
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=COLORS["ink"],
            )
            radio.grid(row=0, column=0, padx=12, pady=(5, 0), sticky="w")
            ctk.CTkLabel(
                option,
                text=subtitles[value],
                text_color=COLORS["muted"],
                font=ctk.CTkFont(size=12),
                wraplength=230,
                justify="left",
                anchor="w",
            ).grid(row=1, column=0, padx=(42, 10), pady=(0, 5), sticky="ew")

    def _section_label(self, parent, label, row):
        ctk.CTkLabel(
            parent,
            text=label,
            text_color=COLORS["ocean"],
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=row, column=0, padx=24, pady=(6, 4), sticky="w")

    def _date_picker(self, parent, label, iso_variable, display_variable, row):
        ctk.CTkLabel(parent, text=label, text_color=COLORS["ink"], font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=row * 2 - 1, column=0, padx=26, pady=(4, 5), sticky="w"
        )
        button = ctk.CTkButton(
            parent,
            textvariable=display_variable,
            height=42,
            corner_radius=10,
            fg_color="#fbfdfd",
            hover_color=COLORS["sand"],
            border_color=COLORS["line"],
            border_width=1,
            text_color=COLORS["ink"],
            command=lambda: self._open_calendar(iso_variable, display_variable),
        )
        button.grid(row=row * 2, column=0, padx=26, pady=(0, 14), sticky="ew")

    def _date_pair(self, parent, row):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, padx=24, pady=(0, 8), sticky="ew")
        frame.grid_columnconfigure((0, 1), weight=1, uniform="dates")
        self._compact_date(frame, "Collect", self.pickup_date_var, self.pickup_date_display_var, 0)
        self._compact_date(frame, "Return", self.return_date_var, self.return_date_display_var, 1)

    def _compact_date(self, parent, label, iso_variable, display_variable, column):
        ctk.CTkLabel(
            parent,
            text=label,
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=column, padx=(0 if column == 0 else 6, 6 if column == 0 else 0), pady=(0, 5), sticky="w")
        ctk.CTkButton(
            parent,
            textvariable=display_variable,
            height=30,
            corner_radius=10,
            fg_color="#fbfdfd",
            hover_color=COLORS["sand"],
            border_color=COLORS["line"],
            border_width=1,
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self._open_calendar(iso_variable, display_variable),
        ).grid(row=1, column=column, padx=(0 if column == 0 else 6, 6 if column == 0 else 0), sticky="ew")

    def _entry_pair(self, parent, row):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, padx=24, pady=(0, 8), sticky="ew")
        frame.grid_columnconfigure((0, 1), weight=1, uniform="length")
        self._compact_entry(frame, "Shortest", self.min_days_var, 0)
        self._compact_entry(frame, "Longest", self.max_days_var, 1)

    def _compact_entry(self, parent, label, variable, column):
        ctk.CTkLabel(
            parent,
            text=label,
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=column, padx=(0 if column == 0 else 6, 6 if column == 0 else 0), pady=(0, 5), sticky="w")
        ctk.CTkEntry(
            parent,
            textvariable=variable,
            height=34,
            corner_radius=10,
            border_color=COLORS["line"],
            fg_color="#fbfdfd",
            font=ctk.CTkFont(size=14),
        ).grid(row=1, column=column, padx=(0 if column == 0 else 6, 6 if column == 0 else 0), sticky="ew")

    def _option(self, parent, label, variable, values, row, command=None):
        ctk.CTkLabel(parent, text=label, text_color=COLORS["ink"], font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=row * 2 - 1, column=0, padx=26, pady=(4, 5), sticky="w"
        )
        menu = ctk.CTkOptionMenu(
            parent,
            values=values,
            variable=variable,
            command=command,
            height=42,
            corner_radius=10,
            fg_color=COLORS["ocean"],
            button_color=COLORS["deep_ocean"],
            button_hover_color=COLORS["sun"],
        )
        menu.grid(row=row * 2, column=0, padx=26, pady=(0, 14), sticky="ew")
        return menu

    def _time_selector(self, parent, label, variable, row):
        ctk.CTkLabel(parent, text=label, text_color=COLORS["ink"], font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=row * 2 - 1, column=0, padx=26, pady=(4, 5), sticky="w"
        )
        menu = ctk.CTkOptionMenu(
            parent,
            values=TIME_OPTIONS,
            variable=variable,
            height=42,
            corner_radius=10,
            fg_color=COLORS["ocean"],
            button_color=COLORS["deep_ocean"],
            button_hover_color=COLORS["sun"],
        )
        menu.grid(row=row * 2, column=0, padx=26, pady=(0, 14), sticky="ew")
        return menu

    def _time_window_selector(self, parent, label, earliest_variable, latest_variable, row):
        ctk.CTkLabel(parent, text=label, text_color=COLORS["ink"], font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=row * 2 - 1, column=0, padx=26, pady=(4, 5), sticky="w"
        )
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row * 2, column=0, padx=26, pady=(0, 14), sticky="ew")
        frame.grid_columnconfigure((0, 1), weight=1, uniform="time-window")
        earliest = ctk.CTkOptionMenu(
            frame,
            values=TIME_OPTIONS,
            variable=earliest_variable,
            height=38,
            corner_radius=10,
            fg_color=COLORS["ocean"],
            button_color=COLORS["deep_ocean"],
            button_hover_color=COLORS["sun"],
        )
        earliest.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        latest = ctk.CTkOptionMenu(
            frame,
            values=TIME_OPTIONS,
            variable=latest_variable,
            height=38,
            corner_radius=10,
            fg_color=COLORS["ocean"],
            button_color=COLORS["deep_ocean"],
            button_hover_color=COLORS["sun"],
        )
        latest.grid(row=0, column=1, padx=(6, 0), sticky="ew")
        return earliest, latest

    def _open_calendar(self, iso_variable, display_variable):
        selected = date.fromisoformat(iso_variable.get())
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Select date")
        dialog.geometry("340x360")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["sky"])
        dialog.transient(self.root)
        dialog.grab_set()

        state = {"year": selected.year, "month": selected.month}
        panel = ctk.CTkFrame(dialog, fg_color=COLORS["panel"], corner_radius=12)
        panel.pack(fill="both", expand=True, padx=16, pady=16)

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(12, 8))
        title = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(side="left", expand=True)

        grid = ctk.CTkFrame(panel, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=10, pady=10)

        def choose(day):
            picked = date(state["year"], state["month"], day)
            iso_variable.set(picked.isoformat())
            display_variable.set(_display_date(picked.isoformat()))
            dialog.destroy()

        def render():
            for child in grid.winfo_children():
                child.destroy()
            title.configure(text=f"{calendar.month_name[state['month']]} {state['year']}")
            for col, day_name in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
                ctk.CTkLabel(grid, text=day_name, text_color=COLORS["muted"]).grid(row=0, column=col, padx=2, pady=2)
            for row_index, week in enumerate(calendar.monthcalendar(state["year"], state["month"]), start=1):
                for col, day in enumerate(week):
                    if not day:
                        ctk.CTkLabel(grid, text="").grid(row=row_index, column=col, padx=2, pady=2)
                        continue
                    ctk.CTkButton(grid, text=str(day), width=36, height=30, command=lambda value=day: choose(value)).grid(
                        row=row_index, column=col, padx=2, pady=2
                    )

        def move(month_delta):
            month = state["month"] + month_delta
            year = state["year"]
            if month < 1:
                month = 12
                year -= 1
            elif month > 12:
                month = 1
                year += 1
            state["month"] = month
            state["year"] = year
            render()

        ctk.CTkButton(header, text="<", width=36, command=lambda: move(-1)).pack(side="left", padx=(0, 8))
        ctk.CTkButton(header, text=">", width=36, command=lambda: move(1)).pack(side="right", padx=(8, 0))
        render()

    def _start_search(self):
        if self.search_running:
            return

        try:
            search_settings, mode = self._search_settings()
        except ValueError as exc:
            self._set_status("Check dates", str(exc), 0, 0)
            self._append_log(f"Input error: {exc}")
            return

        estimate = estimate_search(search_settings, mode)
        if not self._confirm_search(estimate):
            self._set_status("Search cancelled", "No provider websites were searched.", 0, 0)
            return

        self._save_user_settings()
        self.search_running = True
        self.stop_requested.clear()
        self.pause_requested.clear()
        self.search_button.configure(state="disabled", text="Checking prices...")
        self.pause_button.configure(state="normal", text="Pause Search")
        self.stop_button.configure(state="normal")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.support_var.set("Checking prices now. I will show the saving once everything is compared.")
        self.current_provider_var.set("Getting ready")
        self.current_combination_var.set("Preparing provider websites")
        self.best_price_var.set("--")
        self.cheapest_provider_var.set("--")
        self.remaining_time_var.set("--")
        self._set_status("Getting ready", "Preparing to check the provider websites", 0, 0)

        self.worker = threading.Thread(target=self._run_search, args=(search_settings, mode), daemon=True)
        self.worker.start()

    def _search_settings(self):
        try:
            pickup = date.fromisoformat(self.pickup_date_var.get().strip())
            dropoff = date.fromisoformat(self.return_date_var.get().strip())
        except ValueError as exc:
            raise ValueError("Choose valid dates using the calendar picker.") from exc

        if dropoff <= pickup:
            raise ValueError("Return date must be after pickup date.")

        total_days = (dropoff - pickup).days
        preset = self.search_mode_var.get()
        mode = "single" if preset == COMPARE_EXACT_DATES else "full"
        if mode == "single":
            min_days = total_days
            max_days = total_days
        else:
            try:
                min_days = int(self.min_days_var.get().strip())
                max_days = int(self.max_days_var.get().strip())
            except ValueError as exc:
                raise ValueError("Enter whole numbers for the shortest and longest holiday.") from exc
            if min_days < 1:
                raise ValueError("The shortest holiday must be at least 1 day.")
            if max_days < min_days:
                raise ValueError("The longest holiday must be the same as, or longer than, the shortest holiday.")
            if max_days > total_days:
                raise ValueError("The longest holiday cannot be longer than the dates you selected.")

        search_settings = replace(
            self.settings,
            start_date=pickup,
            end_date=dropoff,
            min_days=min_days,
            max_days=max_days,
            pickup_time=self.pickup_time_var.get(),
            return_time=self.return_time_var.get(),
            final_return_time=self.return_time_var.get(),
            visible_browser=self.visible_browser_var.get(),
        )
        search_settings.transmission = self.transmission_var.get()
        search_settings.vehicle_seats = self.vehicle_seats_var.get()
        search_settings.vehicle_type = self.vehicle_type_var.get()
        search_settings.cache_mode = self.cache_mode_var.get()
        search_settings.time_mode = USE_CHOSEN_TIMES if preset == QUICK_SEARCH else self.time_mode_var.get()
        if preset == QUICK_SEARCH:
            search_settings.pickup_times = [self.pickup_time_var.get()]
            search_settings.return_times = [self.return_time_var.get()]
        elif search_settings.time_mode == USE_CHOSEN_TIMES:
            search_settings.pickup_times = [self.pickup_time_var.get()]
            search_settings.return_times = [self.return_time_var.get()]
        else:
            search_settings.pickup_times = self._generated_time_window(
                self.pickup_time_var.get(), self.pickup_time_latest_var.get(), "pickup"
            )
            search_settings.return_times = self._generated_time_window(
                self.return_time_var.get(), self.return_time_latest_var.get(), "return"
            )
        search_settings.pickup_time = search_settings.pickup_times[0]
        search_settings.return_time = search_settings.return_times[0]
        search_settings.final_return_time = search_settings.return_times[0]
        return search_settings, mode

    def _run_search(self, search_settings, mode):
        try:
            rows, reports = run_search(
                search_settings,
                mode,
                progress_callback=self._progress,
                stop_callback=self.stop_requested.is_set,
                pause_callback=self.pause_requested.is_set,
            )
            self.events.put(("done", rows, reports))
        except Exception as exc:
            self.events.put(("error", exc))

    def _progress(self, completed, total, message, summary=None):
        self.events.put(("progress", completed, total, message, summary or {}))

    def _process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "progress":
                    _, completed, total, message, summary = event
                    self._set_status("Checking prices", self._progress_detail(message, summary), completed, total)
                    self._append_log(f"[{completed}/{total}] {message}")
                elif kind == "done":
                    _, rows, reports = event
                    self._finish_search(rows, reports)
                elif kind == "error":
                    _, exc = event
                    self._fail_search(exc)
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.after_id = self.root.after(100, self._process_events)

    def _close(self):
        self.stop_requested.set()
        if self.after_id:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None
        self.root.destroy()

    def _finish_search(self, rows, reports):
        _, _, html_path = reports
        total = len(rows)
        if self.stop_requested.is_set():
            self._set_status("Search stopped", f"Opening a report with the best results found so far: {html_path.resolve()}", total, total)
            self._append_log("Search stopped. Completed results were kept and included in the report.")
        else:
            self._set_status("Your results are ready", f"Opening your report: {html_path.resolve()}", total, total)
        self._append_log(f"Checked {total} prices.")
        self._update_support_message(rows)
        self.search_running = False
        self.search_button.configure(state="normal", text="Find my car")
        self.pause_button.configure(state="disabled", text="Pause Search")
        self.stop_button.configure(state="disabled")
        webbrowser.open(html_path.resolve().as_uri())

    def _fail_search(self, exc):
        self._set_status("Something went wrong", str(exc), 0, 0)
        self._append_log(f"Could not finish checking prices: {exc}")
        self.support_var.set(
            "No adverts, subscriptions or affiliate links. If it helped, buying Jamie an Estrella is appreciated."
        )
        self.search_running = False
        self.search_button.configure(state="normal", text="Find my car")
        self.pause_button.configure(state="disabled", text="Pause Search")
        self.stop_button.configure(state="disabled")

    def _toggle_pause(self):
        if not self.search_running:
            return
        if self.pause_requested.is_set():
            self.pause_requested.clear()
            self.pause_button.configure(text="Pause Search")
            self._append_log("Search resumed.")
            self.fact_var.set("Back to checking live prices.")
        else:
            self.pause_requested.set()
            self.pause_button.configure(text="Resume Search")
            self._append_log("Search paused. Completed results are safe.")
            self.fact_var.set("Paused. Resume when you are ready, or stop to keep the results found so far.")

    def _stop_search(self):
        if not self.search_running:
            return
        self.stop_requested.set()
        self.pause_requested.clear()
        self.pause_button.configure(state="disabled", text="Pause Search")
        self.stop_button.configure(state="disabled")
        self._set_status("Stopping search", "Finishing the current provider check, then your report will open with completed results.", 0, 0)
        self._append_log("Stop requested. Keeping completed results.")

    def _set_status(self, title, detail, completed, total):
        self.status_var.set(title)
        self.detail_var.set(detail)
        self.count_var.set(f"{completed} of {total} checked" if total else "0 checked")
        self.progress_bar.set(completed / total if total else 0)

    def _append_log(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", f"{message}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _update_support_message(self, rows):
        prices = [float(row["price"]) for row in rows if row.get("success") and row.get("price")]
        if len(prices) >= 2:
            saved = max(prices) - min(prices)
            if saved > 0.009:
                self.support_var.set(f"You saved EUR {saved:.2f} today. Fancy buying Jamie an Estrella?")
                return
        self.support_var.set(
            "No adverts, subscriptions or affiliate links. If it helped, buying Jamie an Estrella is appreciated."
        )

    def _show_about(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"About {self.app_name}")
        dialog.geometry("520x460")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["sky"])
        dialog.transient(self.root)
        dialog.grab_set()

        panel = ctk.CTkFrame(dialog, fg_color=COLORS["panel"], corner_radius=14)
        panel.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(
            panel,
            text=self.app_name,
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(24, 6))
        ctk.CTkLabel(
            panel,
            text=f"Version {self.app_version}",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=14),
        ).pack(anchor="w", padx=24)
        ctk.CTkLabel(
            panel,
            text=(
                "A local Windows application that compares prices from four trusted "
                "Canary Islands car hire companies."
            ),
            text_color=COLORS["ink"],
            wraplength=430,
            justify="left",
            font=ctk.CTkFont(size=15),
        ).pack(anchor="w", padx=24, pady=(18, 12))
        ctk.CTkLabel(
            panel,
            text="\n".join(f"- {provider}" for provider in PROVIDERS),
            text_color=COLORS["muted"],
            justify="left",
            font=ctk.CTkFont(size=14),
        ).pack(anchor="w", padx=32, pady=(0, 22))

        ctk.CTkButton(panel, text="GitHub Repository", command=self._open_github).pack(
            fill="x", padx=24, pady=(0, 10)
        )
        ctk.CTkButton(
            panel,
            text="Report an Issue",
            fg_color=COLORS["coral"],
            hover_color="#bf574b",
            command=self._open_issue,
        ).pack(fill="x", padx=24, pady=(0, 18))
        ctk.CTkButton(panel, text="Close", fg_color="#7b8f96", command=dialog.destroy).pack(
            fill="x", padx=24, pady=(0, 24)
        )

    def _open_github(self):
        webbrowser.open(self.app_config.get("github_url", ""))

    def _open_issue(self):
        webbrowser.open(self.app_config.get("issue_url", ""))

    def _open_donation(self):
        donation_url = self.app_config.get("donation_url")
        if donation_url:
            webbrowser.open(donation_url)

    def _load_user_settings(self):
        if not USER_SETTINGS_PATH.exists():
            return {}
        try:
            return json.loads(USER_SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _saved_preset(self):
        saved = self.user_settings.get("search_mode", SEARCH_PRESETS[0])
        if saved in {"Single Search", "Compare Exact Dates", QUICK_SEARCH}:
            return QUICK_SEARCH
        if saved in {"Holiday Optimiser", "Find the Cheapest Holiday", "Smart Search", SMART_SEARCH}:
            return SMART_SEARCH
        if saved in {"Deep Search", THOROUGH_SEARCH}:
            return THOROUGH_SEARCH
        if saved in SEARCH_PRESETS:
            return saved
        return SEARCH_PRESETS[0]

    def _save_user_settings(self):
        data = {
            "pickup_date": self.pickup_date_var.get().strip(),
            "return_date": self.return_date_var.get().strip(),
            "pickup_time": self.pickup_time_var.get(),
            "return_time": self.return_time_var.get(),
            "pickup_time_latest": self.pickup_time_latest_var.get(),
            "return_time_latest": self.return_time_latest_var.get(),
            "time_mode": self.time_mode_var.get(),
            "min_days": self.min_days_var.get().strip(),
            "max_days": self.max_days_var.get().strip(),
            "search_mode": self.search_mode_var.get(),
            "cache_mode": self.cache_mode_var.get(),
            "transmission": self.transmission_var.get(),
            "vehicle_seats": self.vehicle_seats_var.get(),
            "vehicle_type": self.vehicle_type_var.get(),
            "visible_browser": self.visible_browser_var.get(),
        }
        USER_SETTINGS_PATH.parent.mkdir(exist_ok=True)
        USER_SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _apply_preset(self):
        preset = self.search_mode_var.get()
        if preset == QUICK_SEARCH:
            self.preset_help_var.set("One exact set of dates and times. Fastest option.")
            self.date_help_var.set("Use these as your collection and return dates.")
            self.length_help_var.set("We work out the number of hire days from your dates.")
            self.cache_mode_var.set("Reuse prices from today")
            self.time_mode_var.set(USE_CHOSEN_TIMES)
        elif preset == SMART_SEARCH:
            self.preset_help_var.set(
                "Search nearby dates and nearby collection times. Good balance between speed and savings."
            )
            self.date_help_var.set("Choose the earliest date you could leave and the latest date you could return.")
            self.length_help_var.set("We will try hire lengths between these shortest and longest stays.")
            self.cache_mode_var.set("Reuse prices from today")
            self.time_mode_var.set(TRY_NEARBY_TIMES)
            if not self.initializing:
                self._set_default_time_window(60)
        else:
            self.preset_help_var.set(
                "Search hundreds of date, hire length and collection-time choices. Slower, but most thorough."
            )
            self.date_help_var.set("Choose the widest dates you could travel between.")
            self.length_help_var.set("We will try every hire length in this range.")
            self.cache_mode_var.set("Reuse prices from today")
            self.time_mode_var.set(TRY_NEARBY_TIMES)
            if not self.initializing:
                self._set_default_time_window(120)
        self._refresh_time_mode()

    def _toggle_advanced(self):
        self.advanced_visible = not self.advanced_visible
        if self.advanced_visible:
            self.advanced_frame.grid()
            self.advanced_button.configure(text="Hide search options")
        else:
            self.advanced_frame.grid_remove()
            self.advanced_button.configure(text="Need more control? Show search options")

    def _refresh_time_mode(self):
        state = "normal" if self.time_mode_var.get() == TRY_NEARBY_TIMES else "disabled"
        for controls in (getattr(self, "pickup_time_window_controls", ()), getattr(self, "return_time_window_controls", ())):
            for index, control in enumerate(controls):
                if index == 0:
                    control.configure(state="normal")
                else:
                    control.configure(state=state)

    def _generated_time_window(self, earliest, latest, label):
        if earliest not in TIME_OPTIONS or latest not in TIME_OPTIONS:
            raise ValueError("Choose pickup and return times from the list.")
        start = _time_to_minutes(earliest)
        end = _time_to_minutes(latest)
        if end < start:
            raise ValueError(f"The latest {label} time must be after the earliest {label} time.")
        return [value for value in TIME_OPTIONS if start <= _time_to_minutes(value) <= end]

    def _set_default_time_window(self, minutes):
        pickup_start, pickup_end = _time_window_around(self.pickup_time_var.get(), minutes)
        return_start, return_end = _time_window_around(self.return_time_var.get(), minutes)
        self.pickup_time_var.set(pickup_start)
        self.pickup_time_latest_var.set(pickup_end)
        self.return_time_var.set(return_start)
        self.return_time_latest_var.set(return_end)

    def _confirm_search(self, estimate):
        searches = estimate.get("provider_searches_estimated", 0)
        runtime = estimate.get("estimated_duration_text", "Unknown")
        message = (
            f"This search will check approximately {searches} live prices.\n\n"
            f"Search size: {estimate.get('search_size_band', 'Small')}\n"
            f"Dates to compare: {estimate.get('date_combinations_generated', 0)}\n"
            f"Time choices: {estimate.get('time_combinations_generated', 0)}\n"
            f"Duplicate searches skipped: {estimate.get('duplicate_searches_removed', 0)}\n"
            f"Recent results: {estimate.get('cache_mode', 'Always check fresh prices')}\n"
            f"Estimated time: {runtime}\n\n"
            "Continue?"
        )
        if searches > 1500:
            message = (
                f"This is an {estimate.get('search_size_band', 'Extreme').lower()} search.\n\n"
                f"It will check approximately {searches} live prices.\n\n"
                f"Duplicate searches already skipped: {estimate.get('duplicate_searches_removed', 0)}\n"
                f"Estimated time: {runtime}.\n\n"
                "You can continue, or make the search faster."
            )
            if self._long_search_dialog(message):
                return True
            messagebox.showinfo(
                "Make it faster",
                "For faster results, try a smaller date range, fewer hire lengths, or choose exact pickup and return times.",
                parent=self.root,
            )
            return False
        return messagebox.askokcancel("Start checking prices?", message, parent=self.root)

    def _long_search_dialog(self, message):
        result = {"continue": False}
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("This may take a little while")
        dialog.geometry("460x330")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["sky"])
        dialog.transient(self.root)
        dialog.grab_set()

        panel = ctk.CTkFrame(dialog, fg_color=COLORS["panel"], corner_radius=16)
        panel.pack(fill="both", expand=True, padx=22, pady=22)
        ctk.CTkLabel(
            panel,
            text="This search may take a little while",
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=22, weight="bold"),
            wraplength=380,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(22, 10))
        ctk.CTkLabel(
            panel,
            text=message,
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=14),
            wraplength=380,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 18))

        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.pack(fill="x", padx=22, pady=(0, 22))
        buttons.grid_columnconfigure((0, 1), weight=1)

        def choose_continue():
            result["continue"] = True
            dialog.destroy()

        def choose_faster():
            result["continue"] = False
            dialog.destroy()

        ctk.CTkButton(
            buttons,
            text="Make it Faster",
            height=38,
            fg_color="#edf6f7",
            hover_color=COLORS["sand"],
            text_color=COLORS["deep_ocean"],
            command=choose_faster,
        ).grid(row=0, column=0, padx=(0, 10), sticky="ew")
        ctk.CTkButton(
            buttons,
            text="Continue",
            height=38,
            fg_color=COLORS["sun"],
            hover_color="#d99b2e",
            text_color="#1f2d32",
            command=choose_continue,
        ).grid(row=0, column=1, sticky="ew")

        self.root.wait_window(dialog)
        return result["continue"]

    def _progress_detail(self, message, summary):
        if not summary:
            return message
        remaining = max(summary.get("total_provider_searches", 0) - summary.get("provider_searches_completed", 0), 0)
        self.current_provider_var.set(str(summary.get("current_provider") or "N/A"))
        self.current_combination_var.set(
            f"{summary.get('current_holiday', 'N/A')} / {summary.get('current_time_combination', 'N/A')}"
        )
        best = summary.get("best_price_so_far")
        self.best_price_var.set(f"EUR {float(best):.2f}" if best else "--")
        self.cheapest_provider_var.set(str(summary.get("cheapest_provider_so_far") or "--"))
        self.remaining_time_var.set(_duration_text(summary.get("estimated_remaining_seconds")))
        self.fact_var.set(_search_fact(summary, message))
        return (
            f"{message}\n"
            f"Reused recent results: {summary.get('cache_hits', 0)} / Checked live: {summary.get('live_searches', 0)} / "
            f"Still to check: {remaining}\n"
            f"Time so far: {_duration_text(summary.get('elapsed_seconds'))} / "
            f"About {_duration_text(summary.get('estimated_remaining_seconds'))} left"
        )

    def _show_help(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"How {self.app_name} Helps")
        dialog.geometry("620x560")
        dialog.configure(fg_color=COLORS["sky"])
        dialog.transient(self.root)
        dialog.grab_set()

        panel = ctk.CTkScrollableFrame(dialog, fg_color=COLORS["panel"], corner_radius=14)
        panel.pack(fill="both", expand=True, padx=24, pady=24)
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel,
            text="Why checking prices can take a little while",
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=26, weight="bold"),
        ).grid(row=0, column=0, padx=22, pady=(22, 12), sticky="w")
        help_text = (
            f"{self.app_name} checks PlusCar, AutoReisen, Cicar and Payless Car because they are trusted local companies.\n\n"
            "Choose Quick Search when your dates and times are fixed. It checks one exact holiday and is the fastest option.\n\n"
            "Choose Smart Search when you have a little flexibility. It checks nearby dates and pickup times to look for a better price without making you wait too long.\n\n"
            "Choose Thorough Search when price matters most. It can check hundreds of real prices, so it may take longer, but it gives the app the best chance of finding the cheapest option.\n\n"
            "Recent results can make repeat checks faster. Prices still come from the provider websites, so you can continue there when you are ready to book."
        )
        ctk.CTkLabel(
            panel,
            text=help_text,
            text_color=COLORS["ink"],
            justify="left",
            wraplength=540,
            font=ctk.CTkFont(size=15),
        ).grid(row=1, column=0, padx=22, pady=(0, 20), sticky="w")
        ctk.CTkButton(panel, text="Close", command=dialog.destroy).grid(
            row=2, column=0, padx=22, pady=(0, 22), sticky="ew"
        )

def _display_date(value):
    return date.fromisoformat(str(value)).strftime("%d/%m/%Y")


def _saved_time_mode(value):
    if value in {"Flexible Time", "Try nearby times", TRY_NEARBY_TIMES}:
        return TRY_NEARBY_TIMES
    return USE_CHOSEN_TIMES


def _saved_recent_price_choice(value):
    legacy = {
        "Live Search": "Always check fresh prices",
        "Smart Search": "Reuse prices from today",
        "Fast Search": "Reuse prices from this week",
    }
    return legacy.get(value, value if value in CACHE_MODE_OPTIONS else CACHE_MODE_OPTIONS[1])


def _time_to_minutes(value):
    hour, minute = [int(part) for part in value.split(":", 1)]
    return hour * 60 + minute


def _time_window_around(value, minutes):
    centre = _time_to_minutes(value)
    start = max(_time_to_minutes(TIME_OPTIONS[0]), centre - minutes)
    end = min(_time_to_minutes(TIME_OPTIONS[-1]), centre + minutes)
    return _nearest_time(start), _nearest_time(end)


def _nearest_time(minutes):
    return min(TIME_OPTIONS, key=lambda value: abs(_time_to_minutes(value) - minutes))


def _duration_text(seconds):
    if seconds is None:
        return "calculating"
    seconds = int(float(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    return f"{minutes // 60}h {minutes % 60}m"


def _search_fact(summary, message=""):
    provider = summary.get("current_provider")
    total = summary.get("total_provider_searches", 0)
    cache_hits = summary.get("cache_hits", 0)
    live = summary.get("live_searches", 0)
    completed = summary.get("provider_searches_completed", 0)
    messages = [
        "Checking live prices from trusted providers...",
        "Comparing trusted local companies...",
        "Looking for cheaper date combinations...",
        "Checking flexible pickup times...",
        "Searching another combination...",
        "Finding the best value for your holiday...",
    ]
    if cache_hits and cache_hits >= live:
        return "Reusing recent prices so you do not wait for the same checks again."
    if total and completed:
        return messages[completed % len(messages)]
    if provider and provider != "N/A":
        return f"Checking {provider} for the best confirmed price."
    if total:
        return f"Comparing up to {total} possible prices."
    return "Preparing your holiday search."


def main():
    global ctk
    try:
        import customtkinter as customtkinter
    except ModuleNotFoundError as exc:
        raise SystemExit("CustomTkinter is not installed. Run install_windows.bat, then start the app again.") from exc

    ctk = customtkinter
    setup_logging()
    CanaryCarFinderApp().run()


if __name__ == "__main__":
    main()
