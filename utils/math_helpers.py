import math

def calculate_max_entry_price(profit_percent: float) -> float:
    return 1.0 / (1.0 + profit_percent / 100.0)

def round_price(price: float, tick_size: float) -> float:
    return math.floor(price / tick_size) * tick_size

def calculate_order_size(usdc_amount: float, price: float) -> float:
    return max(usdc_amount / price, 5.0)
