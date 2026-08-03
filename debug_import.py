import api.market_data as md

print("Loaded from:", md.__file__)
print("Has get_price:", hasattr(md, "get_price"))
print("Has get_candles:", hasattr(md, "get_candles"))
print(dir(md))