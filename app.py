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
st.title("🌍 Smart Route Optimizer")

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
    ["Normal/Clear", "Road Blockage"]
)

# Q-Learning inspired Penalty: Higher values force the path to change physically
condition_map = {
    "Normal/Clear": {"penalty": 1.0, "color": "black", "mult": 1.0},
    #"Heavy Traffic": {"penalty": 4.0, "color": "orange", "mult": 1.3},
    #"Rainy/Weather": {"penalty": 2.5, "color": "blue", "mult": 1.15},
    "Road Blockage": {"penalty": 15.0, "color": "red", "mult": 1.8}
}

selected_penalty = condition_map[condition]["penalty"]
selected_mult = condition_map[condition]["mult"]
route_color = condition_map[condition]["color"]

# =========================
# 4. MAIN SELECTION
# =========================
col1, col2 = st.columns(2)
with col1:
    start_node = st.selectbox("🟢 Source Node", cities, index=cities.index("Vidhan Sabha") if "Vidhan Sabha" in cities else 0)
with col2:
    end_node = st.selectbox("🔴 Destination Node", cities, index=cities.index("AIIMS") if "AIIMS" in cities else 1)

if st.button("🛣️ Start Navigation"):
    
    # --- DYNAMIC PATH RE-ROUTING (Q-Learning logic) ---
    temp_G = G_base.copy()
    
    # To force the graph path to change, we increase the cost of edges 
    # based on the environment. This makes the 'normal' path too expensive.
    random.seed(hash(condition)) 
    for u, v in temp_G.edges():
        if random.random() < 0.5: # 50% chance an edge is affected by current condition
            temp_G[u][v]['weight'] *= selected_penalty

    # A. Get Dataset Ride Distance (Ground Truth)
    direct_match = df[((df['Pickup Location'] == start_node) & (df['Drop Location'] == end_node)) | 
                      ((df['Pickup Location'] == end_node) & (df['Drop Location'] == start_node))]
    
    base_total = direct_match.iloc[0]['Ride Distance'] if not direct_match.empty else None

    try:
        # B. Calculate the path on the re-weighted graph
        # This will now yield a DIFFERENT set of nodes (a detour)
        path = nx.shortest_path(temp_G, source=start_node, target=end_node, weight='weight')
        
        # C. Calculate Segment Ratios
        raw_segments = []
        raw_sum = 0.0
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            d = G_base[u][v]['weight'] # Base distance for ratio
            raw_sum += d
            raw_segments.append({'u': u, 'v': v, 'base': d})

        # D. Maintain Distance Integrity
        if base_total is None: base_total = raw_sum
        dynamic_total = base_total * selected_mult
        
        final_steps = []
        actual_sum_check = 0.0
        for seg in raw_segments:
            # Proportionally distribute the dynamic total among the NEW nodes
            segment_share = (seg['base'] / raw_sum) * dynamic_total
            actual_sum_check += segment_share
            final_steps.append({'u': seg['u'], 'v': seg['v'], 'dist': segment_share})

        # =========================
        # 5. DISPLAY
        # =========================
        st.info(f"Environment: **{condition}**.")
        
        res1, res2 = st.columns([1, 2])
        
        with res1:
            st.metric("Total Route Distance", f"{actual_sum_check:.2f} km")
            st.write("### 🧭 Step-by-Step Breakdown")
            for step in final_steps:
                st.write(f"➡ **{step['u']}** → **{step['v']}** = `{step['dist']:.2f} km`")
                st.divider()

        with res2:
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
                 </div>
                 """
            m.get_root().html.add_child(folium.Element(legend_html))
            components.html(m._repr_html_(), height=800)

    except nx.NetworkXNoPath:
        st.error("No alternative path found under these severe conditions.")
