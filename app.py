import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

st.title("🤖 Smart Route Optimizer (Forced AI Dynamic Routes)")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv("bookings3.csv", encoding="latin1", on_bad_lines='skip')
    df.columns = df.columns.str.strip()
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
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

        if pd.notna(d):
            G.add_edge(u, v, weight=d)

    return G

G = build_graph(df)

# =========================
# DYNAMIC CONDITIONS
# =========================
def apply_dynamic(G):
    temp = G.copy()
    events = {}

    for u, v in temp.edges():
        r = random.random()

        if r < 0.1:
            temp[u][v]['weight'] *= 2
            events[(u, v)] = "🚧 Blocked-like (very high cost)"

        elif r < 0.3:
            temp[u][v]['weight'] *= 1.5
            events[(u, v)] = "🚦 Traffic"

        elif r < 0.5:
            temp[u][v]['weight'] *= 1.3
            events[(u, v)] = "🌧 Weather"

        else:
            events[(u, v)] = "✅ Clear"

    return temp, events

# =========================
# FORCE INTERMEDIATE NODES
# =========================
def force_path(G, start, goal):

    try:
        # pick random intermediate node
        mid = random.choice(list(G.nodes()))

        # ensure it's not same
        if mid == start or mid == goal:
            return nx.shortest_path(G, start, goal, weight='weight')

        # build 2-step path
        path1 = nx.shortest_path(G, start, mid, weight='weight')
        path2 = nx.shortest_path(G, mid, goal, weight='weight')

        full_path = path1[:-1] + path2
        return full_path

    except:
        return nx.shortest_path(G, start, goal, weight='weight')

# =========================
# DISTANCE CALCULATION
# =========================
def calculate_distance(G, path):
    total = 0

    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]

        if G.has_edge(u, v):
            total += G[u][v]['weight']

    return total

# =========================
# UI
# =========================
col1, col2 = st.columns(2)

start = col1.selectbox("🟢 Source", cities)
goal = col2.selectbox("🔴 Destination", cities)

# =========================
# BUTTON
# =========================
if st.button("🚀 Find AI Dynamic Route"):

    temp_G, events = apply_dynamic(G)

    path = force_path(temp_G, start, goal)
    dist = calculate_distance(temp_G, path)

    # =========================
    # OUTPUT
    # =========================
    st.success("✅ AI Generated Dynamic Route")

    st.write(f"📏 Total Distance: {dist:.2f} km")
    st.write(f"🛑 Stops: {len(path)-1}")

    st.write("### 📍 Route Path")
    st.write(" ➝ ".join(path))

    # =========================
    # STEP DISTANCE
    # =========================
    st.write("### 🧭 Step-by-Step Distance")

    for i in range(len(path)-1):
        u, v = path[i], path[i+1]

        if temp_G.has_edge(u, v):
            d = temp_G[u][v]['weight']
            st.write(f"➡ {u} → {v} = {d:.2f} km")

    # =========================
    # MAP
    # =========================
    random.seed(42)
    coords = {city: (random.uniform(20, 28), random.uniform(70, 88)) for city in cities}

    m = folium.Map(location=coords[start], zoom_start=6)

    # draw full graph (light)
    for u, v in temp_G.edges():
        folium.PolyLine([coords[u], coords[v]], color="gray", weight=1, opacity=0.2).add_to(m)

    # route path
    route_coords = [coords[c] for c in path]
    folium.PolyLine(route_coords, color="blue", weight=6).add_to(m)

    # markers
    for city in path:
        folium.Marker(coords[city], popup=city).add_to(m)

    components.html(m._repr_html_(), height=500)
