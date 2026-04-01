import streamlit as st
import pandas as pd
import networkx as nx
import random
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("🗺️ Smart Route Optimizer (Pro)")

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

cities = sorted(set(df['Pickup Location']).union(set(df['Drop Location'])))

# =========================
# BUILD GRAPH
# =========================
@st.cache_resource
def build_graph(df):
    G = nx.Graph()
    for _, row in df.iterrows():
        u, v, d = row['Pickup Location'], row['Drop Location'], row['Ride Distance']
        if G.has_edge(u, v):
            if d < G[u][v]['weight']:
                G[u][v]['weight'] = d
        else:
            G.add_edge(u, v, weight=d)
    return G

G = build_graph(df)

# =========================
# SIDEBAR (GRAPH ALWAYS)
# =========================
st.sidebar.title("📊 Network Graph (Always Visible)")

pos = nx.spring_layout(G, seed=42)

fig, ax = plt.subplots(figsize=(5, 4))
ax.set_facecolor("#0d0d1a")

nx.draw_networkx_nodes(G, pos, node_size=80, node_color="#00BFFF", ax=ax)
nx.draw_networkx_edges(G, pos, alpha=0.3, ax=ax)
nx.draw_networkx_labels(G, pos, font_size=5, ax=ax)

ax.set_title("City Network", color="white")
ax.axis("off")

st.sidebar.pyplot(fig)

# =========================
# SESSION STATE
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
        st.error("❌ No path found")
        st.stop()

    # =========================
    # RESULT
    # =========================
    st.success("✅ Route Found")

    colA, colB, colC = st.columns(3)
    colA.metric("Distance", f"{dist:.2f} km")
    colB.metric("Stops", len(path)-1)
    colC.metric("Time", f"{(dist/40)*60:.0f} mins")

    st.write("### 📍 Path")
    st.write(" ➝ ".join(path))

    # =========================
    # REAL MAP STYLE
    # =========================
    coords = {city: (random.uniform(20, 28), random.uniform(70, 88)) for city in cities}

    m = folium.Map(location=coords[start], zoom_start=6, tiles="OpenStreetMap")

    # traffic edges
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

    # markers
    folium.Marker(coords[start], tooltip="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coords[goal], tooltip="End", icon=folium.Icon(color="red")).add_to(m)

    st_folium(m, width=1000, height=500)
