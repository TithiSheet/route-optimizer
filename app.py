import streamlit as st
import pandas as pd
import random
import networkx as nx
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

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

cities = sorted(set(df['Pickup Location']).union(set(df['Drop Location'])))

# =========================
# BUILD GRAPH
# =========================
@st.cache_resource
def build_graph(df):
    G = nx.Graph()
    for _, row in df.iterrows():
        u, v, d = row['Pickup Location'], row['Drop Location'], row['Ride Distance']
        G.add_edge(u, v, weight=d)
    return G

G = build_graph(df)

# =========================
# UI
# =========================
col1, col2 = st.columns(2)
start = col1.selectbox("🟢 Source", cities)
goal  = col2.selectbox("🔴 Destination", cities)

# =========================
# FAKE REALISTIC COORDS (INDIA RANGE)
# =========================
coords = {city: (random.uniform(18, 30), random.uniform(72, 88)) for city in cities}

# =========================
# EVENTS
# =========================
EVENTS = {
    'CLEAR': ('green', 1),
    'TRAFFIC': ('orange', 1.5),
    'BLOCKAGE': ('red', None)
}

def generate_events():
    emap = {}
    for u, v in G.edges():
        r = random.random()
        if r < 0.1:
            emap[(u, v)] = 'BLOCKAGE'
        elif r < 0.3:
            emap[(u, v)] = 'TRAFFIC'
        else:
            emap[(u, v)] = 'CLEAR'
    return emap

# =========================
# BUTTON
# =========================
if st.button("🚀 Find Smart Route"):

    event_map = generate_events()
    temp_G = G.copy()

    # Apply traffic
    for (u, v), evt in event_map.items():
        if evt == 'BLOCKAGE':
            if temp_G.has_edge(u, v):
                temp_G.remove_edge(u, v)
        elif evt == 'TRAFFIC':
            temp_G[u][v]['weight'] *= 1.5

    try:
        path = nx.shortest_path(temp_G, start, goal, weight='weight')
        dist = nx.shortest_path_length(temp_G, start, goal, weight='weight')
    except:
        st.error("❌ No route found")
        st.stop()

    # =========================
    # RESULT PANEL
    # =========================
    st.success("✅ Route Found")

    colA, colB, colC = st.columns(3)
    colA.metric("Distance", f"{dist:.2f} km")
    colB.metric("Stops", len(path)-1)
    colC.metric("Time", f"{(dist/40)*60:.0f} mins")

    st.write("### 📍 Route Path")
    st.write(" ➝ ".join(path))

    # =========================
    # MAP (Google-like)
    # =========================
    m = folium.Map(location=coords[start], zoom_start=6, tiles="CartoDB positron")

    # Draw edges with traffic color
    for (u, v), evt in event_map.items():
        if evt == 'BLOCKAGE':
            continue
        color = EVENTS[evt][0]
        folium.PolyLine([coords[u], coords[v]], color=color, weight=2).add_to(m)

    # Highlight optimal path
    route_coords = [coords[c] for c in path]
    folium.PolyLine(route_coords, color="blue", weight=6).add_to(m)

    # Markers
    folium.Marker(coords[start], tooltip="Start", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coords[goal], tooltip="Goal", icon=folium.Icon(color="red")).add_to(m)

    st_folium(m, width=900, height=500)

    # =========================
    # GRAPH (STAYS)
    # =========================
    st.write("### 📊 Network Graph View")

    pos = nx.spring_layout(G, seed=42)

    plt.figure(figsize=(10, 7))
    ax = plt.gca()
    ax.set_facecolor("#0d0d1a")

    for (u, v), evt in event_map.items():
        if evt == 'BLOCKAGE':
            continue
        color = EVENTS[evt][0]
        nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], edge_color=color, width=1.5)

    # highlight path
    edges = list(zip(path, path[1:]))
    nx.draw_networkx_edges(G, pos, edgelist=edges, edge_color="cyan", width=3)

    nx.draw_networkx_nodes(G, pos, node_color="white", node_size=200)
    nx.draw_networkx_labels(G, pos, font_size=6)

    plt.title("Graph View (Traffic + Path)", color="white")
    plt.axis("off")

    st.pyplot(plt)

    # =========================
    # LEGEND
    # =========================
    st.write("### 🧾 Legend")
    st.markdown("""
    - 🟢 Clear Route  
    - 🟠 Traffic  
    - 🔴 Blocked  
    - 🔵 Optimal Path  
    """)
