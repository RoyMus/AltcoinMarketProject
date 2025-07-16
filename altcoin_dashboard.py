# altcoin_dashboard.py

import streamlit as st
import pandas as pd
import requests
import numpy as np
import time

def highlight_top_rows(s,n=3):
    return ['background-color: lightgreen'] * n + [''] * (len(s) - n)

def get_price_history(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": "30",
        "interval": "daily"
    }
    r = requests.get(url, params=params)
    if r.status_code != 200:
        st.error(f"Error fetching data for {coin_id}: {r.json().get('error', 'Unknown error')}")
        return pd.DataFrame()
    return pd.DataFrame(r.json()['prices'], columns=['timestamp', 'price'])

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_rsi_for_coin(coin_id):
    price_history = get_price_history(coin_id)
    if price_history.empty:
        return np.nan
    price_series = pd.Series(price_history['price'].values, index=pd.to_datetime(price_history['timestamp'], unit='ms'))
    rsi = calculate_rsi(price_series)
    return rsi.iloc[-1]  # Return the last RSI value

# ------------------
# Config
st.set_page_config(page_title="Altcoin Screener", layout="wide")
st.title("🔥 Altcoin Strength Dashboard")

# ------------------
# Fetch Data
@st.cache_data(ttl=43200) # Cache for 12 hours
def fetch_market_data():
    url = f"https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "price_change_percentage": "1h,24h,7d,14d",
        "per_page": 250,
        "order": "market_cap_desc"
    }
    r = requests.get(url, params=params)
    return pd.DataFrame(r.json())

df = fetch_market_data()

# ------------------
# Feature Engineering
df["Vol Trend"] = df["total_volume"] / df["market_cap"]
df["Momentum"] = df["price_change_percentage_7d_in_currency"] / 7  # basic proxy
df["EMA Diff"] = (df["current_price"] - df["high_24h"]) / df["current_price"]  # dummy placeholder

# Normalize & Score
def normalize(series):
    return (series - series.min()) / (series.max() - series.min())

df["score"] = (
    0.35 * normalize(df["price_change_percentage_7d_in_currency"]) +
    0.25 * normalize(df["Momentum"]) +
    0.2 * normalize(df["Vol Trend"]) +
    0.2 * normalize(df["price_change_percentage_14d_in_currency"])
)

df_sorted = df.sort_values(by="score", ascending=False)



# ------------------
# Display Table
dataframe = st.dataframe(
    df_sorted[["id", "score", "price_change_percentage_7d_in_currency",
               "price_change_percentage_14d_in_currency", "Vol Trend", "Momentum", "EMA Diff"]]
    .rename(columns={
        "id": "Token",
        "score": "Score",
        "price_change_percentage_7d_in_currency": "7d Return",
        "price_change_percentage_14d_in_currency": "14d Return",
    }).style.apply(highlight_top_rows, n=3, axis=0),
    use_container_width=True
)
