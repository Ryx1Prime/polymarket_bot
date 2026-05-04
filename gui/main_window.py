import customtkinter as ctk
from gui.settings_tab import SettingsTab
from gui.log_tab import LogTab

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

STATUS_IDLE    = ("⏹  Остановлен", "#888888")
STATUS_RUNNING = ("▶  Работает",   "#52c068")
STATUS_ERROR   = ("✖  Ошибка",     "#e05252")

class MainWindow(ctk.CTk):
    def __init__(self, config_manager, start_cmd, stop_cmd):
        super().__init__()
        self.title("PolyBot — Polymarket Scalper")
        self.geometry("720x560")
        self.minsize(640, 480)

        self._build_header()
        self._build_tabs(config_manager)
        self._build_footer(start_cmd, stop_cmd)

    def _build_header(self):
        header = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color=("gray88", "gray13"))
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="🤖  PolyBot",
            font=ctk.CTkFont(size=20, weight="bold"), anchor="w"
        ).pack(side="left", padx=16)

        self.status_badge = ctk.CTkLabel(
            header, text=STATUS_IDLE[0],
            font=ctk.CTkFont(size=12),
            text_color=STATUS_IDLE[1], anchor="e"
        )
        self.status_badge.pack(side="right", padx=16)

    def _build_tabs(self, config_manager):
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=12, pady=(8, 4))

        tab_settings = self.tabview.add("⚙  Настройки")
        tab_logs = self.tabview.add("📋  Логи")

        self.settings_tab = SettingsTab(tab_settings, config_manager)
        self.settings_tab.pack(fill="both", expand=True)

        self.log_tab = LogTab(tab_logs)
        self.log_tab.pack(fill="both", expand=True)

    def _build_footer(self, start_cmd, stop_cmd):
        footer = ctk.CTkFrame(self, height=56, corner_radius=0, fg_color=("gray88", "gray13"))
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        btn_frame = ctk.CTkFrame(footer, fg_color="transparent")
        btn_frame.pack(expand=True, fill="both", padx=16, pady=8)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        self.btn_start = ctk.CTkButton(
            btn_frame, text="▶  Запустить",
            command=start_cmd, height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2d8a4e", hover_color="#246b3d", corner_radius=10
        )
        self.btn_start.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.btn_stop = ctk.CTkButton(
            btn_frame, text="⏹  Остановить",
            command=stop_cmd, height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#8a2d2d", hover_color="#6b2424", corner_radius=10
        )
        self.btn_stop.grid(row=0, column=1, padx=(6, 0), sticky="ew")

    def set_bot_running(self):
        self.status_badge.configure(text=STATUS_RUNNING[0], text_color=STATUS_RUNNING[1])
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")

    def set_bot_stopped(self):
        self.status_badge.configure(text=STATUS_IDLE[0], text_color=STATUS_IDLE[1])
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="normal")

    def set_bot_error(self):
        self.status_badge.configure(text=STATUS_ERROR[0], text_color=STATUS_ERROR[1])
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="normal")
