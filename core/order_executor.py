from py_clob_client_v2 import ClobClient, MarketOrderArgs, OrderType, PartialCreateOrderOptions, Side
from utils.logger import logger_instance
from utils.math_helpers import round_price

class OrderExecutor:
    def __init__(self, clob_client: ClobClient, funder_address: str):
        self.client = clob_client
        self.funder_address = funder_address

    def execute_fak_order(self, token_id: str, max_entry_price: float, usdc_amount: float, tick_size: float):
        try:
            price = round_price(max_entry_price, tick_size)

            logger_instance.info(
                "OrderExecutor",
                f"Выставление FAK: token={token_id[:10]}... цена={price:.4f} USDC={usdc_amount}"
            )

            order_args = MarketOrderArgs(
                token_id=token_id,
                price=price,
                amount=usdc_amount,
                side=Side.BUY,
            )

            options = PartialCreateOrderOptions(
                tick_size=str(tick_size),
                neg_risk=False
            )

            resp = self.client.create_and_post_market_order(
                order_args=order_args,
                options=options,
                order_type=OrderType.FAK,
            )

            if not isinstance(resp, dict):
                logger_instance.warning("OrderExecutor", f"Нестандартный ответ: {resp}")
                return resp

            error_msg = resp.get("errorMsg") or resp.get("error") or ""
            if error_msg:
                if "FOK_ORDER_NOT_FILLED" in error_msg or "FAK_ORDER_NOT_FILLED" in error_msg:
                    logger_instance.warning("OrderExecutor", f"FAK не исполнен (нет ликвидности)")
                elif "NOT_ENOUGH_BALANCE" in error_msg:
                    logger_instance.critical("OrderExecutor", f"Недостаточно средств: {error_msg}")
                    raise ValueError("INVALID_ORDER_NOT_ENOUGH_BALANCE")
                else:
                    logger_instance.error("OrderExecutor", f"Ошибка ордера: {error_msg}")
            else:
                order_id = resp.get("orderID") or resp.get("id") or "n/a"
                logger_instance.info("OrderExecutor", f"Ордер принят: {order_id}")

            return resp

        except Exception as e:
            logger_instance.error("OrderExecutor", f"Исключение при выставлении ордера: {str(e)}")
            if "INVALID_ORDER_NOT_ENOUGH_BALANCE" in str(e):
                raise
            return None
