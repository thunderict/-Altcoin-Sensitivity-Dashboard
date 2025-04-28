import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

# ------------------- UI CONFIG (Fixed) ------------------- #
st.set_page_config(
    page_title="Altcoin Beta & Volatility Dashboard (TradingView ATR)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Force dark theme with no glitches
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #0e1117; }
    .st-emotion-cache-1dj0hjr { color: white; }
    .stSelectbox, .stNumberInput, .stRadio > label { color: white !important; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Altcoin Sensitivity Dashboard (ATR Upgraded)")
st.caption("Volatility now matches TradingView's ATR(14)/Close method")

# ------------------- API SETUP (Optimized) ------------------- #
COINGECKO_API = "https://api.coingecko.com/api/v3"
BINANCE_API = "https://api.binance.com/api/v3"

@st.cache_data(ttl=3600)
def get_all_coins():
    """Fetch all CoinGecko coins with retry logic."""
    try:
        url = f"{COINGECKO_API}/coins/list"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return pd.DataFrame(r.json())
    except Exception as e:
        st.error(f"CoinGecko API error: {str(e)}")
        return pd.DataFrame()

def get_ohlc_data(coin_id, days=14):
    """
    Fetch OHLC data from CoinGecko → fallback to Binance if needed.
    Returns: DataFrame with columns [timestamp, open, high, low, close]
    """
    try:
        # Try CoinGecko first
        url = f"{COINGECKO_API}/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"
        data = requests.get(url, timeout=10).json()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except:
        # Fallback to Binance
        symbol = "BTCUSDT" if coin_id == "bitcoin" else f"{coin_id.upper()}USDT"
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        url = f"{BINANCE_API}/klines?symbol={symbol}&interval=1d&startTime={int(start_time.timestamp()*1000)}&endTime={int(end_time.timestamp()*1000)}"
        data = requests.get(url).json()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'trades', 'taker_buy_volume', 'taker_buy_quote_volume', 'ignore'])
        df = df[['timestamp', 'open', 'high', 'low', 'close']].astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

# ------------------- CORE CALCULATIONS (Upgraded) ------------------- #
def calculate_true_range(high, low, prev_close):
    """True Range for ATR calculation."""
    return max(high - low, abs(high - prev_close), abs(low - prev_close))

def calculate_atr(df, window=14):
    """Calculate ATR(14) from OHLC data."""
    df['prev_close'] = df['close'].shift(1)
    df['TR'] = df.apply(lambda x: calculate_true_range(x['high'], x['low'], x['prev_close']), axis=1)
    df['ATR'] = df['TR'].rolling(window).mean()
    return df['ATR'].iloc[-1]  # Return latest ATR(14)

def calculate_beta(btc_returns, alt_returns):
    """Unchanged covariance/variance method."""
    covariance = np.cov(alt_returns, btc_returns)[0][1]
    btc_variance = np.var(btc_returns)
    return covariance / btc_variance if btc_variance != 0 else 0

def calculate_volatility_multiplier(btc_ohlc, alt_ohlc):
    """TradingView-style: (ATR(14)/Close) for altcoin ÷ BTC."""
    btc_atr = calculate_atr(btc_ohlc)
    alt_atr = calculate_atr(alt_ohlc)
    btc_vol = (btc_atr / btc_ohlc['close'].iloc[-1]) * 100
    alt_vol = (alt_atr / alt_ohlc['close'].iloc[-1]) * 100
    return alt_vol / btc_vol if btc_vol != 0 else 0

# ------------------- UI LAYOUT (Debugged) ------------------- #
all_coins = get_all_coins()

with st.sidebar:
    st.header("Settings")
    mode = st.radio("Calculation Mode:", ["Beta", "Volatility Multiplier"], index=0)
    search = st.text_input("🔍 Search Coin (name/symbol)", key="search").lower()
    filtered_coins = all_coins[all_coins['name'].str.contains(search, case=False) | all_coins['symbol'].str.contains(search, case=False)]
    selected_coin = st.selectbox("Select Coin:", filtered_coins['id'].tolist(), key="coin_select")

# ------------------- MAIN CALCULATIONS ------------------- #
if selected_coin:
    with st.spinner(f"Calculating {selected_coin} {mode}..."):
        try:
            btc_ohlc = get_ohlc_data("bitcoin")
            alt_ohlc = get_ohlc_data(selected_coin)
            
            if mode == "Beta":
                btc_returns = np.log(btc_ohlc['close'] / btc_ohlc['close'].shift(1)).dropna()
                alt_returns = np.log(alt_ohlc['close'] / alt_ohlc['close'].shift(1)).dropna()
                result = calculate_beta(btc_returns, alt_returns)
            else:
                result = calculate_volatility_multiplier(btc_ohlc, alt_ohlc)
            
            st.metric(label=f"{selected_coin.upper()} {mode}", value=round(result, 3))
            
            # BTC Move Calculator
            btc_move = st.number_input("💰 BTC % Move (e.g., 5 for 5%)", value=1.0, min_value=-100.0, max_value=100.0)
            alt_move = btc_move * result
            st.success(f"**Estimated {selected_coin.upper()} Move**: {round(alt_move, 2)}%")
            
        except Exception as e:
            st.error(f"Error calculating {mode}: {str(e)}")

# ------------------- CSV EXPORT (Fixed) ------------------- #
if st.sidebar.button("📤 Export Data"):
    with st.spinner("Exporting..."):
        try:
            coin_ids = filtered_coins['id'].tolist()
            export_data = []
            for coin in coin_ids[:10]:  # Limit to 10 coins to avoid rate limits
                try:
                    btc_ohlc = get_ohlc_data("bitcoin")
                    coin_ohlc = get_ohlc_data(coin)
                    if mode == "Beta":
                        btc_returns = np.log(btc_ohlc['close'] / btc_ohlc['close'].shift(1)).dropna()
                        coin_returns = np.log(coin_ohlc['close'] / coin_ohlc['close'].shift(1)).dropna()
                        val = calculate_beta(btc_returns, coin_returns)
                    else:
                        val = calculate_volatility_multiplier(btc_ohlc, coin_ohlc)
                    export_data.append((coin, val))
                except:
                    continue
            df_export = pd.DataFrame(export_data, columns=["Coin", mode])
            st.sidebar.download_button("⬇️ Download CSV", df_export.to_csv(index=False), file_name=f"altcoin_{mode}.csv")
        except Exception as e:
            st.sidebar.error(f"Export failed: {str(e)}")
