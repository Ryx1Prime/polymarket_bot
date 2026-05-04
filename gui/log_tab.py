import queue
import customtkinter as ctk
from utils.logger import logger_instance

LEVEL_COLORS = {
    "INFO":     "#6ec6e6",
    "WARN":     "#f0c060",
    "ERROR":    "#e07070",
    "CRITICAL": "#ff4444",
}

class LogTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 4))

        ctk.CTkLabel(
            header_frame, text="📋  Лог событий",
            font=ctk.CTkFont(size=16, weight="bold"), anchor="w"
        ).pack(side="left")

        self.clear_btn = ctk.CTkButton(
            header_frame, text="Очистить", width=90, height=28,
            font=ctk.CTkFont(size=12), fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            command=self._clear_logs
        )
        self.clear_btn.pack(side="right")

        self.textbox = ctk.CTkTextbox(
            self, state="disabled", wrap="word",
            font=ctk.CTkFont(family="Courier New", size=12),
            corner_radius=10, border_width=1
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.textbox.tag_config("INFO",     foreground="#6ec6e6")
        self.textbox.tag_config("WARN",     foreground="#f0c060")
        self.textbox.tag_config("ERROR",    foreground="#e07070")
        self.textbox.tag_config("CRITICAL", foreground="#ff4444")
        self.textbox.tag_config("DEFAULT",  foreground="#cccccc")

        self.update_logs()

    def _clear_logs(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")

    def _detect_level(self, msg: str) -> str:
        for level in LEVEL_COLORS:
            if f"[{level}]" in msg:
                return level
        return "DEFAULT"

    def update_logs(self):
        try:
            while True:
                msg = logger_instance.log_queue.get_nowait()
                level = self._detect_level(msg)
                self.textbox.configure(state="normal")
                self.textbox.insert("end", msg + "\n", level)
                self.textbox.see("end")
                self.textbox.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self.update_logs)
