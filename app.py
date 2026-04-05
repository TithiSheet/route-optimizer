import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import streamlit.components.v1 as components

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(layout="wide", page_title="Smart Route Optimizer")
st.title("🌍 Smart Route Optimizer")

# =========================
# 1. LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_csv("bookings.csv", encoding="latin1", on_bad_lines='skip')
    df.columns = df.columns.str.strip()
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
    # Filter valid rows
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

# Fixed Map Coordinates
@st.cache_data
def get_coords(city_list):
    random.seed(42)
    return {city: (random.uniform(28.4, 28.8), random.uniform(77.0, 77.4)) for city in city_list}

coords = get_coords(cities)

# =========================
# 3. UI SELECTION
# =========================
col1, col2 = st.columns(2)
with col1:
    start_node = st.selectbox("🟢 Source Node", cities, index=cities.index("IGI Airport") if "IGI Airport" in cities else 0)
with col2:
    end_node = st.selectbox("🔴 Destination Node", cities, index=cities.index("Madipur") if "Madipur" in cities else 1)

if st.button("Calculate Route"):
    
    # A. Get the "Ride Distance" from dataset for this specific trip
    direct_row = df[((df['Pickup Location'] == start_node) & (df['Drop Location'] == end_node)) | 
                    ((df['Pickup Location'] == end_node) & (df['Drop Location'] == start_node))]
    
    if direct_row.empty:
        st.warning("No direct ride distance found for this pair in dataset. Using path sum.")
        target_total = None
    else:
        target_total = direct_row.iloc[0]['Ride Distance']

    try:
        # B. Find the path
        path = nx.shortest_path(G_base, source=start_node, target=end_node, weight='weight')
        
        # C. Calculate the Raw Sum of segments in the path
        raw_segment_data = []
        raw_path_sum = 0.0
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            dist = G_base[u][v]['weight']
            raw_path_sum += dist
            raw_segment_data.append({'from': u, 'to': v, 'base_dist': dist})
        
        # D. Calculate Scaled Distances to match Dataset's "Ride Distance"
        # Logic: (Segment / Total Path Sum) * Dataset Ride Distance
        final_details = []
        final_total_display = 0.0
        
        if target_total and raw_path_sum > 0:
            scale_factor = target_total / raw_path_sum
        else:
            scale_factor = 1.0
            target_total = raw_path_sum

        for seg in raw_segment_data:
            scaled_dist = seg['base_dist'] * scale_factor
            final_total_display += scaled_dist
            final_details.append({
                "from": seg['from'], 
                "to": seg['to'], 
                "dist": scaled_dist
            })

        # =========================
        # 4. OUTPUT DISPLAY
        # =========================
        st.success(f"✅ Journey: {start_node} to {end_node}")
        
        res_col1, res_col2 = st.columns([1, 2])
        
        with res_col1:
            st.metric("Total Route Distance (Matches Dataset)", f"{final_total_display:.2f} km")
            st.write("### 🧭 Step-by-Step Segments")
            for d in final_details:
                st.write(f"➡ **{d['from']}** → **{d['to']}** = `{d['dist']:.2f} km`")
                st.divider()

        with res_col2:
            m = folium.Map(location=coords[start_node], zoom_start=11)
            
            # Draw Path Line
            route_pts = [coords[city] for city in path]
            folium.PolyLine(route_pts, color="black", weight=5).add_to(m)

            # Markers: Source (Green), Middle (Blue), Destination (Red)
            for i, city in enumerate(path):
                if i == 0:
                    folium.Marker(coords[city], popup=f"SOURCE: {city}", icon=folium.Icon(color='green')).add_to(m)
                elif i == len(path)-1:
                    folium.Marker(coords[city], popup=f"DESTINATION: {city}", icon=folium.Icon(color='red')).add_to(m)
                else:
                    folium.Marker(coords[city], popup=f"MIDDLE NODE: {city}", icon=folium.Icon(color='blue')).add_to(m)

            # LEGEND
            legend_html = """
                 <div style="position: fixed; bottom: 50px; left: 50px; width: 210px; height: 140px; 
                             background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
                             padding: 10px; border-radius: 8px;">
                 <b>📍 Legend</b><br>
                 <span style="color: green;">●</span> Source Node (Start)<br>
                 <span style="color: blue;">●</span> Middle Node (Intermediate)<br>
                 <span style="color: red;">●</span> Destination Node (End)<br>
                 <span style="color: black;"><b>—</b></span> Calculated Route Path
                 </div>
                 """
            m.get_root().html.add_child(folium.Element(legend_html))
            components.html(m._repr_html_(), height=600)

    except nx.NetworkXNoPath:
        st.error("No connectivity found between these nodes in the dataset.")
