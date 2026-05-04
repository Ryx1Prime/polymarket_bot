import json
import time
import threading
import websocket
from py_clob_client_v2 import ClobClient
from utils.logger import logger_instance

class SignalEngine:
    def __init__(self, clob_client: ClobClient):
        self.client = clob_client
        self.ws_url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
        self.latest_price = None
        self.ws = None
        self.ws_thread = None
        self.active_token = None
        self.last_update = 0

    def start_ws(self, token_id: str):
        self.stop_ws()
        self.active_token = token_id
        self.latest_price = None
        self.last_update = 0

        def on_message(ws, message):
            try:
                data = json.loads(message)
                if isinstance(data, list) and len(data) > 0:
                    event = data[0]
                    if event.get("event_type") == "price_change" and event.get("asset_id") == self.active_token:
                        price = float(event.get("price", 0))
                        if price > 0:
                            self.latest_price = price
                            self.last_update = time.time()
                elif isinstance(data, dict):
                    if data.get("event_type") == "price_change" and data.get("asset_id") == self.active_token:
                        price = float(data.get("price", 0))
                        if price > 0:
                            self.latest_price = price
                            self.last_update = time.time()
            except Exception as e:
                logger_instance.error("SignalEngine", f"Ошибка парсинга WS: {str(e)}")

        def on_error(ws, error):
            logger_instance.warning("SignalEngine", f"WS ошибка: {str(error)}")

        def on_close(ws, close_status_code, close_msg):
            pass

        def on_open(ws):
            sub_msg = {
                "assets_ids": [self.active_token],
                "type": "market"
            }
            ws.send(json.dumps(sub_msg))

        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self.ws_thread.start()

    def stop_ws(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=2)
        self.ws = None
        self.ws_thread = None

    def _get_midpoint_rest(self, token_id: str) -> float:
        try:
            midpoint_resp = self.client.get_midpoint(token_id)
            if isinstance(midpoint_resp, dict):
                return float(midpoint_resp.get("mid", 0))
            return float(midpoint_resp)
        except Exception as e:
            logger_instance.error("SignalEngine", f"REST midpoint ошибка: {str(e)}")
            return 0.0

    def get_signal(self, up_token: str, min_signal: float) -> dict:
        if self.active_token != up_token:
            self.start_ws(up_token)

        up_price = None
        timeout_start = time.time()

        while time.time() - timeout_start < 2:
            if self.latest_price is not None and time.time() - self.last_update < 5:
                up_price = self.latest_price
                break
            time.sleep(0.1)

        if up_price is None:
            logger_instance.warning("SignalEngine", "WS таймаут, переход на REST")
            up_price = self._get_midpoint_rest(up_token)

        if up_price <= 0:
            return {"has_signal": False, "direction": None, "up_price": 0, "confidence": 0}

        down_price = 1.0 - up_price
        up_pct = up_price * 100.0
        down_pct = down_price * 100.0
        confidence = max(up_pct, down_pct)

        if up_pct >= down_pct:
            direction = "UP"
            target_token = up_token
        else:
            direction = "DOWN"
            target_token = up_token

        has_signal = confidence >= min_signal

        logger_instance.info(
            "SignalEngine",
            f"UP={up_pct:.1f}% DOWN={down_pct:.1f}% → {direction} (уверенность {confidence:.1f}%, порог {min_signal}%)"
        )

        return {
            "has_signal": has_signal,
            "direction": direction,
            "up_price": up_price,
            "confidence": confidence
        }

    def get_current_price(self, token_id: str) -> float:
        if self.latest_price is not None and time.time() - self.last_update < 5:
            return self.latest_price
        return self._get_midpoint_rest(token_id)
