
import pandas as pd
from stocks import main_symbols

STOCK_PRICE_DIR = "stock_prices"

def save_all_symbols():
    # Get all symbols
    from vnstock import Quote, Listing
    listing = Listing()
    df = pd.DataFrame(listing.all_symbols())
    # Write all data to CSV
    df.to_csv('all_symbols.csv', index=False)

def save_main_symbols_prices():
    from vnstock import Quote, Listing
    for symbol in main_symbols:
        quote = Quote(symbol=symbol, source='VCI')
        df = pd.DataFrame(quote.history(start='2024-01-01', end='2025-08-30'))
        path = f"{STOCK_PRICE_DIR}/{symbol}.csv"
        df.to_csv(path, index=False)

def process_stock_data():
    percentage_by_symbol = {}
    start_time = '2025-06-02'
    end_time = '2025-08-27'
    for symbol in main_symbols:
        path = f"{STOCK_PRICE_DIR}/{symbol}.csv"
        df = pd.read_csv(path)
        # Process the DataFrame (df) as needed
        # start_price = df['close'].iloc[0]
        # end_price = df['close'].iloc[-1]
        start_price = df.loc[df['time'] == start_time, 'close'].values[0]
        end_price = df.loc[df['time'] == end_time, 'close'].values[0]
        percentage_by_symbol[symbol] = (end_price - start_price) / start_price * 100

    # for symbol, percentage in percentage_by_symbol.items():
    #     print(f"Symbol: {symbol}, Increased Percentage: {percentage:.2f}%")

    list_increased = sorted(percentage_by_symbol.items(), key=lambda x: x[1], reverse=True)
    print("Top symbols with highest increase:")
    for symbol, percentage in list_increased:
        print(f"Symbol: {symbol}, Increased Percentage: {percentage:.2f}%")

save_main_symbols_prices()
# process_stock_data()