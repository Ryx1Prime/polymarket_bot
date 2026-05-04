import time
import threading
from utils.logger import logger_instance
from utils.math_helpers import calculate_max_entry_price

class TradingLoop:
    def __init__(self, config, auth_manager, market_finder, signal_engine, order_executor):
        self.config = config
        self.auth_manager = auth_manager
        self.market_finder = market_finder
        self.signal_engine = signal_engine
        self.order_executor = order_executor
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)

    def _sleep_interruptible(self, seconds: float) -> bool:
        start = time.time()
        while time.time() - start < seconds:
            if self.stop_event.is_set():
                return False
            time.sleep(0.5)
        return True

    def _run(self):
        asset = self.config.get("asset", "BTC")
        interval_m = int(self.config.get("interval_m", 5))
        sec_before_close = int(self.config.get("sec_before_close", 10))
        min_signal = float(self.config.get("min_signal", 60.0))
        profit_pct = float(self.config.get("profit_pct", 5.0))
        order_usdc = float(self.config.get("order_usdc", 10.0))
        max_loss_usdc = float(self.config.get("max_loss_usdc", 50.0))

        max_entry = calculate_max_entry_price(profit_pct)
        total_lost = 0.0

        logger_instance.info(
            "TradingLoop",
            f"Запуск: {asset} {interval_m}m | профит={profit_pct}% | макс. вход={max_entry:.4f} | USDC={order_usdc} | стоп-лосс={max_loss_usdc}$"
        )

        while not self.stop_event.is_set():
            try:
                market_info = None
                while not market_info and not self.stop_event.is_set():
                    market_info = self.market_finder.find_market(asset, interval_m)
                    if not market_info:
                        if not self._sleep_interruptible(5):
                            return

                if self.stop_event.is_set():
                    return

                close_time = market_info["close_time"]
                wait_time = close_time - time.time() - sec_before_close

                if wait_time > 0:
                    logger_instance.info("TradingLoop", f"Ожидание {wait_time:.0f}с до окна анализа")
                    if not self._sleep_interruptible(wait_time):
                        return

                signal = self.signal_engine.get_signal(market_info["up_token"], min_signal)

                if not signal["has_signal"]:
                    logger_instance.info("TradingLoop", f"Слабый сигнал ({signal['confidence']:.1f}%), пропуск окна")
                    self._wait_next_window(close_time)
                    continue

                direction = signal["direction"]
                up_price = signal["up_price"]

                if direction == "UP":
                    target_token = market_info["up_token"]
                    entry_price = up_price
                else:
                    target_token = market_info["down_token"]
                    entry_price = 1.0 - up_price

                if entry_price <= 0 or entry_price > max_entry:
                    logger_instance.info(
                        "TradingLoop",
                        f"Нет точки входа: цена {entry_price:.4f} > макс {max_entry:.4f}"
                    )
                    self._wait_next_window(close_time)
                    continue

                logger_instance.info(
                    "TradingLoop",
                    f"ВХОД {direction}: цена={entry_price:.4f} токен={target_token[:12]}..."
                )

                try:
                    self.order_executor.execute_fak_order(
                        token_id=target_token,
                        max_entry_price=max_entry,
                        usdc_amount=order_usdc,
                        tick_size=market_info["tick_size"]
                    )

                except ValueError as ve:
                    if "INVALID_ORDER_NOT_ENOUGH_BALANCE" in str(ve):
                        logger_instance.critical("TradingLoop", "Недостаточно средств — бот остановлен")
                        self.stop_event.set()
                        return

                self._wait_next_window(close_time)

            except Exception as e:
                logger_instance.error("TradingLoop", f"Непредвиденная ошибка: {str(e)}")
                if not self._sleep_interruptible(5):
                    return

    def _wait_next_window(self, close_time: float):
        sleep_to_next = close_time - time.time() + 2
        if sleep_to_next > 0:
            self._sleep_interruptible(sleep_to_next)
