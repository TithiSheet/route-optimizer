import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

st.title("🌍 Smart Route Optimizer (Correct Distance)")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv("bookings3.csv", encoding="latin1", on_bad_lines='skip')

    df.columns = df.columns.str.strip()

    # Convert to numeric
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')

    # ❗ REMOVE NULL VALUES (IMPORTANT FIX)
    df = df.dropna(subset=['Ride Distance', 'Pickup Location', 'Drop Location'])

    return df

df = load_data()

if df.empty:
    st.error("❌ Dataset not loaded properly")
    st.stop()

cities = sorted(set(df['Pickup Location']).union(set(df['Drop Location'])))

# =========================
# BUILD GRAPH
# =========================
@st.cache_resource
def build_graph(df):
    G = nx.Graph()

    for _, row in df.iterrows():
        u = row['Pickup Location']
        v = row['Drop Location']
        d = row['Ride Distance']

        # Keep MIN distance if duplicate edge
        if G.has_edge(u, v):
            if d < G[u][v]['weight']:
                G[u][v]['weight'] = d
        else:
            G.add_edge(u, v, weight=d)

    return G

G = build_graph(df)

# =========================
# SESSION STATE
# =========================
if "map_html" not in st.session_state:
    st.session_state.map_html = None

if "distance" not in st.session_state:
    st.session_state.distance = None

if "stops" not in st.session_state:
    st.session_state.stops = None

if "path" not in st.session_state:
    st.session_state.path = None

# =========================
# UI
# =========================
col1, col2 = st.columns(2)

start = col1.selectbox("🟢 Source", cities)
goal  = col2.selectbox("🔴 Destination", cities)

# =========================
# BUTTON
# =========================
if st.button("🛣️ Find Route"):

    try:
        path = nx.shortest_path(G, start, goal, weight='weight')
        dist = nx.shortest_path_length(G, start, goal, weight='weight')
    except:
        st.error("❌ No path found")
        st.stop()

    st.session_state.path = path
    st.session_state.distance = dist
    st.session_state.stops = len(path) - 1

    # =========================
    # FIXED COORDS
    # =========================
    random.seed(42)
    coords = {city: (random.uniform(20, 28), random.uniform(70, 88)) for city in cities}

    # =========================
    # MAP
    # =========================
    m = folium.Map(location=coords[start], zoom_start=6)

    # Draw full graph
    for u, v in G.edges():
        folium.PolyLine(
            [coords[u], coords[v]],
            color="gray",
            weight=1,
            opacity=0.3
        ).add_to(m)

    # Draw route
    route_coords = [coords[c] for c in path]

    folium.PolyLine(
        route_coords,
        color="blue",
        weight=8,
        opacity=0.9
    ).add_to(m)

    # Markers
    for city in path:
        folium.CircleMarker(
            location=coords[city],
            radius=5,
            color="yellow",
            fill=True,
            fill_color="yellow",
            popup=city
        ).add_to(m)

    folium.Marker(
        coords[start],
        popup=f"Start: {start}",
        icon=folium.Icon(color="green")
    ).add_to(m)

    folium.Marker(
        coords[goal],
        popup=f"Destination: {goal}",
        icon=folium.Icon(color="red")
    ).add_to(m)

    # Save map
    st.session_state.map_html = m._repr_html_()

# =========================
# RESULT
# =========================
if st.session_state.distance is not None:
    st.success("✅ Route Found")

    st.write(f"📏 Distance: {st.session_state.distance:.2f} km")
    st.write(f"🛑 Stops: {st.session_state.stops}")

    if st.session_state.path:
        st.write("### 📍 Route Path")
        st.write(" ➝ ".join(st.session_state.path))

# =========================
# MAP DISPLAY
# =========================
st.subheader("🗺️ Route Map")

if st.session_state.map_html:
    components.html(st.session_state.map_html, height=550)
else:
    default_map = folium.Map(location=[22.5, 78.9], zoom_start=5)
    components.html(default_map._repr_html_(), height=550)
