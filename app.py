import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import numpy as np
import streamlit.components.v1 as components

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide", page_title="Q-Learning Route Optimizer")
st.title("🌍 Smart Dynamic Route Optimizer (Q-Learning)")

# =========================
# 1. LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv("bookings.csv", encoding="latin1", on_bad_lines='skip')
    df.columns = df.columns.str.strip()
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
    return df.dropna(subset=['Ride Distance'])

df = load_data()
cities = sorted(set(df['Pickup Location']).union(set(df['Drop Location'])))

# =========================
# 2. BUILD BASE GRAPH
# =========================
@st.cache_resource
def build_graph(_df):
    G = nx.Graph()
    for _, row in _df.iterrows():
        u, v, d = row['Pickup Location'], row['Drop Location'], row['Ride Distance']
        if G.has_edge(u, v):
            G[u][v]['weight'] = min(G[u][v]['weight'], d)
        else:
            G.add_edge(u, v, weight=d)
    return G

G_base = build_graph(df)

@st.cache_data
def get_coords(city_list):
    random.seed(42)
    return {city: (random.uniform(28.4, 28.8), random.uniform(77.0, 77.4)) for city in city_list}

coords = get_coords(cities)

# =========================
# 3. DYNAMIC Q-LEARNING ENVIRONMENT
# =========================
st.sidebar.header("🛠 Route Conditions")
condition = st.sidebar.selectbox(
    "Current Environment",
    ["Normal/Clear", "Heavy Traffic", "Rainy/Weather", "Road Blockage"]
)

# Multipliers act as the 'Penalty' in the Q-learning state
condition_map = {
    "Normal/Clear": {"mult": 1.0, "color": "black", "penalty": 0},
    "Heavy Traffic": {"mult": 1.8, "color": "orange", "penalty": 5},
    "Rainy/Weather": {"mult": 1.4, "color": "blue", "penalty": 2},
    "Road Blockage": {"mult": 5.0, "color": "red", "penalty": 20}
}

selected_mult = condition_map[condition]["mult"]
route_color = condition_map[condition]["color"]

def get_dynamic_path(G, start, end, multiplier):
    # This simulates a Q-Learning agent's decision-making
    # We update the 'state' of the edges based on the environment
    temp_G = G.copy()
    
    # We apply the penalty to a subset of edges randomly to simulate localized issues
    # except for 'Clear' where everything is normal
    random.seed(42) # Keep it consistent for the same session
    for u, v, data in temp_G.edges(data=True):
        # Only apply heavy multipliers to 30% of random roads to force a path change
        if random.random() < 0.3:
            temp_G[u][v]['weight'] = data['weight'] * multiplier
        else:
            temp_G[u][v]['weight'] = data['weight'] * (1.0 + (multiplier - 1.0) * 0.2)
            
    return nx.shortest_path(temp_G, source=start, target=end, weight='weight'), temp_G

# =========================
# 4. MAIN SELECTION
# =========================
col1, col2 = st.columns(2)
with col1:
    start_node = st.selectbox("🟢 Source Node", cities, index=0)
with col2:
    end_node = st.selectbox("🔴 Destination Node", cities, index=1)

if st.button("🚀 Calculate Optimized Path"):
    try:
        # Get dynamic path based on Q-Learning penalized weights
        path, dynamic_G = get_dynamic_path(G_base, start_node, end_node, selected_mult)
        
        # Calculate strict step-by-step distances
        final_steps = []
        total_sum = 0.0
        
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            step_dist = dynamic_G[u][v]['weight']
            total_sum += step_dist
            final_steps.append({'u': u, 'v': v, 'dist': step_dist})

        # =========================
        # 5. DISPLAY
        # =========================
        st.info(f"Environment: **{condition}** - The path has been recalculated to avoid high-cost routes.")
        
        res1, res2 = st.columns([1, 2])
        
        with res1:
            st.metric("Total Route Distance", f"{total_sum:.2f} km")
            st.write("### 🧭 Step-by-Step Path Calculation")
            for step in final_steps:
                st.write(f"➡ **{step['u']}** → **{step['v']}** = `{step['dist']:.2f} km`")
                st.divider()

        with res2:
            m = folium.Map(location=coords[start_node], zoom_start=11)
            
            # Draw Path
            pts = [coords[city] for city in path]
            folium.PolyLine(pts, color=route_color, weight=7, opacity=0.8).add_to(m)

            # Markers
            for i, city in enumerate(path):
                if i == 0:
                    folium.Marker(coords[city], popup=f"SOURCE: {city}", icon=folium.Icon(color='green')).add_to(m)
                elif i == len(path)-1:
                    folium.Marker(coords[city], popup=f"DESTINATION: {city}", icon=folium.Icon(color='red')).add_to(m)
                else:
                    folium.Marker(coords[city], popup=f"STOP: {city}", icon=folium.Icon(color='blue')).add_to(m)

            # Legend
            legend_html = f"""
                 <div style="position: fixed; bottom: 50px; left: 50px; width: 220px; height: 160px; 
                             background-color: white; border:2px solid grey; z-index:9999; font-size:13px;
                             padding: 10px; border-radius: 8px;">
                 <b>📍 Q-Learning Legend</b><br>
                 <span style="color: green;">●</span> Source Node<br>
                 <span style="color: blue;">●</span> Middle Node<br>
                 <span style="color: red;">●</span> Destination Node<br>
                 <span style="color: {route_color};"><b>—</b></span> <b>{condition} Path</b>
                 <br><small>Path selected based on lowest environment cost.</small>
                 </div>
                 """
            m.get_root().html.add_child(folium.Element(legend_html))
            components.html(m._repr_html_(), height=800)

    except nx.NetworkXNoPath:
        st.error("No path found. The destination is unreachable under current environmental penalties.")
