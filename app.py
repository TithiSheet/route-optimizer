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
# GRAPH
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
# SIDEBAR GRAPH (ALWAYS)
# =========================
st.sidebar.title("📊 Network Graph")

pos = nx.spring_layout(G, seed=42)

fig, ax = plt.subplots(figsize=(5,4))
nx.draw(G, pos, node_size=50, ax=ax)
ax.axis("off")

st.sidebar.pyplot(fig)

# =========================
# SESSION STATE
# =========================
if "map" not in st.session_state:
    st.session_state.map = None

if "path" not in st.session_state:
    st.session_state.path = None

# =========================
# UI
# =========================
col1, col2 = st.columns(2)

start = col1.selectbox("🟢 Source", cities)
goal  = col2.selectbox("🔴 Destination", cities)

# =========================
# BUTTONS
# =========================
b1, b2, b3 = st.columns(3)

if b1.button("🔄 Swap"):
    start, goal = goal, start

if b2.button("🧹 Clear"):
    st.session_state.map = None
    st.session_state.path = None

# =========================
# FIND ROUTE
# =========================
if b3.button("🚀 Find Route"):

    temp_G = G.copy()

    try:
        path = nx.shortest_path(temp_G, start, goal, weight='weight')
        dist = nx.shortest_path_length(temp_G, start, goal, weight='weight')
    except:
        st.error("❌ No path found")
        st.stop()

    # store in session
    st.session_state.path = path

    # =========================
    # MAP
    # =========================
    coords = {city: (random.uniform(20, 28), random.uniform(70, 88)) for city in cities}

    m = folium.Map(location=coords[start], zoom_start=6)

    route_coords = [coords[c] for c in path]

    folium.PolyLine(route_coords, color="blue", weight=6).add_to(m)

    folium.Marker(coords[start], tooltip="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coords[goal], tooltip="End", icon=folium.Icon(color="red")).add_to(m)

    st.session_state.map = m

    # RESULT
    st.success("✅ Route Found")
    st.write(f"📏 Distance: {dist:.2f} km")
    st.write(f"🛑 Stops: {len(path)-1}")

# =========================
# 🔥 ALWAYS SHOW MAP
# =========================
st.subheader("🗺️ Route Map")

if st.session_state.map:
    st_folium(st.session_state.map, width=1000, height=500)
else:
    # default empty map (ALWAYS visible)
    default_map = folium.Map(location=[22.5, 78.9], zoom_start=5)
    st_folium(default_map, width=1000, height=500)
