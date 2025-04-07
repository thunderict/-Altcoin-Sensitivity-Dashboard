import streamlit as st
import requests
import time

# Function for intro screen
def intro_screen():
    st.title("Altcoin Beta Dashboard")
    st.markdown("""
        ### Welcome to the **Altcoin Beta Calculator**!
        This app allows you to calculate how much an altcoin will move based on BTC's movement using **beta** and **volatility** metrics.
        
        - Select an altcoin from the dropdown
        - View its beta value vs BTC
        - Input BTC's % movement to see how the altcoin will react!
        
        Built with Streamlit, powered by the CoinGecko API.
    """)

# Function to toggle light/dark mode
def toggle_theme():
    theme = st.radio("Choose your theme", ("Light", "Dark"), index=1)

    if theme == "Dark":
        st.markdown("""
            <style>
            body {
                background-color: #1e1e1e;
                color: white;
            }
            </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <style>
            body {
                background-color: #f5f5f5;
                color: black;
            }
            </style>
        """, unsafe_allow_html=True)

# Function to fetch coin data (using @st.cache_data)
@st.cache_data
def fetch_coin_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 250}
    response = requests.get(url, params=params)
    return response.json()

# Auto-refresh function
def auto_refresh():
    st.write("Last refreshed: ", time.strftime("%Y-%m-%d %H:%M:%S"))
    st.button("Refresh", key="refresh")

# Function for tracking user interactions
def track_interactions():
    if 'refresh_count' not in st.session_state:
        st.session_state.refresh_count = 0
    
    if st.button("Refresh"):
        st.session_state.refresh_count += 1
        st.write(f"Refresh clicked {st.session_state.refresh_count} times!")

# Main Function
def main():
    # Show Intro screen once
    if 'intro_shown' not in st.session_state:
        intro_screen()
        st.session_state.intro_shown = True
    
    # Toggle theme
    toggle_theme()
    
    # Fetch Coin Data
    coin_data = fetch_coin_data()
    
    # Search Bar for coins
    coin_search = st.text_input("Search for a coin:")
    filtered_coins = [coin for coin in coin_data if coin_search.lower() in coin['name'].lower()]
    
    if filtered_coins:
        st.write("Filtered Results: ", filtered_coins)
    else:
        st.write("No coins found. Please refine your search.")
    
    # Auto-refresh
    auto_refresh()

    # Track refresh button interactions
    track_interactions()

# Run the app
if __name__ == "__main__":
    main()
