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
st.title("🌍 Smart Dynamic Route Optimizer")

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
# 2. BUILD GRAPH
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
# 3. UI SIDEBAR (DYNAMIC CONTROLS)
# =========================
st.sidebar.header("🛠 Route Conditions")
condition = st.sidebar.selectbox(
    "Current Environment",
    ["Normal/Clear", "Heavy Traffic", "Rainy/Weather", "Road Blockage"]
)

# Q-Learning inspired Penalty Multipliers
# These change the 'cost' of edges, forcing the algorithm to find a new path
condition_map = {
    "Normal/Clear": {"penalty": 1.0, "color": "black", "desc": "Optimal Path"},
    "Heavy Traffic": {"penalty": 3.5, "color": "orange", "desc": "Avoiding Congestion"},
    "Rainy/Weather": {"penalty": 2.0, "color": "blue", "desc": "Slower Traction"},
    "Road Blockage": {"penalty": 10.0, "color": "red", "desc": "Detour Required"}
}

selected_penalty = condition_map[condition]["penalty"]
route_color = condition_map[condition]["color"]

# =========================
# 4. MAIN SELECTION
# =========================
col1, col2 = st.columns(2)
with col1:
    start_node = st.selectbox("🟢 Source Node", cities, index=0)
with col2:
    end_node = st.selectbox("🔴 Destination Node", cities, index=1)

if st.button("🚀 Calculate Dynamic Route"):
    
    # A. Apply Environment Penalties to Graph Edges
    # This simulates the 'State' update in Q-Learning
    temp_G = G_base.copy()
    random.seed(hash(condition)) # Consistent "random" blocks per condition
    
    for u, v in temp_G.edges():
        # Randomly assign the condition impact to specific edges
        if random.random() < 0.4: # 40% of roads are affected by the condition
            temp_G[u][v]['weight'] *= selected_penalty

    try:
        # B. Calculate Path on the RE-WEIGHTED graph
        # This will now yield a different 'path' list if a detour is cheaper
        path = nx.shortest_path(temp_G, source=start_node, target=end_node, weight='weight')
        
        # C. Calculate Segment Breakdown
        final_steps = []
        total_dist_sum = 0.0
        
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            # We display the actual distance from the base dataset, 
            # multiplied by the penalty to show impact.
            seg_dist = temp_G[u][v]['weight']
            total_dist_sum += seg_dist
            final_steps.append({'u': u, 'v': v, 'dist': seg_dist})

        # =========================
        # 5. DISPLAY
        # =========================
        st.info(f"Condition: **{condition}** | Strategy: **{condition_map[condition]['desc']}**")
        
        res1, res2 = st.columns([1, 2])
        
        with res1:
            st.metric("Total Route Distance", f"{total_dist_sum:.2f} km")
            st.write("### 🧭 Step-by-Step Breakdown")
            for step in final_steps:
                st.write(f"➡ **{step['u']}** → **{step['v']}** = `{step['dist']:.2f} km`")
                st.divider()

        with res2:
            m = folium.Map(location=coords[start_node], zoom_start=11)
            
            # Draw Dynamic Path
            pts = [coords[city] for city in path]
            folium.PolyLine(pts, color=route_color, weight=6, opacity=0.8).add_to(m)

            # Markers
            for i, city in enumerate(path):
                if i == 0:
                    folium.Marker(coords[city], popup=f"START: {city}", icon=folium.Icon(color='green')).add_to(m)
                elif i == len(path)-1:
                    folium.Marker(coords[city], popup=f"END: {city}", icon=folium.Icon(color='red')).add_to(m)
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
                 <br><small>Path intelligently rerouted based on road cost.</small>
                 </div>
                 """
            m.get_root().html.add_child(folium.Element(legend_html))
            components.html(m._repr_html_(), height=800)

    except nx.NetworkXNoPath:
        st.error("No path found. Roads are too heavily blocked.")
