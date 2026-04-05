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
# DIRECT DISTANCE
# =========================
def get_direct_distance(start, goal):
    row = df[(df['Pickup Location']==start) & (df['Drop Location']==goal)]
    if not row.empty and pd.notna(row.iloc[0]['Ride Distance']):
        return row.iloc[0]['Ride Distance']

    row2 = df[(df['Pickup Location']==goal) & (df['Drop Location']==start)]
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
            temp[u][v]['weight'] *= 2.0
            events[(u, v)] = "🚧 Blocked"

        elif r < 0.3:
            temp[u][v]['weight'] *= 1.5
            events[(u, v)] = "🚦 Traffic"

        else:
            events[(u, v)] = "✅ Clear"

    return temp, events

# =========================
# FORCE INTERMEDIATE ROUTE
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
# DISTANCE CALCULATION
# =========================
def calculate_distance(G, path, base_distance=None):
    total = 0
    for i in range(len(path)-1):
        u, v = path[i], path[i+1]
        if G.has_edge(u, v):
            total += G[u][v]['weight']

    if base_distance:
        total = max(total, base_distance)

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
if st.button("🚀 Find Dynamic Route"):

    base_distance = get_direct_distance(start, goal)
    temp_G, events = apply_dynamic(G)

    if base_distance:
        path = force_path(temp_G, start, goal)
        dist = calculate_distance(temp_G, path, base_distance)
    else:
        path = nx.shortest_path(temp_G, start, goal, weight='weight')
        dist = calculate_distance(temp_G, path)

    st.success("✅ Route Found")

    st.write(f"📏 Total Distance: {dist:.2f} km")
    st.write(f"🛑 Stops: {len(path)-1}")

    st.write("### 📍 Route Path")
    st.write(" ➝ ".join(path))

    # =========================
    # MAP
    # =========================
    random.seed(42)
    coords = {city: (random.uniform(20, 28), random.uniform(70, 88)) for city in cities}

    m = folium.Map(location=coords[start], zoom_start=6)

    # GRAPH
    for u, v in temp_G.edges():
        event = events.get((u, v), "CLEAR")

        color = "green"
        if "Blocked" in event:
            color = "red"
        elif "Traffic" in event:
            color = "orange"

        folium.PolyLine([coords[u], coords[v]], color=color, weight=2).add_to(m)

    # ROUTE
    route_coords = [coords[c] for c in path]
    folium.PolyLine(route_coords, color="black", weight=6).add_to(m)

    # =========================
    # MARKERS (UPDATED 🎯)
    # =========================

    # Source (Green)
    folium.Marker(
        coords[start],
        popup=f"Start: {start}",
        icon=folium.Icon(color="green")
    ).add_to(m)

    # Destination (Red)
    folium.Marker(
        coords[goal],
        popup=f"End: {goal}",
        icon=folium.Icon(color="red")
    ).add_to(m)

    # Intermediate (Yellow)
    for city in path[1:-1]:
        folium.CircleMarker(
            location=coords[city],
            radius=6,
            color="yellow",
            fill=True,
            fill_color="yellow",
            popup=city
        ).add_to(m)

    # =========================
    # LEGEND
    # =========================
    legend_html = """
    <div style="
        position: fixed;
        bottom: 50px;
        left: 50px;
        width: 220px;
        background-color: white;
        border:2px solid grey;
        z-index:9999;
        padding:10px;
    ">
    <b>🧭 Legend</b><br>
    🟢 Source<br>
    🔴 Destination<br>
    🟡 Intermediate<br>
    🔴 Blocked<br>
    🟠 Traffic<br>
    🟢 Clear<br>
    ⚫ Route Path
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend_html))

    components.html(m._repr_html_(), height=550)
