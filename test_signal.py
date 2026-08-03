from api.market_data import get_candles
from indicators.technical import calculate_indicators
from signals.signal_engine import generate_signal

data = get_candles("XAU/USD", "1h")

df = calculate_indicators(data["values"])

signal = generate_signal(df)

print(signal)