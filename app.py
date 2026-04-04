import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

st.title("🌍 Smart Route Optimizer (Accurate + Step View)")

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
# BUILD GRAPH (CORRECT)
# =========================
@st.cache_resource
def build_graph(df):
    G = nx.Graph()

    for _, row in df.iterrows():
        u = row['Pickup Location']
        v = row['Drop Location']
        d = row['Ride Distance']

        # NULL handling
        if pd.isna(d):
            continue

        if G.has_edge(u, v):
            if d < G[u][v]['weight']:
                G[u][v]['weight'] = d
        else:
            G.add_edge(u, v, weight=d)

    return G

G = build_graph(df)

# =========================
# GET EDGE DISTANCE FROM DATASET
# =========================
def get_edge_distance(u, v):
    direct = df[(df['Pickup Location']==u) & (df['Drop Location']==v)]
    reverse = df[(df['Pickup Location']==v) & (df['Drop Location']==u)]

    if not direct.empty and pd.notna(direct.iloc[0]['Ride Distance']):
        return direct.iloc[0]['Ride Distance']

    if not reverse.empty and pd.notna(reverse.iloc[0]['Ride Distance']):
        return reverse.iloc[0]['Ride Distance']

    return None

# =========================
# UI
# =========================
col1, col2 = st.columns(2)

start = col1.selectbox("🟢 Source", cities)
goal  = col2.selectbox("🔴 Destination", cities)

# =========================
# BUTTON
# =========================
if st.button("🚀 Find Route"):

    try:
        path = nx.shortest_path(G, start, goal, weight='weight')
    except:
        st.error("❌ No path found")
        st.stop()

    # =========================
    # CALCULATE DISTANCE STEPWISE
    # =========================
    total_distance = 0
    step_details = []

    for i in range(len(path)-1):
        u = path[i]
        v = path[i+1]

        d = get_edge_distance(u, v)

        if d is None:
            d = G[u][v]['weight']

        total_distance += d
        step_details.append((u, v, d))

    # =========================
    # OUTPUT
    # =========================
    st.success("✅ Route Found")

    st.write(f"📏 Total Distance: {total_distance:.2f} km")
    st.write(f"🛑 Stops: {len(path)-1}")

    st.write("### 📍 Route Path")
    st.write(" ➝ ".join(path))

    # =========================
    # STEP BY STEP (IMPORTANT 🔥)
    # =========================
    st.write("### 🧭 Step-by-Step Route")

    for u, v, d in step_details:
        st.write(f"➡ {u} → {v} = {d:.2f} km")

    # =========================
    # MAP
    # =========================
    random.seed(42)
    coords = {city: (random.uniform(20, 28), random.uniform(70, 88)) for city in cities}

    m = folium.Map(location=coords[start], zoom_start=6)

    # draw full graph light
    for u, v in G.edges():
        folium.PolyLine(
            [coords[u], coords[v]],
            color="gray",
            weight=1,
            opacity=0.3
        ).add_to(m)

    # draw route
    for u, v, d in step_details:
        folium.PolyLine(
            [coords[u], coords[v]],
            color="blue",
            weight=6,
            tooltip=f"{u} → {v} ({d:.2f} km)"
        ).add_to(m)

    # markers
    for city in path:
        folium.CircleMarker(
            location=coords[city],
            radius=5,
            color="yellow",
            fill=True,
            fill_color="yellow",
            popup=city
        ).add_to(m)

    folium.Marker(coords[start], icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coords[goal], icon=folium.Icon(color="red")).add_to(m)

    st.session_state.map_html = m._repr_html_()

# =========================
# MAP DISPLAY
# =========================
st.subheader("🗺️ Route Map")

if "map_html" in st.session_state and st.session_state.map_html:
    components.html(st.session_state.map_html, height=550)
else:
    m = folium.Map(location=[22.5, 78.9], zoom_start=5)
    components.html(m._repr_html_(), height=550)
