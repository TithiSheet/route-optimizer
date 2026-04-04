import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import time
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

st.title("🚗 Smart Route Optimizer (With Animation)")

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
# GRAPH
# =========================
@st.cache_resource
def build_graph(df):
    G = nx.Graph()
    for _, row in df.iterrows():
        if pd.notna(row['Ride Distance']):
            G.add_edge(
                row['Pickup Location'],
                row['Drop Location'],
                weight=row['Ride Distance']
            )
    return G

G = build_graph(df)

# =========================
# DIRECT DISTANCE
# =========================
def get_direct_distance(u, v):
    row = df[(df['Pickup Location']==u) & (df['Drop Location']==v)]
    if not row.empty and pd.notna(row.iloc[0]['Ride Distance']):
        return row.iloc[0]['Ride Distance']

    row2 = df[(df['Pickup Location']==v) & (df['Drop Location']==u)]
    if not row2.empty and pd.notna(row2.iloc[0]['Ride Distance']):
        return row2.iloc[0]['Ride Distance']

    return None

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
            events[(u, v)] = "Blocked"

        elif r < 0.3:
            temp[u][v]['weight'] *= 1.5
            events[(u, v)] = "Traffic"

        elif r < 0.5:
            temp[u][v]['weight'] *= 1.3
            events[(u, v)] = "Weather"

        elif r < 0.7:
            temp[u][v]['weight'] *= 1.2
            events[(u, v)] = "Road Work"

        else:
            events[(u, v)] = "Clear"

    return temp, events

# =========================
# FORCE PATH
# =========================
def force_path(G, start, goal):
    try:
        mid = random.choice(list(G.nodes()))
        if mid == start or mid == goal:
            return nx.shortest_path(G, start, goal, weight='weight')

        p1 = nx.shortest_path(G, start, mid, weight='weight')
        p2 = nx.shortest_path(G, mid, goal, weight='weight')

        return p1[:-1] + p2
    except:
        return nx.shortest_path(G, start, goal, weight='weight')

# =========================
# DISTANCE
# =========================
def calc_distance(G, path, base=None):
    total = 0
    for i in range(len(path)-1):
        total += G[path[i]][path[i+1]]['weight']

    if base:
        total = max(total, base)

    return total

# =========================
# UI
# =========================
col1, col2 = st.columns(2)

start = col1.selectbox("🟢 Source", cities)
goal  = col2.selectbox("🔴 Destination", cities)

# =========================
# BUTTON
# =========================
if st.button("🚀 Start Route Animation"):

    base = get_direct_distance(start, goal)

    temp_G, events = apply_dynamic(G)

    if base:
        path = force_path(temp_G, start, goal)
        dist = calc_distance(temp_G, path, base)
    else:
        path = nx.shortest_path(temp_G, start, goal, weight='weight')
        dist = calc_distance(temp_G, path)

    st.success("✅ Route Found")

    st.write(f"📏 Distance: {dist:.2f} km")
    st.write(" ➝ ".join(path))

    # =========================
    # FIXED COORDS
    # =========================
    random.seed(42)
    coords = {city: (random.uniform(20, 28), random.uniform(70, 88)) for city in cities}

    # =========================
    # ANIMATION LOOP
    # =========================
    map_placeholder = st.empty()

    for i in range(len(path)):

        m = folium.Map(location=coords[start], zoom_start=6)

        # draw full route
        route_coords = [coords[c] for c in path]
        folium.PolyLine(route_coords, color="blue", weight=5).add_to(m)

        # moving marker 🚗
        folium.Marker(
            coords[path[i]],
            popup=f"🚗 At {path[i]}",
            icon=folium.Icon(color="red", icon="car")
        ).add_to(m)

        # start/end
        folium.Marker(coords[start], icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(coords[goal], icon=folium.Icon(color="black")).add_to(m)

        map_placeholder.write(m)

        time.sleep(1)  # speed control
