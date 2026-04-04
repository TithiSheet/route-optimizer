import streamlit as st
import pandas as pd
import networkx as nx
import random
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

st.title("🌍 Smart Route Optimizer (Dynamic Environment AI)")

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
# UI
# =========================
col1, col2 = st.columns(2)
start = col1.selectbox("🟢 Source", cities)
goal  = col2.selectbox("🔴 Destination", cities)

# =========================
# APPLY DYNAMIC CONDITIONS
# =========================
def apply_dynamic_conditions(G):
    temp = G.copy()
    events = {}

    for u, v in list(temp.edges()):
        r = random.random()

        if r < 0.1:
            temp.remove_edge(u, v)
            events[(u, v)] = "BLOCKED"

        elif r < 0.3:
            temp[u][v]['weight'] *= 1.5
            events[(u, v)] = "TRAFFIC"

        elif r < 0.45:
            temp[u][v]['weight'] *= 1.3
            events[(u, v)] = "WEATHER"

        elif r < 0.6:
            temp[u][v]['weight'] *= 1.2
            events[(u, v)] = "ROADWORK"

        else:
            events[(u, v)] = "CLEAR"

    return temp, events

# =========================
# BUTTON
# =========================
if st.button("🚀 Find Dynamic Route"):

    temp_G, events = apply_dynamic_conditions(G)

    try:
        path = nx.shortest_path(temp_G, start, goal, weight='weight')
        dist = nx.shortest_path_length(temp_G, start, goal, weight='weight')
    except:
        st.error("❌ No route available due to road block")
        st.stop()

    # =========================
    # RESULT
    # =========================
    st.success("✅ Route Found (Dynamic AI)")

    st.write(f"📏 Distance (Dynamic): {dist:.2f} km")
    st.write(f"🛑 Stops: {len(path)-1}")
    st.write("📍 Path:")
    st.write(" ➝ ".join(path))

    # =========================
    # GRAPH VISUALIZATION
    # =========================
    st.subheader("📊 Dynamic Graph View")

    fig, ax = plt.subplots(figsize=(8, 6))

    pos = nx.spring_layout(G, seed=42)

    edge_colors = []
    for u, v in G.edges():
        event = events.get((u, v)) or events.get((v, u))

        if event == "BLOCKED":
            edge_colors.append("red")
        elif event == "TRAFFIC":
            edge_colors.append("orange")
        elif event == "WEATHER":
            edge_colors.append("purple")
        elif event == "ROADWORK":
            edge_colors.append("yellow")
        else:
            edge_colors.append("green")

    nx.draw(
        G,
        pos,
        edge_color=edge_colors,
        node_color="skyblue",
        with_labels=True,
        node_size=500,
        font_size=7,
        ax=ax
    )

    # 🔥 Highlight chosen route
    path_edges = list(zip(path, path[1:]))
    nx.draw_networkx_edges(
        G,
        pos,
        edgelist=path_edges,
        edge_color="blue",
        width=3,
        ax=ax
    )

    st.pyplot(fig)

    # =========================
    # LEGEND
    # =========================
    st.subheader("⚡ Dynamic Conditions")

    st.write("🔴 Red = Blocked Road")
    st.write("🟠 Orange = Traffic")
    st.write("🟣 Purple = Bad Weather")
    st.write("🟡 Yellow = Road Work")
    st.write("🟢 Green = Clear Road")
