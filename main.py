import streamlit as st
import yfinance as yf
import pandas_ta as ta
import json
from datetime import datetime, timedelta
import pandas as pd
import asyncio

# Set page width
st.set_page_config(layout="wide")

async def fetch_data(symbol, start_date, end_date):
    try:
        data = yf.download(
            tickers=symbol,
            period="1d",
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
        )

        adx = ta.adx(high=data["High"], low=data["Low"], close=data["Close"], length=14)
        data["ADX"] = adx["ADX_14"]
        data["RSI"] = ta.rsi(close=data["Close"], length=14)
        data["SMA7"] = ta.sma(close=data["Close"], length=7)
        data["SMA14"] = ta.sma(close=data["Close"], length=14)
        data["SMA21"] = ta.sma(close=data["Close"], length=21)

        conditions_met = (
            (data["ADX"] > 25) &
            (data["RSI"] > 30) & (data["RSI"] < 70) &
            (data["SMA7"] > data["SMA14"]) &
            (data["SMA14"] > data["SMA21"])
        )

        filtered_data = data[conditions_met]

        yesterday = (datetime.today() - timedelta(days=1)).date()

        if not filtered_data.empty and filtered_data.index[-1].date() == yesterday:
            filtered_data["Symbol"] = symbol
            filtered_data = filtered_data[["Symbol", "Close", "Volume", "ADX", "RSI", "SMA7", "SMA14", "SMA21"]]
            filtered_data.index = filtered_data.index.strftime('%Y-%m-%d')
            return filtered_data.tail(1)

    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {str(e)}")

    return None

async def scan_stocks(stocks, start_date, end_date):
    tasks = []
    for symbol in stocks:
        tasks.append(fetch_data(symbol, start_date, end_date))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return pd.concat([result for result in results if result is not None])

def main():
    st.title("Swing Trading Stock Scanner")
    st.write(
        "This tool scans stocks based on the following conditions:\n"
        "1) ADX > 25\n"
        "2) RSI between 30 and 70\n"
        "3) SMA7 > SMA14 > SMA21"
    )

    # Load stock symbols from stocks.json
    try:
        with open("stocks.json", "r") as file:
            stocks_json = json.load(file)
            stocks = [stock for stock in stocks_json]

        st.info("Loaded stocks from stocks.json")

    except FileNotFoundError:
        st.error("Stocks file (stocks.json) not found.")
        return
    except json.JSONDecodeError:
        st.error("Invalid JSON format in stocks.json.")
        return

    # Date inputs for start and end dates
    start_date = st.date_input("Select start date", datetime.today() - timedelta(days=60))
    end_date = st.date_input("Select end date", datetime.today())

    if st.button("Scan"):
        st.info("Scanning...")
        matched_stocks = asyncio.run(scan_stocks(stocks, start_date, end_date))

        # Display results
        if not matched_stocks.empty:
            st.header("Results for Matching Stocks")
            st.dataframe(matched_stocks)
        else:
            st.info("No stocks matched the conditions for yesterday.")

if __name__ == "__main__":
    main()
