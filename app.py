import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

st.title("🌍 Smart Route Optimizer (Dynamic AI Routing)")

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
# DIRECT DISTANCE CHECK
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
# APPLY DYNAMIC CONDITIONS
# =========================
def apply_dynamic_conditions(G):
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

    temp_G, events = apply_dynamic_conditions(G)

    direct_distance = get_direct_distance(start, goal)

    # =========================
    # CHECK DIRECT ROUTE
    # =========================
    use_direct = False

    if direct_distance is not None:
        if temp_G.has_edge(start, goal):
            use_direct = True

    # =========================
    # PATH SELECTION
    # =========================
    if use_direct:
        path = [start, goal]
        st.info("📊 Direct route used (no blockage)")

    else:
        try:
            path = nx.shortest_path(temp_G, start, goal, weight='weight')
            st.warning("⚠️ Direct route unavailable → Alternate path used")
        except:
            st.error("❌ No route available")
            st.stop()

    # =========================
    # CALCULATE DISTANCE
    # =========================
    total_distance = 0
    steps = []

    for i in range(len(path)-1):
        u, v = path[i], path[i+1]

        if temp_G.has_edge(u, v):
            d = temp_G[u][v]['weight']
        else:
            d = 0

        total_distance += d
        steps.append((u, v, d, events.get((u, v), events.get((v, u), "UNKNOWN"))))

    # =========================
    # OUTPUT
    # =========================
    st.success("✅ Route Found")
    st.write(f"📏 Total Distance: {total_distance:.2f} km")
    st.write(f"🛑 Stops: {len(path)-1}")

    st.write("### 📍 Route Path")
    st.write(" ➝ ".join(path))

    # =========================
    # STEP DETAILS WITH EVENTS 🔥
    # =========================
    st.write("### 🧭 Step-by-Step Route with Conditions")

    for u, v, d, event in steps:
        st.write(f"➡ {u} → {v} = {d:.2f} km ({event})")

    # =========================
    # MAP
    # =========================
    random.seed(42)
    coords = {city: (random.uniform(20, 28), random.uniform(70, 88)) for city in cities}

    m = folium.Map(location=coords[start], zoom_start=6)

    # draw route with colors
    for u, v, d, event in steps:

        if "BLOCKED" in event:
            color = "red"
        elif "TRAFFIC" in event:
            color = "orange"
        elif "WEATHER" in event:
            color = "purple"
        elif "ROADWORK" in event:
            color = "blue"
        else:
            color = "green"

        folium.PolyLine(
            [coords[u], coords[v]],
            color=color,
            weight=6,
            tooltip=f"{u} → {v} ({event})"
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
