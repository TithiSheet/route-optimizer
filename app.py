import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

st.title("🤖 Smart Route Optimizer (Q-Learning + Dynamic AI)")

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
# DYNAMIC CONDITIONS
# =========================
def apply_conditions(G):
    temp = G.copy()
    events = {}

    for u, v in temp.edges():
        r = random.random()

        if r < 0.05:
            temp.remove_edge(u, v)
            events[(u, v)] = "BLOCKED"

        elif r < 0.20:
            temp[u][v]['weight'] *= 1.5
            events[(u, v)] = "TRAFFIC"

        elif r < 0.30:
            temp[u][v]['weight'] *= 1.3
            events[(u, v)] = "WEATHER"

        elif r < 0.40:
            temp[u][v]['weight'] *= 1.2
            events[(u, v)] = "ROADWORK"

        else:
            events[(u, v)] = "CLEAR"

    return temp, events

# =========================
# Q-LEARNING ROUTE
# =========================
def q_learning_route(G, start, goal, episodes=200):

    Q = {}

    for node in G.nodes():
        Q[node] = {n: 0 for n in G.neighbors(node)}

    alpha = 0.7
    gamma = 0.8
    epsilon = 0.2

    for _ in range(episodes):
        current = start

        while current != goal:
            neighbors = list(G.neighbors(current))
            if not neighbors:
                break

            if random.random() < epsilon:
                next_node = random.choice(neighbors)
            else:
                next_node = max(Q[current], key=Q[current].get)

            reward = -G[current][next_node]['weight']

            if next_node == goal:
                reward += 50  # reward for reaching goal

            Q[current][next_node] = Q[current][next_node] + alpha * (
                reward + gamma * max(Q[next_node].values(), default=0)
                - Q[current][next_node]
            )

            current = next_node

    # BUILD PATH
    path = [start]
    current = start

    while current != goal:
        if current not in Q or not Q[current]:
            break

        next_node = max(Q[current], key=Q[current].get)

        if next_node in path:
            break

        path.append(next_node)
        current = next_node

    return path

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

# =========================
# UI
# =========================
col1, col2 = st.columns(2)

start = col1.selectbox("🟢 Source", cities)
goal  = col2.selectbox("🔴 Destination", cities)

# =========================
# BUTTON
# =========================
if st.button("🚀 Find Smart AI Route"):

    temp_G, events = apply_conditions(G)

    direct = get_direct_distance(start, goal)

    if direct is not None:
        path = [start, goal]
        dist = direct
        reason = "📊 Direct dataset route"

    else:
        path = q_learning_route(temp_G, start, goal)

        dist = 0
        for i in range(len(path)-1):
            dist += temp_G[path[i]][path[i+1]]['weight']

        reason = "🤖 Q-Learning optimized route (dynamic conditions)"

    # =========================
    # OUTPUT
    # =========================
    st.success("✅ Smart Route Found")

    st.write(f"📏 Distance: {dist:.2f} km")
    st.write(f"🛑 Stops: {len(path)-1}")

    st.write("### 📍 Route Path")
    st.write(" ➝ ".join(path))

    st.info(reason)

    # =========================
    # SIMPLE MAP (FAST)
    # =========================
    random.seed(42)
    coords = {city: (random.uniform(20, 28), random.uniform(70, 88)) for city in cities}

    m = folium.Map(location=coords[start], zoom_start=6)

    route_coords = [coords[c] for c in path]

    folium.PolyLine(route_coords, color="blue", weight=6).add_to(m)

    folium.Marker(coords[start], icon=folium.Icon(color="green")).add_to(m)
    folium.Marker(coords[goal], icon=folium.Icon(color="red")).add_to(m)

    st.session_state.map_html = m._repr_html_()

# =========================
# MAP DISPLAY
# =========================
st.subheader("🗺️ Route Map")

if st.session_state.map_html:
    components.html(st.session_state.map_html, height=500)
else:
    m = folium.Map(location=[22.5, 78.9], zoom_start=5)
    components.html(m._repr_html_(), height=500)
