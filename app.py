import streamlit as st
import pandas as pd
import networkx as nx
import random
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

st.title("🗺️ Smart Route Optimizer Pro")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv("bookings3.csv", encoding="latin1", on_bad_lines='skip')
    df.columns = df.columns.str.strip()

    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
    df = df.dropna(subset=['Ride Distance', 'Pickup Location', 'Drop Location'])

    return df

df = load_data()

# =========================
# GRAPH
# =========================
@st.cache_resource
def build_graph(df):
    G = nx.Graph()
    for _, row in df.iterrows():
        u = row['Pickup Location']
        v = row['Drop Location']
        d = row['Ride Distance']

        if G.has_edge(u, v):
            if d < G[u][v]['weight']:
                G[u][v]['weight'] = d
        else:
            G.add_edge(u, v, weight=d)
    return G

G = build_graph(df)

cities = sorted(set(df['Pickup Location']).union(set(df['Drop Location'])))

# =========================
# SESSION STATE (for buttons)
# =========================
if "start" not in st.session_state:
    st.session_state.start = cities[0]

if "goal" not in st.session_state:
    st.session_state.goal = cities[1]

# =========================
# UI
# =========================
col1, col2 = st.columns(2)

start = col1.selectbox("🟢 Source", cities, index=cities.index(st.session_state.start))
goal  = col2.selectbox("🔴 Destination", cities, index=cities.index(st.session_state.goal))

# =========================
# BUTTONS
# =========================
b1, b2, b3 = st.columns(3)

if b1.button("🔄 Swap"):
    st.session_state.start, st.session_state.goal = goal, start
    st.rerun()

if b2.button("🧹 Clear"):
    st.session_state.start = cities[0]
    st.session_state.goal = cities[1]
    st.rerun()

# =========================
# EVENTS (TRAFFIC)
# =========================
def generate_events():
    emap = {}
    for u, v in G.edges():
        r = random.random()
        if r < 0.08:
            emap[(u, v)] = 'BLOCK'
        elif r < 0.25:
            emap[(u, v)] = 'TRAFFIC'
        else:
            emap[(u, v)] = 'CLEAR'
    return emap

# =========================
# FIND ROUTE
# =========================
if b3.button("🚀 Find Route"):

    if start == goal:
        st.warning("⚠️ Same source and destination")
        st.stop()

    with st.spinner("⚡ Finding best route..."):

        event_map = generate_events()
        temp_G = G.copy()

        # apply traffic
        for (u, v), evt in event_map.items():
            if evt == 'BLOCK':
                if temp_G.has_edge(u, v):
                    temp_G.remove_edge(u, v)
            elif evt == 'TRAFFIC':
                temp_G[u][v]['weight'] *= 1.5

        try:
            path = nx.shortest_path(temp_G, start, goal, weight='weight')
            dist = nx.shortest_path_length(temp_G, start, goal, weight='weight')
        except:
            st.error("❌ No path available")
            st.stop()

    # =========================
    # RESULT
    # =========================
    st.success("✅ Route Found")

    colA, colB, colC = st.columns(3)
    colA.metric("📏 Distance", f"{dist:.2f} km")
    colB.metric("🛑 Stops", len(path)-1)
    colC.metric("⏱️ Time", f"{(dist/40)*60:.0f} mins")

    st.write("### 📍 Route Path")
    st.write(" ➝ ".join(path))

    # =========================
    # MAP (REALISTIC STYLE)
    # =========================
    coords = {city: (random.uniform(20, 28), random.uniform(70, 88)) for city in cities}

    m = folium.Map(location=coords[start], zoom_start=6, tiles="CartoDB positron")

    # draw traffic edges
    for (u, v), evt in event_map.items():
        if evt == 'BLOCK':
            continue

        color = "green"
        if evt == 'TRAFFIC':
            color = "orange"

        folium.PolyLine([coords[u], coords[v]], color=color, weight=2).add_to(m)

    # optimal path
    route_coords = [coords[c] for c in path]
    folium.PolyLine(route_coords, color="blue", weight=6).add_to(m)

    folium.Marker(coords[start], tooltip="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coords[goal], tooltip="End", icon=folium.Icon(color="red")).add_to(m)

    st_folium(m, width=1000, height=500)

    # =========================
    # EXTRA INFO
    # =========================
    st.write("### 🚦 Traffic Summary")

    total_edges = len(event_map)
    traffic = sum(1 for v in event_map.values() if v == 'TRAFFIC')
    blocked = sum(1 for v in event_map.values() if v == 'BLOCK')

    st.write(f"Traffic Roads: {traffic}")
    st.write(f"Blocked Roads: {blocked}")
    st.write(f"Clear Roads: {total_edges - traffic - blocked}")
