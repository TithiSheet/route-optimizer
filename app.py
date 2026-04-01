import streamlit as st
import pandas as pd
import networkx as nx
import folium
from streamlit_folium import st_folium
import requests
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("🗺️ Smart Route Optimizer (Real Road Version)")

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
# GRAPH (LEFT SIDE ALWAYS)
# =========================
st.sidebar.title("📊 Network Graph")

@st.cache_resource
def build_graph(df):
    G = nx.Graph()
    for _, row in df.iterrows():
        G.add_edge(row['Pickup Location'], row['Drop Location'])
    return G

G = build_graph(df)

fig, ax = plt.subplots(figsize=(3,3))
pos = nx.spring_layout(G, seed=42)
nx.draw(G, pos, node_size=20, ax=ax)
ax.set_title("Cities Network")
st.sidebar.pyplot(fig)

# =========================
# CITY LIST
# =========================
cities = sorted(set(df['Pickup Location']).union(set(df['Drop Location'])))

# =========================
# UI
# =========================
col1, col2 = st.columns(2)
start = col1.selectbox("🟢 Source", cities)
goal  = col2.selectbox("🔴 Destination", cities)

c1, c2, c3 = st.columns(3)

if c1.button("🔄 Swap"):
    start, goal = goal, start

if c2.button("🧹 Clear"):
    st.rerun()

run = c3.button("🚀 Find Route")

# =========================
# GET COORDS (FAKE CENTER INDIA)
# =========================
coords = {city: (28 + hash(city)%5, 77 + hash(city)%5) for city in cities}

# =========================
# ROUTE LOGIC
# =========================
if run:
    try:
        path = nx.shortest_path(G, start, goal)
        dist = nx.shortest_path_length(G, start, goal)
    except:
        st.error("❌ No path found")
        st.stop()

    st.success("✅ Route Found")

    st.write(f"📏 Distance: {dist:.2f} km")
    st.write(f"🛑 Stops: {len(path)-1}")

    # =========================
    # REAL ROAD ROUTE USING OSRM
    # =========================
    route_coords = []

    for i in range(len(path)-1):
        s = coords[path[i]]
        d = coords[path[i+1]]

        url = f"http://router.project-osrm.org/route/v1/driving/{s[1]},{s[0]};{d[1]},{d[0]}?overview=full&geometries=geojson"

        res = requests.get(url).json()

        if res.get("routes"):
            geometry = res["routes"][0]["geometry"]["coordinates"]
            route_coords += [(lat, lon) for lon, lat in geometry]

    # =========================
    # MAP (STABLE)
    # =========================
    m = folium.Map(location=coords[start], zoom_start=6)

    if route_coords:
        folium.PolyLine(route_coords, color="blue", weight=5).add_to(m)

    folium.Marker(coords[start], popup=f"Start: {start}", icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coords[goal], popup=f"End: {goal}", icon=folium.Icon(color="red")).add_to(m)

    st_folium(m, width=900, height=500)

else:
    st.info("Click Find Route")
