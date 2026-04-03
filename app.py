import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
from geopy.geocoders import Nominatim
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

st.title("🌍 Smart Route Optimizer (Dynamic + Real Map)")

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
            if G.has_edge(u, v):
                if d < G[u][v]['weight']:
                    G[u][v]['weight'] = d
            else:
                G.add_edge(u, v, weight=d)
    return G

G = build_graph(df)

# =========================
# REAL COORDINATES (OpenStreetMap)
# =========================
geolocator = Nominatim(user_agent="route_app")

@st.cache_data
def get_coordinates(city):
    try:
        location = geolocator.geocode(city + ", India")
        return (location.latitude, location.longitude)
    except:
        return (22.5, 78.9)  # fallback

coords = {city: get_coordinates(city) for city in cities}

# =========================
# DYNAMIC CONDITIONS
# =========================
def apply_dynamic_conditions(G):
    temp = G.copy()
    events = {}

    for u, v in list(temp.edges()):
        r = random.random()

        if r < 0.05:
            temp.remove_edge(u, v)
            events[(u, v)] = "🚧 BLOCKED"

        elif r < 0.20:
            temp[u][v]['weight'] *= 1.5
            events[(u, v)] = "🚦 TRAFFIC"

        elif r < 0.30:
            temp[u][v]['weight'] *= 1.3
            events[(u, v)] = "🌧 WEATHER"

        elif r < 0.40:
            temp[u][v]['weight'] *= 1.2
            events[(u, v)] = "🛠 ROAD WORK"

        else:
            events[(u, v)] = "✅ CLEAR"

    return temp, events

# =========================
# DIRECT DISTANCE CHECK
# =========================
def get_direct_distance(start, goal):
    direct = df[(df['Pickup Location']==start) & (df['Drop Location']==goal)]
    reverse = df[(df['Pickup Location']==goal) & (df['Drop Location']==start)]

    if not direct.empty and pd.notna(direct.iloc[0]['Ride Distance']):
        return direct.iloc[0]['Ride Distance']

    if not reverse.empty and pd.notna(reverse.iloc[0]['Ride Distance']):
        return reverse.iloc[0]['Ride Distance']

    return None

# =========================
# SESSION STATE
# =========================
if "map_html" not in st.session_state:
    st.session_state.map_html = None

if "distance" not in st.session_state:
    st.session_state.distance = None

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
if st.button("🚀 Find Smart Route"):

    # Apply dynamic conditions
    temp_G, events = apply_dynamic_conditions(G)

    direct_distance = get_direct_distance(start, goal)

    # CASE 1: DIRECT
    if direct_distance is not None:
        path = [start, goal]
        dist = direct_distance
        reason = "Direct dataset route used"

    else:
        # CASE 2: DYNAMIC GRAPH
        try:
            path = nx.shortest_path(temp_G, start, goal, weight='weight')

            dist = 0
            for i in range(len(path)-1):
                dist += temp_G[path[i]][path[i+1]]['weight']

            reason = "Dynamic rerouting applied (traffic/blocks)"

        except:
            st.error("❌ No route available")
            st.stop()

    # SAVE
    st.session_state.path = path
    st.session_state.distance = dist

    # =========================
    # RESULT
    # =========================
    st.success("✅ Smart Route Found")
    st.write(f"📏 Distance: {dist:.2f} km")
    st.write(f"🛑 Stops: {len(path)-1}")

    st.write("### 📍 Route Path")
    st.write(" ➝ ".join(path))

    # 👉 Explanation
    st.info(f"🧠 {reason}")

    # =========================
    # MAP (REAL)
    # =========================
    m = folium.Map(location=coords[start], zoom_start=10)

    route_coords = [coords[c] for c in path]

    # Draw route
    folium.PolyLine(route_coords, color="blue", weight=6).add_to(m)

    # Markers
    for city in path:
        folium.Marker(
            coords[city],
            popup=city,
            icon=folium.Icon(color="blue")
        ).add_to(m)

    folium.Marker(coords[start], icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coords[goal], icon=folium.Icon(color="red")).add_to(m)

    st.session_state.map_html = m._repr_html_()

# =========================
# MAP DISPLAY (NO BLINK)
# =========================
st.subheader("🗺️ Real Route Map")

if st.session_state.map_html:
    components.html(st.session_state.map_html, height=550)
else:
    default_map = folium.Map(location=[22.5, 78.9], zoom_start=5)
    components.html(default_map._repr_html_(), height=550)
