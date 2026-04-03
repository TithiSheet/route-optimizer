import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

st.title("🌍 Smart Route Optimizer")

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
'''@st.cache_resource
def build_graph(df):
    G = nx.Graph()
    for _, row in df.iterrows():
        u, v, d = row['Pickup Location'], row['Drop Location'], row['Ride Distance']
        if G.has_edge(u, v):
            if d < G[u][v]['weight']:
                G[u][v]['weight'] = d
        else:
            G.add_edge(u, v, weight=d)
    return G'''

@st.cache_resource
def build_graph(df):
    G = nx.Graph()
    # 🔥 take minimum distance for each pair
    grouped = df.groupby(['Pickup Location', 'Drop Location'])['Ride Distance'].min().reset_index()
    for _, row in grouped.iterrows():
        u = row['Pickup Location']
        v = row['Drop Location']
        d = row['Ride Distance']
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
#if st.button("🛣️ Find Route"):

    #try:
        #path = nx.shortest_path(G, start, goal, weight='weight')
        #dist = nx.shortest_path_length(G, start, goal, weight='weight')
    #except:
        #st.error("❌ No path found")
        #st.stop()

    #st.session_state.path = path
    #st.session_state.distance = dist
    #st.session_state.stops = len(path) - 1'''

if st.button("🛣️ Find Route"):
    try:
        path = nx.shortest_path(G, start, goal, weight='weight')
    except:
        st.error("❌ No path found")
        st.stop()
    # 🔥 CALCULATE REAL DISTANCE FROM DATASET
    total_distance = 0
    segment_details = []
    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]
        d = G[u][v]['weight']
        total_distance += d
        segment_details.append(f"{u} → {v} = {d:.2f} km")
    # SAVE
    st.session_state.path = path
    st.session_state.distance = total_distance
    st.session_state.stops = len(path) - 1
    # SHOW DEBUG (OPTIONAL)
    st.write("### 📊 Segment Distances")
    for s in segment_details:
        st.write(s)

    # =========================
    # FIXED COORDS (CONSISTENT)
    # =========================
    random.seed(42)
    coords = {city: (random.uniform(20, 28), random.uniform(70, 88)) for city in cities}

    # =========================
    # MAP
    # =========================
    m = folium.Map(location=coords[start], zoom_start=6)

    # 🔥 DRAW FULL GRAPH (LIGHT)
    for u, v in G.edges():
        folium.PolyLine(
            [coords[u], coords[v]],
            color="gray",
            weight=1,
            opacity=0.3
        ).add_to(m)

    # 🔥 DRAW ROUTE PATH (MAIN)
    route_coords = [coords[c] for c in path]

    folium.PolyLine(
        route_coords,
        color="blue",
        weight=8,
        opacity=0.9
    ).add_to(m)

    # 🔥 MARKERS FOR EACH STEP
    for city in path:
        folium.CircleMarker(
            location=coords[city],
            radius=5,
            color="yellow",
            fill=True,
            fill_color="yellow",
            popup=city
        ).add_to(m)

    # START & END MARKERS
    folium.Marker(
        coords[start],
        popup=f"Start: {start}",
        tooltip=start,
        icon=folium.Icon(color="green")
    ).add_to(m)

    folium.Marker(
        coords[goal],
        popup=f"Destination: {goal}",
        tooltip=goal,
        icon=folium.Icon(color="red")
    ).add_to(m)

    # SAVE MAP HTML (NO BLINK)
    st.session_state.map_html = m._repr_html_()

# =========================
# RESULT (ALWAYS SHOW)
# =========================
if st.session_state.distance is not None:
    st.success("✅ Route Found")
    st.write(f"📏 Distance: {st.session_state.distance:.2f} km")
    st.write(f"🛑 Stops: {st.session_state.stops}")

    if st.session_state.path:
        st.write("### 📍 Route Path")
        st.write(" ➝ ".join(st.session_state.path))

# =========================
# MAP (ALWAYS SHOW)
# =========================
st.subheader("🗺️ Route Map")

if st.session_state.map_html:
    components.html(st.session_state.map_html, height=550)
else:
    default_map = folium.Map(location=[22.5, 78.9], zoom_start=5)
    components.html(default_map._repr_html_(), height=550)
