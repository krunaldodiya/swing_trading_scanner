import streamlit as st
import yfinance as yf
import pandas_ta as ta
import json
from datetime import datetime, timedelta
import pandas as pd
import asyncio

# Set page width
st.set_page_config(layout="wide")

async def scanning_conditions(data):
    """
    Define scanning conditions here.
    Returns boolean Series indicating which rows meet the conditions.
    """
    adx = ta.adx(high=data["High"], low=data["Low"], close=data["Close"], length=14)
    rsi = ta.rsi(close=data["Close"], length=14)
    sma_7 = ta.sma(close=data["Close"], length=7)
    sma_14 = ta.sma(close=data["Close"], length=14)

    data["ADX"] = adx["ADX_14"]
    data["RSI"] = rsi
    data["SMA7"] = sma_7
    data["SMA14"] = sma_14

    conditions_met = (
        (data["ADX"] > 20) &
        (data["RSI"] > 30) & (data["RSI"] < 70) &
        (ta.cross(data["SMA7"], data["SMA14"]))  # Check for SMA7 crossunder SMA14
    )

    return conditions_met

async def fetch_stock_data(stock, start_date, end_date):
    try:
        # Get historical data
        data = yf.download(
            tickers=stock, 
            period="1d", 
            start=start_date.strftime("%Y-%m-%d"), 
            end=end_date.strftime("%Y-%m-%d"),
        )

        data['Symbol'] = stock

        conditions_met = await scanning_conditions(data)

        filtered_data = data[conditions_met]

        yesterday = (datetime.today() - timedelta(days=1)).date()

        # If there are matching stocks for yesterday, append to the DataFrame
        if not filtered_data.empty and filtered_data.index[-1].date() == yesterday:
            filtered_data = filtered_data[["Symbol", "Close", "Volume", "ADX", "RSI", "SMA7", "SMA14"]]
            filtered_data.index = filtered_data.index.strftime('%Y-%m-%d')
            return filtered_data.tail(1)

    except Exception as e:
        st.error(f"Error fetching data for {stock}: {str(e)}")

    return pd.DataFrame()

async def scan_stocks_async(stocks, start_date, end_date):
    tasks = [fetch_stock_data(stock, start_date, end_date) for stock in stocks]
    results = await asyncio.gather(*tasks)
    return pd.concat(results)

def main():
    st.title("Swing Trading Stock Scanner")
    st.write(
        "This tool scans stocks based on the following conditions:\n"
        "1) ADX > 20\n"
        "2) RSI between 30 and 70\n"
        "3) SMA7 Crossunder SMA14"
    )

    # Load stock symbols from stocks.json
    try:
        with open("stocks.json", "r") as file:
            stocks_json = json.load(file)
            stocks = [stock for stock in stocks_json]
            stock_list = ", ".join(stocks)

        st.info(f"Loaded stocks: {stock_list}")

    except FileNotFoundError:
        st.error("Stocks file (stocks.json) not found.")
        return
    except json.JSONDecodeError:
        st.error("Invalid JSON format in stocks.json.")
        return

    # Date inputs for start and end dates
    start_date = st.date_input("Select start date", datetime.today() - timedelta(days=365))
    end_date = st.date_input("Select end date", datetime.today())

    if st.button("Scan"):
        st.info("Scanning...")
        matched_stocks = asyncio.run(scan_stocks_async(stocks, start_date, end_date))

        # Display results
        if not matched_stocks.empty:
            st.header("Results for Matching Stocks")
            # Reorder columns
            matched_stocks = matched_stocks[["Symbol", "Close", "Volume", "ADX", "RSI", "SMA7", "SMA14"]]
            st.dataframe(matched_stocks)
        else:
            st.info("No stocks matched the conditions for yesterday.")

if __name__ == "__main__":
    main()
