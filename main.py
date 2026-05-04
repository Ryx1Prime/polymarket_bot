from core.config_manager import ConfigManager
from core.auth_manager import AuthManager
from core.market_finder import MarketFinder
from core.signal_engine import SignalEngine
from core.order_executor import OrderExecutor
from core.heartbeat import HeartbeatManager
from core.trading_loop import TradingLoop
from gui.main_window import MainWindow
from utils.logger import logger_instance

class App:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.window = MainWindow(self.config_manager, self.start_bot, self.stop_bot)
        self.trading_loop = None
        self.heartbeat_manager = None
        self.signal_engine = None
        self.auth_manager = None

    def start_bot(self):
        config = self.config_manager.load_config()
        private_key = config.get("private_key", "").strip()
        funder_address = config.get("funder_address", "").strip()

        if not private_key:
            logger_instance.error("Main", "Приватный ключ не задан — перейдите во вкладку «Настройки»")
            self.window.set_bot_error()
            return

        if not funder_address:
            logger_instance.error("Main", "Адрес кошелька не задан — перейдите во вкладку «Настройки»")
            self.window.set_bot_error()
            return

        if not funder_address.startswith("0x") or len(funder_address) != 42:
            logger_instance.error("Main", f"Некорректный адрес кошелька: {funder_address}")
            self.window.set_bot_error()
            return

        if not (len(private_key) == 64 or (private_key.startswith("0x") and len(private_key) == 66)):
            logger_instance.error("Main", "Приватный ключ должен быть 64-символьной hex-строкой (без или с 0x)")
            self.window.set_bot_error()
            return

        try:
            logger_instance.info("Main", "Инициализация подключения к Polygon...")
            self.auth_manager = AuthManager(private_key, funder_address)

            market_finder = MarketFinder()
            self.signal_engine = SignalEngine(self.auth_manager.clob_client)
            order_executor = OrderExecutor(self.auth_manager.clob_client, funder_address)

            usdc_balance = self.auth_manager.get_usdc_balance()
            matic_balance = self.auth_manager.get_matic_balance()
            logger_instance.info("Main", f"Баланс USDC: {usdc_balance:.2f} | Баланс MATIC: {matic_balance:.4f}")

            logger_instance.info("Main", "Проверка апрувов контрактов (Triple Approve)...")
            self.auth_manager.ensure_triple_approve(float(config.get("order_usdc", 10.0)))

            self.heartbeat_manager = HeartbeatManager(self.auth_manager.clob_client)
            self.heartbeat_manager.start()

            self.trading_loop = TradingLoop(
                config, self.auth_manager, market_finder, self.signal_engine, order_executor
            )
            self.trading_loop.start()

            self.window.set_bot_running()
            logger_instance.info("Main", "Бот успешно запущен")

        except Exception as e:
            logger_instance.critical("Main", f"Ошибка запуска: {str(e)}")
            self.window.set_bot_error()

    def stop_bot(self):
        if self.trading_loop:
            self.trading_loop.stop()
        if self.signal_engine:
            self.signal_engine.stop_ws()
        self.trading_loop = None
        self.signal_engine = None
        self.heartbeat_manager = None
        self.window.set_bot_stopped()
        logger_instance.info("Main", "Бот остановлен пользователем")

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = App()
    app.run()
