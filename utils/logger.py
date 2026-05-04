import queue
import datetime

class BotLogger:
    def __init__(self):
        self.log_queue = queue.Queue()

    def _format_msg(self, level: str, module: str, message: str) -> str:
        now = datetime.datetime.now().strftime("%H:%M:%S")
        return f"[{now}] [{level}] [{module}] {message}"

    def info(self, module: str, message: str):
        self.log_queue.put(self._format_msg("INFO", module, message))

    def warning(self, module: str, message: str):
        self.log_queue.put(self._format_msg("WARN", module, message))

    def error(self, module: str, message: str):
        self.log_queue.put(self._format_msg("ERROR", module, message))

    def critical(self, module: str, message: str):
        self.log_queue.put(self._format_msg("CRITICAL", module, message))

logger_instance = BotLogger()
