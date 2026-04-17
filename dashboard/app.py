import streamlit as st
import pandas as pd
import time
import os
import plotly.express as px

st.set_page_config(page_title="Sentinel-HealOps", page_icon="🛡️", layout="wide")

st.title("🛡️ Sentinel-HealOps Control Center")
st.subheader("Autonomous Machine Learning SRE Agent")
st.markdown("---")

LOG_FILE = "/tmp/healops_trades.csv"

def load_data(limit=500):
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame()
    try:
        # Load exactly 6 columns corresponding to C++ logs and Python load_generator
        df = pd.read_csv(LOG_FILE, names=['timestamp_ns', 'buy_id', 'sell_id', 'price', 'qty', 'latency_ns'], header=0)
        
        if df.empty:
            return pd.DataFrame()
            
        df = df.tail(limit)
        df['latency_ms'] = df['latency_ns'] / 1e6
        df['trade_id'] = range(len(df))
        return df
    except Exception as e:
        st.error(f"Error parsing logs: {e}")
        return pd.DataFrame()

df = load_data()

placeholder = st.empty()

with placeholder.container():
    col1, col2, col3, col4 = st.columns(4)
    
    if not df.empty:
        current_lat = df['latency_ms'].iloc[-1]
        historical_mean = df['latency_ms'].mean()
        max_lat = df['latency_ms'].max()
        
        # Heuristic display mirroring the AI model thresholds
        status = "HEALTHY"
        if current_lat > 50:
            status = "NETWORK_DELAY -> ROLLBACKING"
        elif current_lat > 10:
            status = "CPU_SPIKE -> RESTARTING"
            
        col1.metric("Live Latency", f"{current_lat:.2f} ms", f"{current_lat - historical_mean:.2f} ms", delta_color="inverse")
        col2.metric("Mean Latency", f"{historical_mean:.2f} ms")
        col3.metric("Max Latency", f"{max_lat:.2f} ms")
        col4.metric("AI Governor State", status)
        
        st.markdown("### High-Frequency Latency Telemetry")
        
        # Render a rich plotly chart
        fig = px.line(df, x='trade_id', y='latency_ms', title='Latency Over Time', markers=True)
        fig.add_hline(y=10.0, line_dash="dash", line_color="orange", annotation_text="CPU Spike Threshold")
        fig.add_hline(y=50.0, line_dash="dash", line_color="red", annotation_text="Network Delay Threshold")
        fig.update_layout(yaxis_title="Latency (ms)", xaxis_title="Recent Trade Tick", template='plotly_dark')
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("⚠️ Waiting for C++ Engine telemetry stream. Run `python3 scripts/load_generator.py` to begin.")

# Streamlit hack loop for real-time tracking
time.sleep(1)
st.rerun()
