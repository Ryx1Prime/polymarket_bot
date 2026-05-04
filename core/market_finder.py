import time
import json
import requests
from utils.logger import logger_instance

class MarketFinder:
    def __init__(self):
        self.session = requests.Session()
        self.api_url = "https://gamma-api.polymarket.com/markets"

    def get_window_ts(self, interval_m: int) -> int:
        current = int(time.time())
        return current - (current % (interval_m * 60))

    def build_slug(self, asset: str, interval_m: int) -> str:
        window_ts = self.get_window_ts(interval_m)
        return f"{asset.lower()}-updown-{interval_m}m-{window_ts}"

    def find_market(self, asset: str, interval_m: int):
        window_ts = self.get_window_ts(interval_m)
        slug = self.build_slug(asset, interval_m)
        close_time = window_ts + (interval_m * 60)

        logger_instance.info("MarketFinder", f"Поиск рынка: {slug}")

        for attempt in range(3):
            try:
                response = self.session.get(self.api_url, params={"slug": slug}, timeout=10)
                response.raise_for_status()
                data = response.json()

                if not data:
                    logger_instance.warning("MarketFinder", f"Рынок не найден: {slug}")
                    return None

                market = data[0] if isinstance(data, list) else data

                if not market.get("active", False):
                    logger_instance.warning("MarketFinder", f"Рынок неактивен: {slug}")
                    return None

                condition_id = market.get("conditionId", "")
                tick_size = float(market.get("orderPriceMinTickSize", market.get("minimumTickSize", 0.01)))
                neg_risk = market.get("negRisk", False)

                tokens_raw = market.get("clobTokenIds", "[]")
                if isinstance(tokens_raw, str):
                    tokens = json.loads(tokens_raw)
                else:
                    tokens = tokens_raw

                if len(tokens) < 2:
                    logger_instance.error("MarketFinder", "Недостаточно токенов в clobTokenIds")
                    return None

                logger_instance.info(
                    "MarketFinder",
                    f"Рынок найден: tick={tick_size} negRisk={neg_risk} close={time.strftime('%H:%M:%S', time.localtime(close_time))}"
                )

                return {
                    "slug": slug,
                    "condition_id": condition_id,
                    "tick_size": tick_size,
                    "neg_risk": neg_risk,
                    "up_token": tokens[0],
                    "down_token": tokens[1],
                    "close_time": close_time
                }

            except requests.exceptions.RequestException as e:
                logger_instance.warning("MarketFinder", f"Попытка {attempt + 1}/3 не удалась: {str(e)}")
                time.sleep(1)

        logger_instance.error("MarketFinder", "Не удалось получить рынок после 3 попыток")
        return None
