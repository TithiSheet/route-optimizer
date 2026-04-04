import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

st.title("🤖 Smart Route Optimizer (Dynamic + Real Dataset)")

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
        u = row['Pickup Location']
        v = row['Drop Location']
        d = row['Ride Distance']

        if pd.notna(d):
            if G.has_edge(u, v):
                if d < G[u][v]['weight']:
                    G[u][v]['weight'] = d
            else:
                G.add_edge(u, v, weight=d)

    return G

G = build_graph(df)

# =========================
# GET DIRECT DISTANCE
# =========================
def get_direct_distance(u, v):
    direct = df[(df['Pickup Location']==u) & (df['Drop Location']==v)]
    reverse = df[(df['Pickup Location']==v) & (df['Drop Location']==u)]

    if not direct.empty and pd.notna(direct.iloc[0]['Ride Distance']):
        return direct.iloc[0]['Ride Distance']

    if not reverse.empty and pd.notna(reverse.iloc[0]['Ride Distance']):
        return reverse.iloc[0]['Ride Distance']

    return None

# =========================
# DYNAMIC CONDITIONS
# =========================
def apply_dynamic(G):
    temp = G.copy()
    events = {}

    for u, v in list(temp.edges()):
        r = random.random()

        if r < 0.10:
            temp.remove_edge(u, v)
            events[(u, v)] = "🚧 BLOCKED"

        elif r < 0.30:
            temp[u][v]['weight'] *= 1.5
            events[(u, v)] = "🚦 TRAFFIC"

        elif r < 0.45:
            temp[u][v]['weight'] *= 1.3
            events[(u, v)] = "🌧 WEATHER"

        elif r < 0.60:
            temp[u][v]['weight'] *= 1.2
            events[(u, v)] = "🛠 ROADWORK"

        else:
            events[(u, v)] = "✅ CLEAR"

    return temp, events

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

    temp_G, events = apply_dynamic(G)

    direct_dist = get_direct_distance(start, goal)

    use_direct = False

    # Check if direct road exists in dynamic graph
    if direct_dist is not None and temp_G.has_edge(start, goal):
        use_direct = True

    # =========================
    # ROUTE LOGIC
    # =========================
    if use_direct:
        path = [start, goal]
        st.info("📊 Using Direct Route (No Blockage)")
    else:
        try:
            path = nx.shortest_path(temp_G, start, goal, weight='weight')
            st.info("🤖 Using Alternate Route (Dynamic Conditions Applied)")
        except:
            st.error("❌ No route available due to blockages")
            st.stop()

    # =========================
    # STEP DISTANCE
    # =========================
    total_distance = 0
    step_details = []

    for i in range(len(path)-1):
        u = path[i]
        v = path[i+1]

        d = get_direct_distance(u, v)

        if d is None:
            d = temp_G[u][v]['weight']

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

    # Step view
    st.write("### 🧭 Step-by-Step Route")

    for u, v, d in step_details:
        st.write(f"➡ {u} → {v} = {d:.2f} km")

    # =========================
    # MAP
    # =========================
    random.seed(42)
    coords = {city: (random.uniform(20, 28), random.uniform(70, 88)) for city in cities}

    m = folium.Map(location=coords[start], zoom_start=6)

    # draw full graph
    for u, v in G.edges():
        folium.PolyLine(
            [coords[u], coords[v]],
            color="gray",
            weight=1,
            opacity=0.3
        ).add_to(m)

    # draw route with dynamic colors
    for u, v, d in step_details:
        event = events.get((u, v), "CLEAR")

        color = "blue"
        if "BLOCKED" in event:
            color = "red"
        elif "TRAFFIC" in event:
            color = "orange"
        elif "WEATHER" in event:
            color = "purple"
        elif "ROADWORK" in event:
            color = "black"

        folium.PolyLine(
            [coords[u], coords[v]],
            color=color,
            weight=6,
            tooltip=f"{u} → {v} ({d:.2f} km) {event}"
        ).add_to(m)

    # markers
    for city in path:
        folium.Marker(coords[city], popup=city).add_to(m)

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
