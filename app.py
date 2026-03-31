import streamlit as st
import pandas as pd
import random
import networkx as nx
import folium
from streamlit_folium import st_folium

# =========================
# PAGE SETTINGS
# =========================
st.set_page_config(layout="wide")
st.title("🗺️ Smart Route Optimizer (Fast Version)")

# =========================
# LOAD DATA FUNCTION
# =========================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv(
            "bookings.csv",
            encoding="latin1",
            on_bad_lines='skip',
            engine='python'
        )
    except Exception as e:
        st.error(f"❌ Error loading file: {e}")
        return None

    # Clean columns
    df.columns = df.columns.str.strip()

    # Check required columns
    required = ['Pickup Location', 'Drop Location', 'Ride Distance']
    for col in required:
        if col not in df.columns:
            st.error(f"❌ Missing column: {col}")
            return None

    # Clean data
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
    df = df.dropna(subset=['Ride Distance', 'Pickup Location', 'Drop Location'])

    return df

# =========================
# LOAD DATA
# =========================
df = load_data()

if df is None or df.empty:
    st.error("❌ Dataset not loaded properly. Check CSV file.")
    st.stop()

# =========================
# PREPARE DATA
# =========================
cities = sorted(set(df['Pickup Location']).union(set(df['Drop Location'])))

# =========================
# BUILD GRAPH (FAST CACHE)
# =========================
@st.cache_resource
def build_graph(df):
    G = nx.Graph()
    for _, row in df.iterrows():
        u = str(row['Pickup Location']).strip()
        v = str(row['Drop Location']).strip()
        d = row['Ride Distance']

        if G.has_edge(u, v):
            if d < G[u][v]['weight']:
                G[u][v]['weight'] = d
        else:
            G.add_edge(u, v, weight=d)
    return G

G = build_graph(df)

# =========================
# UI INPUT
# =========================
col1, col2 = st.columns(2)

start = col1.selectbox("🟢 Source", cities)
goal  = col2.selectbox("🔴 Destination", cities)

# =========================
# EVENTS (LIGHTWEIGHT)
# =========================
def generate_events():
    emap = {}
    for u, v in G.edges():
        r = random.random()
        if r < 0.05:
            emap[(u, v)] = 'BLOCKAGE'
        elif r < 0.2:
            emap[(u, v)] = 'TRAFFIC'
        else:
            emap[(u, v)] = 'CLEAR'
    return emap

# =========================
# FIND ROUTE BUTTON
# =========================
if st.button("🚀 Find Route"):

    if start == goal:
        st.warning("⚠️ Source and Destination are same!")
        st.stop()

    with st.spinner("⚡ Calculating fast route..."):

        event_map = generate_events()
        temp_G = G.copy()

        # Modify graph
        for (u, v), evt in event_map.items():
            if evt == 'BLOCKAGE':
                if temp_G.has_edge(u, v):
                    temp_G.remove_edge(u, v)
            elif evt == 'TRAFFIC':
                if temp_G.has_edge(u, v):
                    temp_G[u][v]['weight'] *= 1.5

        # Shortest path
        try:
            path = nx.shortest_path(temp_G, start, goal, weight='weight')
            dist = nx.shortest_path_length(temp_G, start, goal, weight='weight')
        except:
            st.error("❌ No route found!")
            st.stop()

    # =========================
    # RESULT
    # =========================
    st.success("✅ Route Found")

    stops = len(path) - 1
    time_minutes = (dist / 40) * 60

    colA, colB, colC = st.columns(3)

    colA.metric("📏 Distance", f"{dist:.2f} km")
    colB.metric("🛑 Stops", stops)
    colC.metric("⏱️ Time", f"{time_minutes:.0f} mins")

    st.write("### 📍 Path")
    st.write(" ➝ ".join(path))

    # =========================
    # MAP (FAST)
    # =========================
    coords = {city: (random.uniform(20, 28), random.uniform(70, 88)) for city in cities}

    m = folium.Map(location=coords[start], zoom_start=6)

    route_coords = [coords[c] for c in path]

    folium.PolyLine(route_coords, color="green", weight=5).add_to(m)

    folium.Marker(coords[start], icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coords[goal], icon=folium.Icon(color="red")).add_to(m)

    st_folium(m, width=900, height=500)
