"""USAFE Connect desktop entry point. Network work runs outside Tk's UI thread."""
import atexit
import json
import os
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from connect_core import MODES, TorSession
from web_launch import is_enabled, mark_window, register_launcher, show_existing_window

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
INSTALL_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else ROOT
APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "USAFE/Connect"
VERSION = "0.1.1"
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
        self.label(main, "tagline", size=28, bold=True, pady=(22, 4))
        self.label(main, "intro", size=11, color=MUTED, pady=(0, 22))

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
        self.check_button = self.button(self.status_card, "verify", self.recheck)
        self.check_button.pack(fill="x")

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
        self.button(footer, "report", self.export_summary).pack(side="left", padx=(0, 8))
        if getattr(sys, "frozen", False):
            self.launcher_button = self.button(footer, "website_enable", self.enable_website_launch)
            self.launcher_button.pack(side="left")
        self.translate()
        self.refresh_controls()
        self.root.after(150, self.poll)

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
                self.events.put({"state": "error", "message": str(error), "stopping": stopping})
            finally:
                self.events.put({"done": True})
        threading.Thread(target=run, daemon=True).start()

    def connect(self):
        if self.busy or self.active():
            return
        self.user_stopped = False
        self.session = TorSession(ROOT / "runtime", APP_DIR)
        mode = self.mode.get()
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
        self.session.cancelled.set()
        self.current_state = "stopping"
        self.set_detail()
        self.translate()
        self.worker(self.session.stop, stopping=True)
        self.refresh_controls()

    def recheck(self):
        if self.busy:
            return
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

    def export_summary(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile="usafe-connection-summary.json", filetypes=[("JSON", "*.json")])
        if path:
            report = {"app": "USAFE Connect", "version": VERSION, "platform": "Windows", "transport": self.session.mode,
                      "bootstrap_percent": self.session.progress, "tor_https_verified": self.session.verified,
                      "scope": "USAFE-managed Tor session"}
            try:
                Path(path).write_text(json.dumps(report, indent=2), encoding="utf-8")
            except OSError as error:
                messagebox.showerror("USAFE Connect", str(error))
            else:
                messagebox.showinfo("USAFE Connect", COPY[self.language.get()]["report_done"])

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
                    if event.get("message"):
                        self.set_detail(event["message"])
                self.translate()
        except queue.Empty:
            pass
        if not self.busy and self.session.process is not None and not self.active():
            self.stop()
        if self.closing and not self.busy and self.session.process is None:
            self.root.destroy()
        else:
            self.root.after(150, self.poll)

    def close(self):
        self.closing = True
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
