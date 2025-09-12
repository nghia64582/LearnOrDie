import datetime as dt
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
        # set end_date to yesterday with format YYYY-MM-DD
        end_date = dt.datetime.now().date() - dt.timedelta(days=1)
        end_date_str = end_date.strftime("%Y-%m-%d")
        df = pd.DataFrame(quote.history(start='2021-01-01', end=end_date_str))
        path = f"{STOCK_PRICE_DIR}/{symbol}.csv"
        df.to_csv(path, index=False)

def process_stock_data():
    percentage_by_symbol = {}
    start_time = dt.datetime(2021, 1, 1)
    end_time = dt.datetime(2025, 8, 10)
    print(f"Processing stock data from {start_time} to {end_time}")
    process(start_time, end_time)

def get_first_date_has_data(date: dt.datetime, df: pd.DataFrame) -> dt.datetime:
    # return the first date in the DataFrame that is greater than or equal to the given date
    
    df['time'] = pd.to_datetime(df['time'])
    mask = df['time'] >= date
    if mask.any():
        return df.loc[mask, 'time'].min()
    return pd.NaT

def process(start_date: dt.datetime, end_date: dt.datetime) -> list[dict]:
    price_by_symbol = {}
    for symbol in main_symbols:
        path = f"{STOCK_PRICE_DIR}/{symbol}.csv"
        df = pd.read_csv(path)
        first_date = get_first_date_has_data(start_date, df)
        last_date = get_first_date_has_data(end_date, df)
        if pd.isna(first_date) or pd.isna(last_date):
            continue
        # Filter the DataFrame for the date range
        df_filtered = df[(df['time'] >= first_date) & (df['time'] <= last_date)]
        start_price = df_filtered['close'].iloc[0] if not df_filtered.empty else None
        end_price = df_filtered['close'].iloc[-1] if not df_filtered.empty else None
        if start_price is not None and end_price is not None:
            price_by_symbol[symbol] = {
                'start_price': start_price,
                'end_price': end_price,
                'percentage_change': int((end_price - start_price) / start_price * 100)
            }
    list_data = []
    
    for symbol, data in price_by_symbol.items():
        list_data.append({
            'symbol': symbol,
            'start_price': data['start_price'],
            'end_price': data['end_price'],
            'increased_rate': data['percentage_change']
        })
    list_data.sort(key=lambda x: x['increased_rate'], reverse=True)
    return list_data

# save_main_symbols_prices()
# process_stock_data()