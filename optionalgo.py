import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from math import isclose

st.set_page_config(page_title="Orderbook Simulation (Educational)", layout="wide")
st.title("Orderbook Simulation — Educational (not for market manipulation)")
st.markdown(
    """
    This Streamlit app simulates a tiny limit orderbook to illustrate the behavior you described: an "ALGO"
    agent posting wide quotes, a human entering the book, the mid-price moving toward a fair value, and
    the ALGO briefly selling at an elevated price and then reverting.

    **Important:** This app is for learning, detection and research only. It must not be used to design
    or execute manipulative trading strategies in real markets.
    """
)

# --- Sidebar controls ---
st.sidebar.header("Simulation parameters")
fair_price = st.sidebar.number_input("Fair price", value=40.0, step=1.0, format="%.2f")
algo_bid = st.sidebar.number_input("ALGO initial bid", value=20.0, step=1.0, format="%.2f")
algo_ask = st.sidebar.number_input("ALGO initial ask", value=100.0, step=1.0, format="%.2f")
human_buy = st.sidebar.number_input("Human limit buy price", value=21.0, step=1.0, format="%.2f")
other_tick_steps = st.sidebar.slider("Passive liquidity steps", 0, 10, 4)
threshold_pct = st.sidebar.slider("Sell threshold above fair (%)", 0, 100, 20)
size_algo = st.sidebar.number_input("Size for ALGO orders", value=100, step=1)
size_human = st.sidebar.number_input("Size for human order", value=10, step=1)

st.sidebar.markdown("---")
run_button = st.sidebar.button("Run simulation")

# --- Helper functions for orderbook simulation ---

def best_bid(orderbook):
    if not orderbook['bids']:
        return (None, 0, None)
    return max(orderbook['bids'], key=lambda x: x[0])

def best_ask(orderbook):
    if not orderbook['asks']:
        return (None, 0, None)
    return min(orderbook['asks'], key=lambda x: x[0])

def mid_price(orderbook):
    bb = best_bid(orderbook)[0]
    ba = best_ask(orderbook)[0]
    if bb is None or ba is None:
        return None
    return (bb + ba) / 2.0


def simulate(fair_price, algo_bid, algo_ask, human_buy, steps=4, threshold_pct=20, size_algo=100, size_human=10):
    HUMAN = 'HUMAN'
    ALGO = 'ALGO'
    OTHER = 'OTHER'

    orderbook = {
        'bids': [(algo_bid, size_algo, ALGO)],
        'asks': [(algo_ask, size_algo, ALGO)],
    }

    events = []

    def record(ts, actor, action, price=None, size=None, note=None):
        bb = best_bid(orderbook)[0]
        ba = best_ask(orderbook)[0]
        events.append({'t': ts, 'actor': actor, 'action': action, 'price': price, 'size': size, 'note': note,
                       'best_bid': bb, 'best_ask': ba, 'mid': mid_price(orderbook)})

    ts = 0
    record(ts, 'INIT', 'initial quotes')

    # 1: human posts buy
    ts += 1
    orderbook['bids'].append((human_buy, size_human, HUMAN))
    record(ts, HUMAN, 'post bid', human_buy, size_human, 'human limit buy')

    # 2: algo improves bid to regain top-of-book
    ts += 1
    # replace algo bid if present
    replaced = False
    for i, (p, s, a) in enumerate(orderbook['bids']):
        if isclose(p, algo_bid) and a == ALGO:
            orderbook['bids'][i] = (algo_bid + 2.0, s, a)
            replaced = True
            record(ts, ALGO, 'replace bid', algo_bid + 2.0, s, 'algo updates bid to regain top')
            break
    if not replaced:
        orderbook['bids'].append((algo_bid + 2.0, size_algo, ALGO))
        record(ts, ALGO, 'post bid', algo_bid + 2.0, size_algo, 'algo posts improved bid')

    # 3.. steps: mid drifts upward due to passive liquidity improvement
    for step in range(steps):
        ts += 1
        # passive participants improve bids
        current_bb = best_bid(orderbook)[0] or human_buy
        new_bid = current_bb + max(1.0, step * 1.0)
        orderbook['bids'].append((new_bid, 20, OTHER))
        record(ts, OTHER, 'post bid', new_bid, 20, 'other liquidity')

        # algo tightens ask toward fair
        # find algo ask and move it closer (replace)
        for i, (p, s, a) in enumerate(orderbook['asks']):
            if a == ALGO:
                new_ask = max(p - 10.0, fair_price + 10.0 - step * 3.0)
                orderbook['asks'][i] = (new_ask, s, a)
                record(ts, ALGO, 'replace ask', new_ask, s, 'algo tightens ask')
                break

    # Check threshold
    ts += 1
    record(ts, 'CHECK', 'check mid')
    threshold = fair_price * (1.0 + threshold_pct / 100.0)

    if mid_price(orderbook) is not None and mid_price(orderbook) >= threshold:
        # ALGO sells at threshold (post ask) and human buys (fill)
        ts += 1
        orderbook['asks'].append((threshold, size_human, ALGO))
        record(ts, ALGO, 'post ask', threshold, size_human, 'algo sells at threshold')

        ts += 1
        # model a fill: human buys from that ask
        record(ts, HUMAN, 'trade(fill)', threshold, size_human, 'human buys at elevated price')

        # Revert algo to original wide quotes
        ts += 1
        # remove the threshold ask
        orderbook['asks'] = [o for o in orderbook['asks'] if not (isclose(o[0], threshold) and o[2] == ALGO)]
        record(ts, ALGO, 'remove ask', threshold, size_human, 'remove elevated ask')

        # revert algo bid
        for i, (p, s, a) in enumerate(orderbook['bids']):
            if a == ALGO:
                orderbook['bids'][i] = (algo_bid, s, a)
                record(ts, ALGO, 'replace bid', algo_bid, s, 'algo reverts bid to original')
                break
        # revert algo ask back to original wide
        for i, (p, s, a) in enumerate(orderbook['asks']):
            if a == ALGO:
                orderbook['asks'][i] = (algo_ask, s, a)
                record(ts, ALGO, 'replace ask', algo_ask, s, 'algo reverts ask to original')
                break
    else:
        ts += 1
        record(ts, 'RESULT', 'no predatory sell', None, None, 'mid did not reach threshold')

    df = pd.DataFrame(events)
    df = df.sort_values('t').reset_index(drop=True)
    return df, orderbook


# --- Run simulation and display results ---
if run_button:
    df, orderbook = simulate(fair_price, algo_bid, algo_ask, human_buy, steps=other_tick_steps,
                             threshold_pct=threshold_pct, size_algo=size_algo, size_human=size_human)

    st.subheader("Event timeline")
    st.dataframe(df[['t', 'actor', 'action', 'price', 'size', 'note', 'best_bid', 'best_ask', 'mid']])

    # Mid-price chart
    st.subheader("Mid-price over time")
    chart_df = df[['t', 'mid']].set_index('t')
    st.line_chart(chart_df)

    # Detection flags (basic educational heuristics)
    st.subheader("Detection flags (educational)")
    flags = []
    ALGO = 'ALGO'
    threshold = fair_price * (1.0 + threshold_pct / 100.0)
    suspicious = df[(df['actor'] == ALGO) & (df['action'].str.contains('post ask', na=False)) & (df['price'] == threshold)]
    if not suspicious.empty:
        flags.append("ALGO posted ask at threshold ({}).".format(threshold))
    reverts = df[(df['actor'] == ALGO) & (df['action'].str.contains('replace', na=False)) & (df['note'].str.contains('revert', na=False))]
    if not reverts.empty:
        flags.append("ALGO reverted quotes quickly after selling.")
    if flags:
        for f in flags:
            st.markdown(f"- {f}")
    else:
        st.markdown("No clear predatory pattern detected in this run.")

    # Final top-of-book
    st.subheader("Final top-of-book")
    final_bids = sorted(orderbook['bids'], key=lambda x: -x[0])
    final_asks = sorted(orderbook['asks'], key=lambda x: x[0])
    st.write("Best bid:", final_bids[0] if final_bids else None)
    st.write("Best ask:", final_asks[0] if final_asks else None)

    # Download CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download events CSV", data=csv, file_name='orderbook_events.csv', mime='text/csv')

    st.caption("This tool is educational. Do not use to design or execute manipulative strategies.")
else:
    st.info("Adjust parameters in the left sidebar and click 'Run simulation' to begin.")
