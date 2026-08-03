from api.market_data import get_candles

data = get_candles("XAU_USD", "H1")

print(data)