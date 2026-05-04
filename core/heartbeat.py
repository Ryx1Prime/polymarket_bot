import time
import threading
from py_clob_client_v2 import ClobClient
from utils.logger import logger_instance

class HeartbeatManager:
    def __init__(self, clob_client: ClobClient):
        self.client = clob_client
        self.heartbeat_id = ""
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while True:
            try:
                resp = self.client.post_heartbeat(self.heartbeat_id)
                if isinstance(resp, dict):
                    if resp.get("error") == "Invalid ID" or "400" in str(resp.get("status", "")):
                        new_id = resp.get("heartbeat_id")
                        if new_id:
                            self.heartbeat_id = new_id
                            logger_instance.info("Heartbeat", f"Updated heartbeat ID: {new_id}")
                    elif resp.get("heartbeat_id"):
                        self.heartbeat_id = resp.get("heartbeat_id")
            except Exception as e:
                error_str = str(e)
                if "400" in error_str or "Invalid ID" in error_str:
                    try:
                        if hasattr(e, 'response') and e.response:
                            data = e.response.json()
                            new_id = data.get("heartbeat_id")
                            if new_id:
                                self.heartbeat_id = new_id
                                logger_instance.info("Heartbeat", f"Updated heartbeat ID from error: {new_id}")
                    except:
                        pass
                else:
                    logger_instance.warning("Heartbeat", f"Heartbeat error: {error_str}")
            time.sleep(5)
