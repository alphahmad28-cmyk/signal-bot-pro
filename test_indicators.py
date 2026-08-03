from api.market_data import get_candles
from indicators.technical import calculate_indicators

data = get_candles("XAU/USD", "1h")

if "values" not in data:
    print(data)
    exit()

df = calculate_indicators(data["values"])

print(df.tail())