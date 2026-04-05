import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import streamlit.components.v1 as components

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide", page_title="Dynamic Route Optimizer")
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

# Define multipliers based on conditions
condition_map = {
    "Normal/Clear": {"mult": 1.0, "color": "black"},
    "Heavy Traffic": {"mult": 1.3, "color": "orange"},
    "Rainy/Weather": {"mult": 1.15, "color": "blue"},
    "Road Blockage": {"mult": 1.8, "color": "red"}
}

selected_mult = condition_map[condition]["mult"]
route_color = condition_map[condition]["color"]

# =========================
# 4. MAIN SELECTION
# =========================
col1, col2 = st.columns(2)
with col1:
    start_node = st.selectbox("🟢 Source Node", cities, index=0)
with col2:
    end_node = st.selectbox("🔴 Destination Node", cities, index=1)

if st.button("Route Calculation "):
    
    # A. Get Dataset Ride Distance
    direct_match = df[((df['Pickup Location'] == start_node) & (df['Drop Location'] == end_node)) | 
                      ((df['Pickup Location'] == end_node) & (df['Drop Location'] == start_node))]
    
    if direct_match.empty:
        st.warning("No direct distance in dataset. Using calculated shortest path.")
        base_total = None
    else:
        # Ground Truth from CSV
        base_total = direct_match.iloc[0]['Ride Distance']

    try:
        # B. Shortest Path
        path = nx.shortest_path(G_base, source=start_node, target=end_node, weight='weight')
        
        # C. Calculate Segment Ratios
        raw_segments = []
        raw_sum = 0.0
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            d = G_base[u][v]['weight']
            raw_sum += d
            raw_segments.append({'u': u, 'v': v, 'base': d})

        # D. Apply Dynamic Multiplier to the Dataset Total
        if base_total is None: base_total = raw_sum
        
        dynamic_total = base_total * selected_mult
        
        # E. Fragment the Dynamic Total into segments
        final_steps = []
        actual_sum_check = 0.0
        
        for seg in raw_segments:
            # Proportionally distribute the dynamic total
            segment_share = (seg['base'] / raw_sum) * dynamic_total
            actual_sum_check += segment_share
            final_steps.append({'u': seg['u'], 'v': seg['v'], 'dist': segment_share})

        # =========================
        # 5. DISPLAY
        # =========================
        st.info(f"Condition Applied: **{condition}**")
        
        res1, res2 = st.columns([1, 2])
        
        with res1:
            st.metric("Total Route Distance", f"{actual_sum_check:.2f} km")
            st.write("### 🧭 Step-by-Step Breakdown")
            for step in final_steps:
                st.write(f"➡ **{step['u']}** → **{step['v']}** = `{step['dist']:.2f} km`")
                st.divider()

        with res2:
            # INCREASED SIZE: Map is now 800px high for better visibility
            m = folium.Map(location=coords[start_node], zoom_start=11)
            
            # Draw Path with Dynamic Color
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
                 <b>📍 Dynamic Legend</b><br>
                 <span style="color: green;">●</span> Source Node<br>
                 <span style="color: blue;">●</span> Middle Node<br>
                 <span style="color: red;">●</span> Destination Node<br>
                 <span style="color: {route_color};"><b>—</b></span> <b>{condition} Path</b>
                 <br><small>Total = Base CSV Dist × {selected_mult}</small>
                 </div>
                 """
            m.get_root().html.add_child(folium.Element(legend_html))
            
            # Height increased to 800 for the larger view you requested
            components.html(m._repr_html_(), height=800)

    except nx.NetworkXNoPath:
        st.error("No path found.")
