import customtkinter as ctk
from utils.logger import logger_instance

FIELDS = [
    ("private_key",      "Приватный ключ",             "",      "str",   True),
    ("funder_address",   "Адрес кошелька",             "",      "str",   False),
    ("asset",            "Актив",                      "BTC",   "str",   False),
    ("interval_m",       "Интервал (мин)",             "5",     "int",   False),
    ("order_usdc",       "Размер ордера (USDC)",       "10.0",  "float", False),
    ("profit_pct",       "Целевая прибыль (%)",        "5.0",   "float", False),
    ("sec_before_close", "Секунд до закрытия",         "10",    "int",   False),
    ("min_signal",       "Сила сигнала (%)",           "60.0",  "float", False),
    ("max_loss_usdc",    "Стоп-лосс (USDC)",           "50.0",  "float", False),
]

HINTS = {
    "private_key":      "Hex-ключ MetaMask (64 символа, без 0x)",
    "funder_address":   "Адрес кошелька Polygon (0x...)",
    "asset":            "BTC, ETH или SOL",
    "interval_m":       "5, 15 или 60 минут",
    "order_usdc":       "Сумма USDC за один вход",
    "profit_pct":       "Минимальная целевая доходность",
    "sec_before_close": "За сколько секунд до конца окна анализировать",
    "min_signal":       "Порог уверенности рынка (55–70%)",
    "max_loss_usdc":    "Бот остановится, если суммарный убыток превысит этот лимит",
}

class SettingsTab(ctk.CTkScrollableFrame):
    def __init__(self, master, config_manager):
        super().__init__(master, fg_color="transparent")
        self.config_manager = config_manager
        self.entries = {}
        self.columnconfigure(0, weight=0, minsize=200)
        self.columnconfigure(1, weight=1)

        current_config = self.config_manager.load_config()
        row = 0

        section_auth = ctk.CTkLabel(
            self, text="🔐  Авторизация",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#3a7ebf", "#5dade2"), anchor="w"
        )
        section_auth.grid(row=row, column=0, columnspan=2, padx=16, pady=(14, 8), sticky="w")
        row += 1

        for i, (key, label, default, dtype, is_secret) in enumerate(FIELDS):
            if i == 2:
                sep = ctk.CTkFrame(self, height=1, fg_color=("gray75", "gray30"))
                sep.grid(row=row, column=0, columnspan=2, padx=16, pady=(10, 2), sticky="ew")
                row += 1

                section_trade = ctk.CTkLabel(
                    self, text="📈  Параметры торговли",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=("#3a7ebf", "#5dade2"), anchor="w"
                )
                section_trade.grid(row=row, column=0, columnspan=2, padx=16, pady=(4, 8), sticky="w")
                row += 1

            lbl = ctk.CTkLabel(
                self, text=label,
                font=ctk.CTkFont(size=13), anchor="w", width=180
            )
            lbl.grid(row=row, column=0, padx=(16, 8), pady=6, sticky="w")

            ent = ctk.CTkEntry(
                self,
                placeholder_text=HINTS.get(key, ""),
                show="•" if is_secret else "",
                font=ctk.CTkFont(size=13),
                height=36,
                border_width=1,
                corner_radius=8
            )
            ent.grid(row=row, column=1, padx=(0, 16), pady=6, sticky="ew")

            saved_val = current_config.get(key, default)
            if saved_val:
                ent.insert(0, str(saved_val))

            self.entries[key] = ent
            row += 1

        sep_bottom = ctk.CTkFrame(self, height=1, fg_color=("gray75", "gray30"))
        sep_bottom.grid(row=row, column=0, columnspan=2, padx=16, pady=(12, 4), sticky="ew")
        row += 1

        self.status_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), anchor="w"
        )
        self.status_label.grid(row=row, column=0, columnspan=2, padx=16, pady=(4, 2), sticky="w")
        row += 1

        self.save_btn = ctk.CTkButton(
            self,
            text="💾  Сохранить настройки",
            command=self.save_settings,
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=10
        )
        self.save_btn.grid(row=row, column=0, columnspan=2, padx=16, pady=(6, 16), sticky="ew")

    def save_settings(self):
        new_config = {}
        errors = []

        for key, label, default, dtype, is_secret in FIELDS:
            val = self.entries[key].get().strip()
            if not val:
                val = default
            try:
                if dtype == "int":
                    new_config[key] = int(val) if val else 0
                elif dtype == "float":
                    new_config[key] = float(val) if val else 0.0
                else:
                    new_config[key] = val
            except ValueError:
                errors.append(label)

        if errors:
            self.status_label.configure(
                text=f"⚠  Ошибка в полях: {', '.join(errors)}",
                text_color="#e05252"
            )
            return

        self.config_manager.save_config(new_config)
        self.status_label.configure(text="✔  Настройки сохранены", text_color="#52c068")
        self.after(3000, lambda: self.status_label.configure(text=""))
