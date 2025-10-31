import streamlit as st
import pandas as pd

# Set page config
st.set_page_config(page_title="Orderbook Simulation — Educational", layout="wide")

# Apply custom professional styling
st.markdown(
    """
    <style>
    body {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        color: #f8f9fa;
    }
    .stApp {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        color: #f8f9fa;
        font-family: 'Segoe UI', sans-serif;
    }
    .block-container {
        padding: 2rem 3rem;
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.05);
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
    h1, h2, h3, h4 {
        color: #00e0ff;
    }
    .stButton>button {
        background-color: #00e0ff;
        color: black;
        border-radius: 10px;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #02b3e4;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Title
st.title("💹 Orderbook Simulation — Educational Only")

# Sidebar inputs
st.sidebar.header("Simulation Parameters")
fair_price = st.sidebar.number_input("Fair price", value=40.0, step=1.0, format="%.2f")
algo_bid = st.sidebar.number_input("ALGO initial bid", value=20.0, step=1.0, format="%.2f")
algo_ask = st.sidebar.number_input("ALGO initial ask", value=100.0, step=1.0, format="%.2f")
human_buy = st.sidebar.number_input("Human limit buy price", value=21.0, step=1.0, format="%.2f")
threshold_pct = st.sidebar.slider("Sell threshold above fair (%)", 0, 100, 20)
run_button = st.sidebar.button("Run Simulation 🚀")


def simulate():
    HUMAN, ALGO, OTHER = 'HUMAN', 'ALGO', 'OTHER'
    orderbook = {'bids': [(algo_bid, 100, ALGO)], 'asks': [(algo_ask, 100, ALGO)]}
    events = []

    def record(ts, actor, action, price=None, note=None):
        bb = max(orderbook['bids'], key=lambda x: x[0])[0]
        ba = min(orderbook['asks'], key=lambda x: x[0])[0]
        mid = (bb + ba) / 2
        events.append({'t': ts, 'actor': actor, 'action': action, 'price': price, 'best_bid': bb, 'best_ask': ba, 'mid': mid, 'note': note})

    ts = 0
    record(ts, 'INIT', 'Initial quotes')

    ts += 1
    orderbook['bids'].append((human_buy, 10, HUMAN))
    record(ts, HUMAN, 'Post bid', human_buy, 'Human places limit buy')

    ts += 1
    orderbook['bids'][0] = (algo_bid + 2, 100, ALGO)
    record(ts, ALGO, 'Improves bid', algo_bid + 2, 'Algo moves bid up slightly')

    ts += 1
    sell_trigger = fair_price * (1 + threshold_pct / 100)
    orderbook['asks'][0] = (sell_trigger, 100, ALGO)
    record(ts, ALGO, 'Sell trigger', sell_trigger, 'Algo prepares to sell at threshold')

    ts += 1
    orderbook['asks'][0] = (algo_ask, 100, ALGO)
    orderbook['bids'][0] = (algo_bid, 100, ALGO)
    record(ts, ALGO, 'Reset quotes', None, 'Algo resets to original quotes')

    return pd.DataFrame(events)

if run_button:
    df = simulate()
    st.subheader("📊 Simulation Events")
    st.dataframe(df, use_container_width=True)

    st.info("✅ Simulation complete. This is for educational understanding of market behavior, not for trading use.") 
