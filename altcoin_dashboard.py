import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
from io import StringIO

# ------------------- UI CONFIG ------------------- #
st.set_page_config(
    page_title="Altcoin Beta & Volatility Multiplier Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    body { background-color: #0e1117; color: white; }
    .stApp { background-color: #0e1117; }
    .css-1d391kg { background-color: #0e1117; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Altcoin Sensitivity Dashboard")
st.markdown("Compare how strongly altcoins react to BTC movements using **Beta** or your custom **Volatility Multiplier** model.")

# ------------------- API SETUP ------------------- #
COINGECKO_API = "https://api.coingecko.com/api/v3"

@st.cache_data(ttl=3600)
def get_all_coins():
    url = f"{COINGECKO_API}/coins/list"
    r = requests.get(url)
    return pd.DataFrame(r.json())

@st.cache_data(ttl=3600)
def get_coin_market_chart(coin_id, days=30):
    url = f"{COINGECKO_API}/coins/{coin_id}/market_chart?vs_currency=usd&days={days}&interval=daily"
    r = requests.get(url)
    prices = r.json().get("prices", [])
    df = pd.DataFrame(prices, columns=['timestamp', 'price'])
    df['price'] = df['price'].astype(float)
    return df['price']

# ------------------- CALCULATIONS ------------------- #
def calculate_beta(btc_returns, alt_returns):
    covariance = np.cov(alt_returns, btc_returns)[0][1]
    btc_variance = np.var(btc_returns)
    return covariance / btc_variance if btc_variance != 0 else 0

def calculate_volatility_multiplier(btc_returns, alt_returns):
    return np.std(alt_returns) / np.std(btc_returns) if np.std(btc_returns) != 0 else 0

@st.cache_data(ttl=1800)
def calculate_coin_sensitivity(coin_id, mode="Beta"):
    btc_prices = get_coin_market_chart("bitcoin")
    alt_prices = get_coin_market_chart(coin_id)
    if len(btc_prices) != len(alt_prices):
        min_len = min(len(btc_prices), len(alt_prices))
        btc_prices = btc_prices[-min_len:]
        alt_prices = alt_prices[-min_len:]

    btc_returns = np.log(btc_prices / btc_prices.shift(1)).dropna()
    alt_returns = np.log(alt_prices / alt_prices.shift(1)).dropna()

    if mode == "Beta":
        return round(calculate_beta(btc_returns, alt_returns), 3)
    else:
        return round(calculate_volatility_multiplier(btc_returns, alt_returns), 3)

# ------------------- SIDEBAR ------------------- #
all_coins = get_all_coins()

mode = st.sidebar.radio("Choose Calculation Mode:", ["Beta", "Volatility Multiplier"])
search = st.sidebar.text_input("🔍 Search for a coin (e.g., solana)").lower()

filtered_coins = all_coins[all_coins['name'].str.contains(search, case=False) | all_coins['symbol'].str.contains(search, case=False)]

selected_coin = st.sidebar.selectbox("Select Coin:", filtered_coins['id'].tolist())

sensitivity = calculate_coin_sensitivity(selected_coin, mode)

st.metric(label=f"{selected_coin.capitalize()} {mode}", value=sensitivity)

# ------------------- CALCULATOR ------------------- #
btc_move = st.number_input("📌 Enter BTC % Move (e.g. 5 for 5%)", value=1.0)
alt_move = btc_move * sensitivity
st.success(f"Estimated {selected_coin.upper()} move: {round(alt_move, 2)}% based on {mode}")

# ------------------- OPTIONAL CSV EXPORT ------------------- #
if st.sidebar.button("📤 Export Sensitivity Data"):
    coin_ids = filtered_coins['id'].tolist()
    export_data = []
    for coin in coin_ids:
        try:
            sens = calculate_coin_sensitivity(coin, mode)
            export_data.append((coin, sens))
        except:
            continue
    df_export = pd.DataFrame(export_data, columns=["Coin", f"{mode}"])
    csv = df_export.to_csv(index=False)
    st.sidebar.download_button("Download CSV", csv, file_name=f"altcoin_{mode.lower()}_data.csv")
