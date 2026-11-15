"""USAFE Connect desktop entry point. Network work runs outside Tk's UI thread."""
import atexit
import os
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from connect_core import MODES, TorSession
from connect_help import ADVICE, GUIDE, OUTCOMES, DIFFICULTIES, attempt_record, connection_report, error_code, recovery_method
from web_launch import is_enabled, mark_window, register_launcher, show_existing_window

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
INSTALL_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else ROOT
APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "USAFE/Connect"
VERSION = "0.1.2"
BACKGROUND = "#0a161a"
SURFACE = "#122529"
FIELD = "#0d1d21"
EDGE = "#2a4144"
TEXT = "#eef9f6"
MUTED = "#a9c1c3"
ACCENT = "#86ebc4"

COPY = {
    "en": {
        "tagline": "Browse through Tor bridges", "intro": "Choose a bridge to connect, then open Tor Browser.",
        "route": "Bridge method", "custom": "Custom bridge", "status_title": "Connection status",
        "snowflake_info": "Reach Tor through volunteer proxies.",
        "obfs4_info": "Connect using the obfs4 bridges included with USAFE.",
        "custom_info": "Paste obfs4 or WebTunnel bridge lines from a trusted source.",
        "connect": "Connect", "stop": "Disconnect", "ready": "Ready to connect",
        "connecting": "Connecting", "verifying": "Verifying the route",
        "connected": "Tor connection verified", "error": "Connection needs attention",
        "stopping": "Disconnecting",
        "browser": "Tor Browser", "choose": "Choose browser…", "open": "Open Tor Browser",
        "scope": "This connection serves the Tor Browser opened here.",
        "report": "Save connection summary", "verify": "Recheck connection",
        "report_done": "Connection summary saved. It contains the method, progress and verification result.",
        "browser_waiting": "Available after the connection is verified.",
        "browser_help": "Close any other Tor Browser window before opening this session.",
        "browser_missing": "Choose Browser/firefox.exe from your Tor Browser folder.",
        "website_enable": "Enable website launch", "website_enabled": "Website launch enabled",
        "website_done": "You can now open this window from the Connect section on the USAFE website.",
        "offline": "Disconnected",
        "guide": "Offline connection guide", "close": "Close", "save": "Save this summary",
        "summary": "Your connection summary", "summary_intro": "Preview exactly what you save. Nothing is sent automatically.",
        "feedback": "Optional: how did your task go?", "difficulty": "Where did you need help?",
        "outcomes": ("Skip this question", "I completed my task", "I needed help", "I could not complete my task"),
        "difficulties": ("Skip this question", "No difficulty", "Connecting", "Setting up a bridge", "Opening the browser", "Understanding what is protected"),
        "try_obfs4": "Try obfs4 instead", "try_snowflake": "Try Snowflake instead", "try_custom": "Set up a fresh bridge",
        "elapsed": "Connecting for {seconds}s", "checked": "Last verified {seconds}s ago",
        "steps": "1  Choose a bridge   →   2  Verify access   →   3  Open browser",
        "stage_start": "Starting the bridge connection", "stage_bridge": "Reaching the Tor network",
        "stage_circuit": "Building a route through Tor", "stage_verify": "Checking HTTPS access through Tor",
        "stage_wait": "Some networks take longer. You can disconnect at any time.",
        "local_only": "Local preview · No automatic upload",
        "history": "Connection attempts (up to 10)", "no_attempts": "No completed attempts in this app session.",
        "route_verified": "Route currently verified", "yes": "Yes", "no": "No",
        "verified": "Verified", "failed": "Could not connect", "cancelled": "Stopped by you",
    },
    "tr": {
        "tagline": "Tor köprüsüyle internete bağlan", "intro": "Bir köprü seçip bağlan, ardından Tor Browser’ı aç.",
        "route": "Köprü yöntemi", "custom": "Özel köprü", "status_title": "Bağlantı durumu",
        "snowflake_info": "Gönüllü proxy’ler üzerinden Tor’a ulaş.",
        "obfs4_info": "USAFE ile gelen obfs4 köprülerinden bağlan.",
        "custom_info": "Güvendiğin bir kaynaktan aldığın obfs4 veya WebTunnel satırlarını yapıştır.",
        "connect": "Bağlan", "stop": "Bağlantıyı kes", "ready": "Bağlanmaya hazır",
        "connecting": "Bağlanıyor", "verifying": "Bağlantı doğrulanıyor",
        "connected": "Tor bağlantısı doğrulandı", "error": "Bağlantı kurulamadı",
        "stopping": "Bağlantı kesiliyor",
        "browser": "Tor Browser", "choose": "Tarayıcı seç…", "open": "Tor Browser’ı aç",
        "scope": "Bu bağlantı, bu pencereden açtığın Tor Browser için geçerli.",
        "report": "Bağlantı özetini kaydet", "verify": "Bağlantıyı tekrar doğrula",
        "report_done": "Özet kaydedildi. Yöntem, ilerleme ve doğrulama sonucunu içerir.",
        "browser_waiting": "Bağlantı doğrulanınca açabilirsin.",
        "browser_help": "Bu oturumu açmadan önce diğer Tor Browser pencerelerini kapat.",
        "browser_missing": "Tor Browser klasörünün içinden Browser/firefox.exe dosyasını seç.",
        "website_enable": "Siteden açmayı etkinleştir", "website_enabled": "Siteden açma etkin",
        "website_done": "Bu pencereyi artık USAFE sitesindeki Connect bölümünden açabilirsin.",
        "offline": "Bağlantı kesildi",
        "guide": "Çevrimdışı bağlantı rehberi", "close": "Kapat", "save": "Bu özeti kaydet",
        "summary": "Bağlantı özetin", "summary_intro": "Kaydedeceğin bilgileri önceden gör. Hiçbir şey otomatik gönderilmez.",
        "feedback": "İsteğe bağlı: işini tamamlayabildin mi?", "difficulty": "Nerede yardıma ihtiyaç duydun?",
        "outcomes": ("Soruyu atla", "İşimi tamamladım", "Yardıma ihtiyaç duydum", "İşimi tamamlayamadım"),
        "difficulties": ("Soruyu atla", "Zorluk yaşamadım", "Bağlantı kurma", "Köprü ayarlama", "Tarayıcı açma", "Bağlantı kapsamını anlama"),
        "try_obfs4": "obfs4 ile dene", "try_snowflake": "Snowflake ile dene", "try_custom": "Yeni köprü ayarla",
        "elapsed": "Bağlantı süresi: {seconds} sn", "checked": "Son doğrulama: {seconds} sn önce",
        "steps": "1  Köprü seç   →   2  Erişimi doğrula   →   3  Tarayıcıyı aç",
        "stage_start": "Köprü bağlantısı başlatılıyor", "stage_bridge": "Tor ağına ulaşılıyor",
        "stage_circuit": "Tor üzerinden bağlantı yolu kuruluyor", "stage_verify": "Tor üzerinden HTTPS erişimi kontrol ediliyor",
        "stage_wait": "Bazı ağlarda daha uzun sürebilir. İstediğin zaman bağlantıyı kesebilirsin.",
        "local_only": "Yerel önizleme · Otomatik gönderim yok",
        "history": "Bağlantı denemeleri (en fazla 10)", "no_attempts": "Bu uygulama oturumunda tamamlanmış deneme yok.",
        "route_verified": "Bağlantı şu anda doğrulanmış", "yes": "Evet", "no": "Hayır",
        "verified": "Doğrulandı", "failed": "Bağlanamadı", "cancelled": "Sen durdurdun",
    },
}


class App:
    def __init__(self, root):
        self.root = root
        self.events = queue.Queue()
        self.session = TorSession(ROOT / "runtime", APP_DIR)
        self.language = tk.StringVar(value="en")
        self.mode = tk.StringVar(value=MODES[0])
        self.browser_path = tk.StringVar()
        bundled_browser = INSTALL_DIR / "Tor Browser/Browser/firefox.exe"
        if bundled_browser.is_file():
            self.browser_path.set(str(bundled_browser))
        self.jobs = 0
        self.closing = False
        self.user_stopped = False
        self.current_state = "ready"
        self.progress = 0
        self.issue = None
        self.attempt_started = None
        self.attempt_mode = None
        self.checked_at = None
        self.attempts = []
        self.labels = []
        self.stacked = None
        self.launcher_enabled = getattr(sys, "frozen", False) and is_enabled(Path(sys.executable))
        atexit.register(lambda: self.session.stop())
        root.title("USAFE Connect")
        root.geometry(f"{min(960, root.winfo_screenwidth() - 64)}x{min(700, root.winfo_screenheight() - 100)}")
        root.minsize(560, 460)
        root.configure(bg=BACKGROUND)
        if (ROOT / "assets/usafe.ico").is_file():
            root.iconbitmap(str(ROOT / "assets/usafe.ico"))
        root.protocol("WM_DELETE_WINDOW", self.close)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", padding=7, arrowsize=14, background=SURFACE, bordercolor=EDGE, arrowcolor=TEXT)
        style.map("TCombobox", fieldbackground=[("readonly", SURFACE)], foreground=[("readonly", TEXT)],
                  selectbackground=[("readonly", SURFACE)], selectforeground=[("readonly", TEXT)])
        style.configure("Vertical.TScrollbar", troughcolor=BACKGROUND, background=EDGE, arrowsize=10)
        root.option_add("*TCombobox*Listbox.background", FIELD)
        root.option_add("*TCombobox*Listbox.foreground", TEXT)
        root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        root.option_add("*TCombobox*Listbox.selectForeground", BACKGROUND)
        canvas = tk.Canvas(root, bg=BACKGROUND, highlightthickness=0)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        main = tk.Frame(canvas, bg=BACKGROUND, padx=32, pady=26)
        content = canvas.create_window((0, 0), window=main, anchor="nw")
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(content, width=event.width))
        main.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        root.bind("<MouseWheel>", lambda event: canvas.yview_scroll(-int(event.delta / 120), "units")
                  if event.widget.winfo_class() not in ("Text", "TCombobox") else None)
        header = tk.Frame(main, bg=BACKGROUND)
        header.pack(fill="x")
        if (ROOT / "assets/usafe.png").is_file():
            self.logo = tk.PhotoImage(file=str(ROOT / "assets/usafe.png")).subsample(8, 8)
            tk.Label(header, image=self.logo, bg=BACKGROUND, bd=0).pack(side="left", padx=(0, 8))
        tk.Label(header, text="USAFE Connect", bg=BACKGROUND, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(side="left")
        lang = ttk.Combobox(header, values=("English", "Türkçe"), state="readonly", width=10, font=("Segoe UI", 10))
        lang.current(0)
        lang.pack(side="right")
        lang.bind("<<ComboboxSelected>>", lambda _: self.select_language(lang.current()))
        self.label(main, "tagline", size=24, bold=True, pady=(14, 4))
        self.label(main, "intro", size=11, color=MUTED, pady=(0, 10))
        self.label(main, "steps", size=10, color=ACCENT, pady=(0, 12))

        self.panels = tk.Frame(main, bg=BACKGROUND)
        self.panels.pack(fill="x")
        self.bridge_card = self.card(self.panels)
        self.status_card = self.card(self.panels)
        self.panels.bind("<Configure>", lambda event: self.arrange_panels(event.width))
        self.label(self.bridge_card, "route", size=13, bold=True, pady=(0, 12))
        methods = tk.Frame(self.bridge_card, bg=SURFACE)
        methods.pack(fill="x")
        self.methods = []
        for index, mode in enumerate(MODES):
            methods.columnconfigure(index, weight=1)
            option = tk.Radiobutton(methods, text=mode if mode == "obfs4" else mode.title(), value=mode,
                                    variable=self.mode, command=self.bridge_state, indicatoron=False,
                                    bg=FIELD, fg=TEXT, selectcolor=EDGE, activebackground=EDGE,
                                    activeforeground=TEXT, disabledforeground=MUTED, borderwidth=0,
                                    relief="flat", offrelief="flat", highlightthickness=1,
                                    highlightbackground=EDGE, highlightcolor=ACCENT, pady=8,
                                    font=("Segoe UI", 10, "bold"), cursor="hand2")
            option.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 6, 0))
            self.methods.append(option)
        self.method_info = self.label(self.bridge_card, None, color=MUTED, size=10, pady=(10, 12))
        self.bridge_fields = tk.Frame(self.bridge_card, bg=SURFACE)
        self.bridges = tk.Text(self.bridge_fields, height=3, width=1, wrap="word", bg=FIELD, fg=TEXT, insertbackground=TEXT,
                               relief="flat", highlightthickness=1, highlightbackground=EDGE,
                               highlightcolor=ACCENT, padx=9, pady=7, font=("Segoe UI", 10), undo=False)
        self.bridges.pack(fill="x", pady=(0, 12))
        self.bridge_actions = tk.Frame(self.bridge_card, bg=SURFACE)
        self.bridge_actions.pack(fill="x", pady=(3, 0))
        self.connect_button = self.button(self.bridge_actions, "connect", self.connect, primary=True)
        self.connect_button.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.stop_button = self.button(self.bridge_actions, "stop", self.stop)
        self.stop_button.pack(side="left", fill="x", expand=True)

        self.label(self.status_card, "status_title", size=13, bold=True, pady=(0, 10))
        status_row = tk.Frame(self.status_card, bg=SURFACE)
        status_row.pack(fill="x", pady=(0, 10))
        self.ring = tk.Canvas(status_row, bg=SURFACE, width=82, height=82, highlightthickness=0)
        self.ring.pack(side="left", padx=(0, 16))
        status_copy = tk.Frame(status_row, bg=SURFACE)
        status_copy.pack(side="left", fill="x", expand=True)
        self.status = self.label(status_copy, None, size=14, bold=True)
        self.detail = self.label(self.status_card, None, size=10, color=MUTED)
        self.detail.pack_forget()
        self.timing = self.label(self.status_card, None, size=10, color=MUTED, pady=(0, 8))
        self.check_button = self.button(self.status_card, "verify", self.recheck)
        self.check_button.pack(fill="x")
        self.recovery_button = self.button(self.status_card, "try_obfs4", self.recover, primary=True)

        browser = self.card(main)
        browser.pack(fill="x", pady=(14, 0))
        self.label(browser, "browser", size=13, bold=True, pady=(0, 4))
        self.browser_help = self.label(browser, None, size=10, color=MUTED, pady=(0, 12))
        actions = tk.Frame(browser, bg=SURFACE)
        actions.pack(fill="x")
        self.open_button = self.button(actions, "open", self.open_browser, primary=True)
        self.open_button.pack(side="left", padx=(0, 8))
        self.button(actions, "choose", self.choose_browser).pack(side="left")

        self.label(main, "scope", size=10, color=MUTED, pady=(16, 7))
        footer = tk.Frame(main, bg=BACKGROUND)
        footer.pack(fill="x")
        self.report_button = self.button(footer, "report", self.export_summary)
        self.guide_button = self.button(footer, "guide", self.show_guide)
        def arrange_footer(event):
            stacked = event.width < 650
            self.report_button.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 7))
            self.guide_button.grid(row=1 if stacked else 0, column=0 if stacked else 1, sticky="w", pady=(0, 7))
        footer.bind("<Configure>", arrange_footer)
        if getattr(sys, "frozen", False):
            self.launcher_button = self.button(footer, "website_enable", self.enable_website_launch)
            self.launcher_button.grid(row=2, column=0, columnspan=2, sticky="w")
        tk.Label(footer, text="USAFE Connect  " + VERSION, fg=MUTED, bg=BACKGROUND,
                 font=("Segoe UI", 9)).grid(row=3, column=0, columnspan=2, sticky="e")
        self.translate()
        self.refresh_controls()
        self.root.after(150, self.poll)
        self.root.after(1000, self.tick)

    @property
    def busy(self):
        return self.jobs > 0

    def active(self):
        process = self.session.process
        return process is not None and process.poll() is None

    @staticmethod
    def wrap_label(event):
        width = max(1, event.width - 4)
        if int(event.widget["wraplength"]) != width:
            event.widget.configure(wraplength=width)

    @staticmethod
    def card(parent):
        return tk.Frame(parent, bg=SURFACE, padx=19, pady=17, highlightbackground=EDGE, highlightthickness=1)

    def arrange_panels(self, width):
        stacked = width < 680
        if stacked == self.stacked:
            return
        self.stacked = stacked
        self.panels.columnconfigure(0, weight=3, uniform="panel" if not stacked else "")
        self.panels.columnconfigure(1, weight=2 if not stacked else 0, uniform="panel" if not stacked else "")
        self.bridge_card.grid(row=0, column=0, sticky="nsew", padx=(0, 0 if stacked else 7))
        self.status_card.grid(row=1 if stacked else 0, column=0 if stacked else 1,
                              sticky="nsew", padx=(0 if stacked else 7, 0), pady=(14 if stacked else 0, 0))

    def label(self, parent, key, size=11, bold=False, pady=0, color=TEXT):
        widget = tk.Label(parent, bg=parent["bg"], fg=color, anchor="w", justify="left", width=1,
                          font=("Segoe UI", size, "bold" if bold else "normal"))
        widget.pack(fill="x", pady=pady)
        widget.bind("<Configure>", self.wrap_label)
        if key:
            self.labels.append((widget, key))
        return widget

    def button(self, parent, key, command, primary=False):
        widget = tk.Button(parent, command=command, activeforeground=BACKGROUND if primary else TEXT,
                           activebackground="#aaf8da" if primary else EDGE, disabledforeground=MUTED,
                           relief="flat", borderwidth=0, highlightthickness=1, highlightbackground=EDGE,
                           highlightcolor=ACCENT, padx=13, pady=9, font=("Segoe UI", 10, "bold"), cursor="hand2")
        widget.primary = primary
        self.button_state(widget, True)
        self.labels.append((widget, key))
        return widget

    @staticmethod
    def button_state(widget, enabled):
        widget.configure(state="normal" if enabled else "disabled", bg=ACCENT if enabled and widget.primary else FIELD,
                         fg=BACKGROUND if widget.primary else TEXT)

    def select_language(self, index):
        self.language.set(("en", "tr")[index])
        self.translate()

    def translate(self):
        words = COPY[self.language.get()]
        for widget, key in self.labels:
            widget.configure(text=words[key])
        self.methods[-1].configure(text=words["custom"])
        self.bridge_state()
        if hasattr(self, "launcher_button") and self.launcher_enabled:
            self.launcher_button.configure(text=words["website_enabled"])
        browser_hint = "browser_missing" if not self.browser_path.get() else (
            "browser_help" if self.current_state == "connected" else "browser_waiting"
        )
        self.browser_help.configure(text=words[browser_hint])
        self.render_status()
        self.render_guidance()

    def render_guidance(self):
        words = COPY[self.language.get()]
        if self.current_state == "error":
            advice = ADVICE.get(self.issue, ADVICE["unknown"])
            self.set_detail(getattr(advice, self.language.get()))
        elif self.current_state in ("connecting", "verifying"):
            stage = "stage_verify" if self.current_state == "verifying" else (
                "stage_circuit" if self.progress >= 80 else "stage_bridge" if self.progress >= 10 else "stage_start")
            hint = words[stage]
            if self.attempt_started is not None and time.monotonic() - self.attempt_started > 30:
                hint += "\n" + words["stage_wait"]
            self.set_detail(hint)
        else:
            self.set_detail()
        next_mode = recovery_method(self.issue, self.mode.get()) if self.current_state == "error" else None
        if next_mode:
            self.recovery_button.configure(text=words["try_" + next_mode])
            self.recovery_button.pack(fill="x", pady=(8, 0))
            self.button_state(self.recovery_button, not self.busy)
        else:
            self.recovery_button.pack_forget()
        if self.current_state == "connected" and self.checked_at is not None:
            text = words["checked"].format(seconds=int(time.monotonic() - self.checked_at))
        elif self.current_state in ("connecting", "verifying") and self.attempt_started is not None:
            text = words["elapsed"].format(seconds=int(time.monotonic() - self.attempt_started))
        else:
            text = ""
        self.timing.configure(text=text)

    def tick(self):
        self.render_guidance()
        self.root.after(1000, self.tick)

    def finish_attempt(self, outcome, code=None):
        if self.attempt_started is not None:
            self.attempts.append(attempt_record(self.attempt_mode, outcome, self.progress,
                                               time.monotonic() - self.attempt_started, code))
            self.attempts = self.attempts[-10:]
            self.attempt_started = None

    def recover(self):
        next_mode = recovery_method(self.issue, self.mode.get())
        if self.busy or not next_mode:
            return
        # A failed verification may leave Tor running. Finish teardown first.
        # The next attempt starts only after all old worker events are drained.
        self.pending_method = next_mode
        self.stop()

    def render_status(self):
        state = self.current_state
        color = "#ffc899" if state == "error" else ACCENT if state in ("connecting", "verifying", "connected") else MUTED
        self.status.configure(text=COPY[self.language.get()][state], fg=color)
        self.ring.delete("all")
        self.ring.create_oval(7, 7, 75, 75, fill=FIELD, outline=EDGE, width=5)
        if state == "connected":
            self.ring.create_oval(7, 7, 75, 75, outline=color, width=5)
            self.ring.create_line(27, 41, 37, 51, 56, 31, fill=color, width=4, capstyle="round", joinstyle="round")
        else:
            if state in ("connecting", "verifying") and self.progress:
                self.ring.create_arc(7, 7, 75, 75, style="arc", start=90, extent=-min(359.9, self.progress * 3.6),
                                     outline=color, width=5)
            mark = f"{self.progress}%" if state in ("connecting", "verifying") else "!" if state == "error" else "–"
            self.ring.create_text(41, 41, text=mark, fill=color, font=("Segoe UI", 13, "bold"))

    def set_detail(self, text=""):
        if text:
            self.detail.configure(text=text)
            self.detail.pack(fill="x", before=self.check_button, pady=(0, 10))
        else:
            self.detail.pack_forget()

    def bridge_state(self):
        mode = self.mode.get()
        self.method_info.configure(text=COPY[self.language.get()][mode + "_info"])
        if mode == "custom":
            self.bridge_fields.pack(fill="x", before=self.bridge_actions)
            self.bridges.configure(state="disabled" if self.busy or self.active() else "normal")
        else:
            self.bridge_fields.pack_forget()

    def refresh_controls(self):
        active = self.active()
        blocked = self.busy or active
        for option in self.methods:
            option.configure(state="disabled" if blocked else "normal")
        self.button_state(self.connect_button, not blocked)
        self.button_state(self.stop_button, blocked and not self.user_stopped)
        self.button_state(self.check_button, active and not self.busy)
        browser_ready = active and self.session.verified and self.browser_path.get() and not self.busy
        self.button_state(self.open_button, browser_ready)
        if hasattr(self, "launcher_button"):
            self.button_state(self.launcher_button, not self.launcher_enabled)
        self.bridge_state()

    def worker(self, action, stopping=False):
        self.jobs += 1
        def run():
            try:
                action()
            except Exception as error:
                self.events.put({"state": "error", "code": error_code(error), "stopping": stopping})
            finally:
                self.events.put({"done": True})
        threading.Thread(target=run, daemon=True).start()

    def connect(self):
        if self.busy or self.active():
            return
        # A terminated child can still own the profile lock until cleanup.
        if self.session.process is not None or self.session.instance_lock is not None:
            self.session.stop()
        self.user_stopped = False
        self.session = TorSession(ROOT / "runtime", APP_DIR)
        mode = self.mode.get()
        self.issue = None
        self.checked_at = None
        self.attempt_mode = mode
        self.attempt_started = time.monotonic()
        bridges = self.bridges.get("1.0", "end")
        self.set_detail()
        self.current_state = "connecting"
        self.progress = 0
        self.translate()
        self.worker(lambda: self.session.start(mode, bridges, notify=self.events.put))
        self.refresh_controls()

    def stop(self):
        if self.user_stopped and self.busy:
            return
        self.user_stopped = True
        self.finish_attempt("cancelled", "cancelled")
        self.checked_at = None
        self.session.cancelled.set()
        self.current_state = "stopping"
        self.set_detail()
        self.translate()
        self.worker(self.session.stop, stopping=True)
        self.refresh_controls()

    def recheck(self):
        if self.busy or not self.active():
            return
        self.checked_at = None
        self.current_state = "verifying"
        self.set_detail()
        self.translate()
        def check():
            self.session.check_connection()
            self.events.put({"state": "connected", "progress": 100})
        self.worker(check)
        self.refresh_controls()

    def choose_browser(self):
        path = filedialog.askopenfilename(title=COPY[self.language.get()]["choose"], filetypes=[("Tor Browser", "firefox.exe")])
        if path:
            self.browser_path.set(path)
            self.translate()
            self.refresh_controls()

    def enable_website_launch(self):
        try:
            register_launcher(Path(sys.executable))
        except OSError as error:
            messagebox.showerror("USAFE Connect", str(error), parent=self.root)
        else:
            self.launcher_enabled = True
            self.translate()
            self.refresh_controls()
            messagebox.showinfo("USAFE Connect", COPY[self.language.get()]["website_done"], parent=self.root)

    def open_browser(self):
        try:
            self.session.launch_browser(Path(self.browser_path.get()))
        except Exception as error:
            messagebox.showerror("USAFE Connect", str(error))

    def dialog(self, title):
        window = tk.Toplevel(self.root)
        window.title(title)
        window.configure(bg=BACKGROUND, padx=20, pady=20)
        width = min(700, self.root.winfo_screenwidth() - 60)
        height = min(650, self.root.winfo_screenheight() - 100)
        x = max(0, self.root.winfo_rootx() + (self.root.winfo_width() - width) // 2)
        y = max(0, self.root.winfo_rooty() + (self.root.winfo_height() - height) // 2)
        window.geometry(f"{width}x{height}+{x}+{y}")
        if (ROOT / "assets/usafe.ico").is_file():
            window.iconbitmap(str(ROOT / "assets/usafe.ico"))
        window.minsize(480, 400)
        window.transient(self.root)
        window.bind("<Escape>", lambda _: window.destroy())
        return window

    def show_guide(self):
        words = COPY[self.language.get()]
        window = self.dialog(words["guide"])
        selector = ttk.Combobox(window, values=[title for title, _ in GUIDE[self.language.get()]], state="readonly",
                                font=("Segoe UI", 11))
        selector.pack(fill="x", pady=(0, 14))
        selector.current(0)
        area = tk.Frame(window, bg=SURFACE)
        area.pack(fill="both", expand=True)
        body = tk.Text(area, wrap="word", bg=SURFACE, fg=TEXT, font=("Segoe UI", 12),
                       padx=18, pady=18, relief="flat", width=1, height=8)
        scrollbar = ttk.Scrollbar(area, command=body.yview)
        scrollbar.pack(side="right", fill="y")
        body.configure(yscrollcommand=scrollbar.set)
        body.pack(side="left", fill="both", expand=True)
        # Freeze the dialog language. Main-window translation cannot leave half a
        # dialog in another language or retain destroyed widgets in self.labels.
        entries = GUIDE[self.language.get()]
        def select(_=None):
            body.configure(state="normal")
            body.delete("1.0", "end")
            body.insert("1.0", entries[selector.current()][1])
            body.configure(state="disabled")
            body.yview_moveto(0)
        selector.bind("<<ComboboxSelected>>", select)
        select()
        tk.Button(window, text=words["close"], command=window.destroy, bg=ACCENT, fg=BACKGROUND,
                  relief="flat", padx=20, pady=8, font=("Segoe UI", 10, "bold")).pack(anchor="e", pady=(14, 0))

    def export_summary(self):
        language = self.language.get()
        words = COPY[language]
        window = self.dialog(words["summary"])
        tk.Label(window, text=words["summary_intro"], fg=TEXT, bg=BACKGROUND,
                 wraplength=430, justify="left", font=("Segoe UI", 11)).pack(anchor="w", pady=(0, 12))
        choices = []
        for label, values in (("feedback", "outcomes"), ("difficulty", "difficulties")):
            tk.Label(window, text=words[label], fg=MUTED, bg=BACKGROUND, font=("Segoe UI", 10)).pack(anchor="w")
            choice = ttk.Combobox(window, values=words[values], state="readonly", font=("Segoe UI", 10))
            choice.current(0)
            choice.pack(fill="x", pady=(4, 10))
            choices.append(choice)
        area = tk.Frame(window, bg=FIELD)
        area.pack(fill="both", expand=True)
        body = tk.Text(area, wrap="word", bg=FIELD, fg=TEXT, font=("Segoe UI", 11),
                       padx=12, pady=12, relief="flat", width=1, height=8)
        scrollbar = ttk.Scrollbar(area, command=body.yview)
        scrollbar.pack(side="right", fill="y")
        body.configure(yscrollcommand=scrollbar.set)
        body.pack(side="left", fill="both", expand=True)
        # Snapshot now, so the saved document is exactly the displayed preview.
        attempts = list(self.attempts)
        verified, state = self.session.verified and self.active(), self.current_state
        def preview(_=None):
            report = connection_report(VERSION, attempts, verified, state,
                                       OUTCOMES[choices[0].current()], DIFFICULTIES[choices[1].current()])
            body.configure(state="normal")
            body.delete("1.0", "end")
            lines = [f"USAFE Connect {report['version']} · Windows", words["scope"], "",
                     words["status_title"] + ": " + words.get(report["state"], report["state"]),
                     words["route_verified"] + ": " + words["yes" if report["current_route_verified"] else "no"],
                     "", words["history"]]
            for index, attempt in enumerate(report["attempts"], 1):
                method = words["custom"] if attempt["transport"] == "custom" else attempt["transport"]
                lines.append(f"{index}. {method} · {words[attempt['outcome']]} · {attempt['bootstrap_percent']}% · ~{attempt['elapsed_seconds_rounded']}s")
                if attempt["issue"]:
                    lines.append(getattr(ADVICE[attempt["issue"]], language))
            if not report["attempts"]:
                lines.append(words["no_attempts"])
            lines.extend(["", words["feedback"], words["outcomes"][choices[0].current()], "",
                          words["difficulty"], words["difficulties"][choices[1].current()]])
            body.insert("1.0", "\n".join(lines))
            body.configure(state="disabled")
        for choice in choices:
            choice.bind("<<ComboboxSelected>>", preview)
        preview()
        def save():
            path = filedialog.asksaveasfilename(parent=window, defaultextension=".txt",
                                               initialfile="usafe-connection-summary.txt", filetypes=[("Text", "*.txt")])
            if path:
                try:
                    Path(path).write_text(body.get("1.0", "end-1c") + "\n", encoding="utf-8")
                except OSError as error:
                    messagebox.showerror("USAFE Connect", str(error), parent=window)
                else:
                    messagebox.showinfo("USAFE Connect", words["report_done"], parent=window)
        tk.Label(window, text=words["local_only"], bg=BACKGROUND, fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=10)
        tk.Button(window, text=words["save"], command=save, bg=ACCENT, fg=BACKGROUND,
                  relief="flat", padx=20, pady=8, font=("Segoe UI", 10, "bold")).pack(anchor="e")

    def poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event.get("done"):
                    self.jobs -= 1
                    if not self.busy and self.current_state == "stopping":
                        self.current_state = "offline"
                        self.progress = 0
                        self.set_detail()
                    self.refresh_controls()
                elif not self.user_stopped or event.get("stopping"):
                    self.current_state = event["state"]
                    self.progress = event.get("progress", self.progress)
                    if self.current_state == "error":
                        self.issue = event.get("code", "unknown")
                        self.checked_at = None
                        self.finish_attempt("failed", self.issue)
                    elif self.current_state == "connected":
                        self.checked_at = time.monotonic()
                        self.issue = None
                        self.finish_attempt("verified")
                self.translate()
        except queue.Empty:
            pass
        if not self.busy and self.session.process is not None and not self.active() and self.current_state != "error":
            self.session.verified = False
            self.current_state = "error"
            self.issue = "tor_stopped"
            self.checked_at = None
            self.translate()
            self.refresh_controls()
        if not self.busy and getattr(self, "pending_method", None) and not self.closing:
            mode = self.pending_method
            self.pending_method = None
            self.mode.set(mode)
            self.issue = None
            self.current_state = "ready"
            self.translate()
            self.refresh_controls()
            if mode != "custom":
                self.connect()
            else:
                self.bridges.focus_set()
        if self.closing and not self.busy and self.session.process is None:
            self.root.destroy()
        else:
            self.root.after(150, self.poll)

    def close(self):
        self.closing = True
        self.pending_method = None
        self.stop()


if __name__ == "__main__":
    if sys.argv[1:2] == ["--from-website"] and show_existing_window(Path(sys.executable)):
        raise SystemExit(0)
    root = tk.Tk()
    if getattr(sys, "frozen", False) and sys.platform == "win32":
        # All native Python/Tk dependencies are now loaded. External Tor, curl and
        # Tor Browser must inherit Windows' normal DLL search path.
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    App(root)
    if getattr(sys, "frozen", False):
        root.after_idle(lambda: mark_window(root.winfo_id(), Path(sys.executable)))
    root.mainloop()
