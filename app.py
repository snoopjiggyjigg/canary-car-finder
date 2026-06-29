import calendar
from copy import replace
from datetime import date
import json
import os
from pathlib import Path
import queue
import sys
import threading
import webbrowser

if getattr(sys, "frozen", False):
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(Path(sys._MEIPASS) / "ms-playwright"))

from app_config import load_app_config
from runner import run_search
from settings import load_settings
from utils import setup_logging

ctk = None


USER_SETTINGS_PATH = Path("config/user_settings.json")
PICKUP_TIME_OPTIONS = ["09:00", "10:30", "11:00", "12:00", "13:00"]
RETURN_TIME_OPTIONS = ["16:30", "17:30", "18:00", "19:00"]
TRANSMISSIONS = ["Any", "Manual", "Automatic"]
SEARCH_MODES = ["Single Search", "Holiday Optimiser"]
SEAT_OPTIONS = ["Any", "2+", "4+", "5+", "7+", "9+"]
VEHICLE_TYPES = ["Any", "Mini", "Economy", "Compact", "Family", "SUV", "Van"]
PROVIDERS = ["PlusCar", "AutoReisen", "Cicar", "Payless Car"]

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
        self.after_id = None

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Canary Car Finder")
        self.root.geometry("1080x760")
        self.root.minsize(920, 680)
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
        self.pickup_time_vars = self._time_vars("pickup_times", PICKUP_TIME_OPTIONS, self.pickup_time_var.get())
        self.return_time_vars = self._time_vars("return_times", RETURN_TIME_OPTIONS, self.return_time_var.get())
        self.min_days_var = ctk.StringVar(value=str(self.user_settings.get("min_days", self.settings.min_days)))
        self.max_days_var = ctk.StringVar(value=str(self.user_settings.get("max_days", self.settings.max_days)))
        self.transmission_var = ctk.StringVar(value=self.user_settings.get("transmission", TRANSMISSIONS[0]))
        self.vehicle_seats_var = ctk.StringVar(value=self.user_settings.get("vehicle_seats", SEAT_OPTIONS[0]))
        self.vehicle_type_var = ctk.StringVar(value=self.user_settings.get("vehicle_type", VEHICLE_TYPES[0]))
        self.search_mode_var = ctk.StringVar(value=self.user_settings.get("search_mode", SEARCH_MODES[0]))
        self.visible_browser_var = ctk.BooleanVar(
            value=bool(self.user_settings.get("visible_browser", self.settings.visible_browser))
        )
        self.status_var = ctk.StringVar(value="Ready for your next Canary trip")
        self.detail_var = ctk.StringVar(
            value="Choose a single search or optimise every trip length in your holiday window."
        )
        self.count_var = ctk.StringVar(value="0 / 0")
        self.support_var = ctk.StringVar(
            value=(
                "If Canary Car Finder helped you find a cheaper hire car, consider buying me an Estrella. "
                "Every donation helps keep the application free and supports future improvements."
            )
        )

        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.after_id = self.root.after(100, self._process_events)

    def run(self):
        self.root.mainloop()

    def _build_layout(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self.root, fg_color=COLORS["deep_ocean"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title_block = ctk.CTkFrame(header, fg_color="transparent")
        title_block.grid(row=0, column=0, padx=34, pady=26, sticky="w")

        ctk.CTkLabel(
            title_block,
            text="Canary Car Finder",
            text_color="white",
            font=ctk.CTkFont(size=34, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            title_block,
            text="Compare four trusted Canary Islands car hire companies.",
            text_color="#d8f2f5",
            font=ctk.CTkFont(size=16),
        ).grid(row=1, column=0, pady=(6, 0), sticky="w")

        about_button = ctk.CTkButton(
            header,
            text="About",
            width=96,
            height=36,
            fg_color="#ffffff",
            hover_color=COLORS["sand"],
            text_color=COLORS["deep_ocean"],
            command=self._show_about,
        )
        about_button.grid(row=0, column=1, padx=34, pady=26, sticky="e")

    def _build_body(self):
        body = ctk.CTkFrame(self.root, fg_color=COLORS["sky"], corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, minsize=380)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        form = ctk.CTkScrollableFrame(
            body,
            fg_color=COLORS["panel"],
            border_color=COLORS["line"],
            border_width=1,
            corner_radius=14,
        )
        form.grid(row=0, column=0, padx=(28, 14), pady=28, sticky="nsew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form,
            text="Trip Details",
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, padx=26, pady=(26, 6), sticky="w")
        ctk.CTkLabel(
            form,
            text="Fuerteventura Airport search",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=14),
        ).grid(row=1, column=0, padx=26, pady=(0, 20), sticky="w")

        mode = ctk.CTkSegmentedButton(
            form,
            values=SEARCH_MODES,
            variable=self.search_mode_var,
            selected_color=COLORS["ocean"],
            selected_hover_color=COLORS["deep_ocean"],
            unselected_color="#edf6f7",
            unselected_hover_color=COLORS["sand"],
            text_color=COLORS["ink"],
            command=lambda _: self._update_mode_help(),
        )
        mode.grid(row=2, column=0, padx=26, pady=(0, 18), sticky="ew")

        self.date_help_var = ctk.StringVar()
        self.length_help_var = ctk.StringVar()

        self._section_label(form, "Holiday Window", 3)
        self._date_picker(form, "Earliest departure", self.pickup_date_var, self.pickup_date_display_var, 4)
        self._date_picker(form, "Latest return", self.return_date_var, self.return_date_display_var, 5)
        ctk.CTkLabel(
            form,
            textvariable=self.date_help_var,
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            wraplength=320,
        ).grid(row=11, column=0, padx=26, pady=(0, 10), sticky="w")
        self._section_label(form, "Trip Length", 12)
        self._entry(form, "Minimum trip length", self.min_days_var, 7)
        self._entry(form, "Maximum trip length", self.max_days_var, 8)
        ctk.CTkLabel(
            form,
            textvariable=self.length_help_var,
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
            wraplength=320,
        ).grid(row=17, column=0, padx=26, pady=(0, 10), sticky="w")
        self._section_label(form, "Time Optimisation", 18)
        self._time_checks(form, "Pickup Times", self.pickup_time_vars, 10)
        self._time_checks(form, "Return Times", self.return_time_vars, 11)
        self._section_label(form, "Vehicle Filters", 24)
        self._option(form, "Transmission", self.transmission_var, TRANSMISSIONS, 13)
        self._option(form, "Vehicle seats", self.vehicle_seats_var, SEAT_OPTIONS, 14)
        self._option(form, "Vehicle type", self.vehicle_type_var, VEHICLE_TYPES, 15)
        self._section_label(form, "Search Options", 31)

        browser_toggle = ctk.CTkSwitch(
            form,
            text="Show provider browser while searching",
            variable=self.visible_browser_var,
            onvalue=True,
            offvalue=False,
            progress_color=COLORS["ocean"],
            button_color=COLORS["sun"],
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=13),
        )
        browser_toggle.grid(row=32, column=0, padx=26, pady=(10, 18), sticky="w")

        self.search_button = ctk.CTkButton(
            form,
            text="Search",
            height=56,
            corner_radius=12,
            fg_color=COLORS["sun"],
            hover_color="#d99b2e",
            text_color="#1f2d32",
            font=ctk.CTkFont(size=20, weight="bold"),
            command=self._start_search,
        )
        self.search_button.grid(row=33, column=0, padx=26, pady=(8, 26), sticky="ew")
        self._update_mode_help()

        content = ctk.CTkFrame(body, fg_color="transparent")
        content.grid(row=0, column=1, padx=(14, 28), pady=28, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        self._build_status_panel(content)
        self._build_support_panel(content)

    def _build_status_panel(self, parent):
        status = ctk.CTkFrame(parent, fg_color=COLORS["panel"], border_color=COLORS["line"], border_width=1, corner_radius=14)
        status.grid(row=0, column=0, sticky="ew")
        status.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            status,
            text="Current Activity",
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

        self.log = ctk.CTkTextbox(
            parent,
            height=300,
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
        support.grid(row=2, column=0, sticky="ew")
        support.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            support,
            text="Saved money?",
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=22, pady=(18, 4), sticky="w")
        ctk.CTkLabel(
            support,
            textvariable=self.support_var,
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=13),
            wraplength=520,
        ).grid(row=1, column=0, padx=22, pady=(0, 16), sticky="w")
        ctk.CTkButton(
            support,
            text="Buy me an Estrella",
            width=180,
            height=38,
            fg_color=COLORS["coral"],
            hover_color="#bf574b",
            command=self._open_donation,
        ).grid(row=0, column=1, rowspan=2, padx=22, pady=18, sticky="e")

    def _build_footer(self):
        footer = ctk.CTkFrame(self.root, fg_color=COLORS["sky"], corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        version = self.app_config.get("version", "1.0.0")
        ctk.CTkLabel(
            footer,
            text=f"Canary Car Finder v{version}",
            text_color=COLORS["muted"],
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=0, padx=28, pady=(0, 16), sticky="w")

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

    def _section_label(self, parent, label, row):
        ctk.CTkLabel(
            parent,
            text=label,
            text_color=COLORS["ocean"],
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=row, column=0, padx=26, pady=(12, 8), sticky="w")

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

    def _option(self, parent, label, variable, values, row):
        ctk.CTkLabel(parent, text=label, text_color=COLORS["ink"], font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=row * 2 - 1, column=0, padx=26, pady=(4, 5), sticky="w"
        )
        menu = ctk.CTkOptionMenu(
            parent,
            values=values,
            variable=variable,
            height=42,
            corner_radius=10,
            fg_color=COLORS["ocean"],
            button_color=COLORS["deep_ocean"],
            button_hover_color=COLORS["sun"],
        )
        menu.grid(row=row * 2, column=0, padx=26, pady=(0, 14), sticky="ew")

    def _time_checks(self, parent, label, variables, row):
        ctk.CTkLabel(parent, text=label, text_color=COLORS["ink"], font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=row * 2 - 1, column=0, padx=26, pady=(4, 5), sticky="w"
        )
        frame = ctk.CTkFrame(parent, fg_color="#fbfdfd", border_color=COLORS["line"], border_width=1, corner_radius=10)
        frame.grid(row=row * 2, column=0, padx=26, pady=(0, 14), sticky="ew")
        frame.grid_columnconfigure((0, 1), weight=1)
        for index, (time_value, variable) in enumerate(variables.items()):
            checkbox = ctk.CTkCheckBox(
                frame,
                text=time_value,
                variable=variable,
                onvalue=True,
                offvalue=False,
            )
            checkbox.grid(row=index // 2, column=index % 2, padx=12, pady=8, sticky="w")

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

        self._save_user_settings()
        self.search_running = True
        self.search_button.configure(state="disabled", text="Searching...")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.support_var.set("Search running. I will show the saving once prices are compared.")
        self._set_status("Starting search", "Preparing provider searches", 0, 0)

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
        mode = "single" if self.search_mode_var.get() == SEARCH_MODES[0] else "full"
        if mode == "single":
            min_days = total_days
            max_days = total_days
        else:
            try:
                min_days = int(self.min_days_var.get().strip())
                max_days = int(self.max_days_var.get().strip())
            except ValueError as exc:
                raise ValueError("Trip lengths must be whole numbers.") from exc
            if min_days < 1:
                raise ValueError("Minimum trip length must be at least 1 day.")
            if max_days < min_days:
                raise ValueError("Maximum trip length must be greater than or equal to the minimum.")
            if max_days > total_days:
                raise ValueError("Maximum trip length cannot exceed the full date window.")

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
        search_settings.pickup_times = self._selected_times(self.pickup_time_vars, "pickup")
        search_settings.return_times = self._selected_times(self.return_time_vars, "return")
        search_settings.pickup_time = search_settings.pickup_times[0]
        search_settings.return_time = search_settings.return_times[0]
        search_settings.final_return_time = search_settings.return_times[0]
        return search_settings, mode

    def _run_search(self, search_settings, mode):
        try:
            rows, reports = run_search(search_settings, mode, progress_callback=self._progress)
            self.events.put(("done", rows, reports))
        except Exception as exc:
            self.events.put(("error", exc))

    def _progress(self, completed, total, message):
        self.events.put(("progress", completed, total, message))

    def _process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "progress":
                    _, completed, total, message = event
                    self._set_status("Searching providers", message, completed, total)
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
        self._set_status("Search complete", f"Report ready: {html_path.resolve()}", total, total)
        self._append_log(f"Completed {total} provider searches.")
        self._update_support_message(rows)
        self.search_running = False
        self.search_button.configure(state="normal", text="Search")
        webbrowser.open(html_path.resolve().as_uri())

    def _fail_search(self, exc):
        self._set_status("Search failed", str(exc), 0, 0)
        self._append_log(f"Search failed: {exc}")
        self.support_var.set(
            "If Canary Car Finder helped you find a cheaper hire car, consider buying me an Estrella. "
            "Every donation helps keep the application free and supports future improvements."
        )
        self.search_running = False
        self.search_button.configure(state="normal", text="Search")

    def _set_status(self, title, detail, completed, total):
        self.status_var.set(title)
        self.detail_var.set(detail)
        self.count_var.set(f"{completed} / {total}")
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
                self.support_var.set(f"You saved EUR {saved:.2f} today. Fancy buying me one Estrella?")
                return
        self.support_var.set(
            "If Canary Car Finder helped you find a cheaper hire car, consider buying me an Estrella."
        )

    def _show_about(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("About Canary Car Finder")
        dialog.geometry("520x460")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["sky"])
        dialog.transient(self.root)
        dialog.grab_set()

        panel = ctk.CTkFrame(dialog, fg_color=COLORS["panel"], corner_radius=14)
        panel.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(
            panel,
            text="Canary Car Finder",
            text_color=COLORS["ink"],
            font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(24, 6))
        ctk.CTkLabel(
            panel,
            text=f"Version {self.app_config.get('version', '1.0.0')}",
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

    def _save_user_settings(self):
        data = {
            "pickup_date": self.pickup_date_var.get().strip(),
            "return_date": self.return_date_var.get().strip(),
            "pickup_time": self.pickup_time_var.get(),
            "return_time": self.return_time_var.get(),
            "pickup_times": self._selected_times(self.pickup_time_vars, "pickup"),
            "return_times": self._selected_times(self.return_time_vars, "return"),
            "min_days": self.min_days_var.get().strip(),
            "max_days": self.max_days_var.get().strip(),
            "search_mode": self.search_mode_var.get(),
            "transmission": self.transmission_var.get(),
            "vehicle_seats": self.vehicle_seats_var.get(),
            "vehicle_type": self.vehicle_type_var.get(),
            "visible_browser": self.visible_browser_var.get(),
        }
        USER_SETTINGS_PATH.parent.mkdir(exist_ok=True)
        USER_SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _update_mode_help(self):
        if self.search_mode_var.get() == SEARCH_MODES[0]:
            self.date_help_var.set("Single Search uses these as the exact pickup and return dates.")
            self.length_help_var.set("Trip length fields are saved but ignored in Single Search.")
        else:
            self.date_help_var.set("Holiday Optimiser searches every valid trip inside this date window.")
            self.length_help_var.set("Every trip length between these limits is searched across all providers.")

    def _time_vars(self, name, options, fallback):
        selected = set(self.user_settings.get(name) or [fallback])
        return {time_value: ctk.BooleanVar(value=time_value in selected) for time_value in options}

    def _selected_times(self, variables, label):
        selected = [time_value for time_value, variable in variables.items() if variable.get()]
        if not selected:
            raise ValueError(f"Select at least one {label} time.")
        return selected

def _display_date(value):
    return date.fromisoformat(str(value)).strftime("%d/%m/%Y")


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
