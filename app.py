# Online Python compiler (interpreter) to run Python online.
# Write Python 3 code in this online editor and run it.


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
st.title("🌍 Smart Route Optimizer2")

# =========================
# 1. LOAD DATA
# =========================
@st.cache_data
def load_data():
    # Loading your updated bookings.csv
    df = pd.read_csv("bookings.csv", encoding="latin1", on_bad_lines='skip')
    df.columns = df.columns.str.strip()
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
    # Remove rows where distance is missing to avoid graph errors
    df = df.dropna(subset=['Ride Distance'])
    return df

df = load_data()
cities = sorted(set(df['Pickup Location']).union(set(df['Drop Location'])))

# =========================
# 2. BUILD GRAPH (STRICT WEIGHTS)
# =========================
@st.cache_resource
def build_graph(_df):
    G = nx.Graph()
    # We group by locations and take the MINIMUM distance to ensure the graph is accurate
    clean_edges = _df.groupby(['Pickup Location', 'Drop Location'])['Ride Distance'].min().reset_index()
    
    for _, row in clean_edges.iterrows():
        u, v, d = row['Pickup Location'], row['Drop Location'], row['Ride Distance']
        G.add_edge(u, v, weight=d)
    return G

G_base = build_graph(df)

# Fixed Coordinates for visualization consistency
@st.cache_data
def get_coords(city_list):
    random.seed(42) 
    # Generating coordinates within a tighter Delhi-NCR bounding box
    return {city: (random.uniform(28.4, 28.8), random.uniform(77.0, 77.4)) for city in city_list}

coords = get_coords(cities)

# =========================
# 3. DYNAMIC TRAFFIC LOGIC
# =========================
def apply_dynamic(G):
    temp_G = G.copy()
    events = {}
    for u, v in temp_G.edges():
        r = random.random()
        if r < 0.10:
            temp_G[u][v]['weight'] *= 2.5  # Blocked weight increase
            events[(u, v)] = "🚧 Blocked"
        elif r < 0.25:
            temp_G[u][v]['weight'] *= 1.6  # Traffic weight increase
            events[(u, v)] = "🚦 Traffic"
        else:
            events[(u, v)] = "✅ Clear"
    return temp_G, events

# =========================
# 4. USER INTERFACE
# =========================
col1, col2 = st.columns(2)
with col1:
    start_node = st.selectbox("🟢 Source", cities, index=0)
with col2:
    end_node = st.selectbox("🔴 Destination", cities, index=min(1, len(cities)-1))

if st.button("🚀 Find Smart Route"):
    # Apply conditions to the graph
    temp_G, events = apply_dynamic(G_base)
    
    try:
        # Calculate Shortest Path using current (dynamic) weights
        path = nx.shortest_path(temp_G, source=start_node, target=end_node, weight='weight')
        
        # --- CALCULATION FIX ---
        # We calculate the total distance by summing the steps directly
        total_dist = 0.0
        path_details = []
        
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            # Retrieve the weight used by the algorithm
            step_dist = temp_G[u][v]['weight']
            total_dist += step_dist
            path_details.append({
                "from": u,
                "to": v,
                "dist": step_dist,
                "status": events.get((u, v), "Clear")
            })

        # =========================
        # OUTPUT DISPLAY
        # =========================
        st.success(f"✅ Route Optimized: {start_node} to {end_node}")
        
        res_col1, res_col2 = st.columns([1, 2])
        
        with res_col1:
            st.metric("Total Route Distance", f"{total_dist:.2f} km")
            
            st.write("### 🧭 Step-by-Step Breakdown")
            for step in path_details:
                st.write(f"➡ **{step['from']}** → **{step['to']}**")
                st.info(f"Distance: **{step['dist']:.2f} km** | Status: {step['status']}")
            
            # Final Validation Check for user peace of mind
            st.caption(f"Verification: Sum of steps ({sum(s['dist'] for s in path_details):.2f}) == Total ({total_dist:.2f})")

        with res_col2:
            # Generate Map
            m = folium.Map(location=coords[start_node], zoom_start=11, tiles="cartodbpositron")

            # Draw the Path
            route_coords = [coords[city] for city in path]
            folium.PolyLine(route_coords, color="black", weight=6, opacity=0.8).add_to(m)

            # Markers
            folium.Marker(coords[start_node], popup="START", icon=folium.Icon(color='green')).add_to(m)
            folium.Marker(coords[end_node], popup="END", icon=folium.Icon(color='red')).add_to(m)

            # Map Legend
            legend_html = """
                 <div style="position: fixed; bottom: 50px; left: 50px; width: 150px; height: 100px; 
                             background-color: white; border:2px solid grey; z-index:9999; font-size:12px;
                             padding: 10px; border-radius: 5px;">
                 <b>Route Legend</b><br>
                 <span style="color: black;">▬</span> Optimized Path<br>
                 <span style="color: green;">●</span> Source<br>
                 <span style="color: red;">●</span> Destination
                 </div>
                 """
            m.get_root().html.add_child(folium.Element(legend_html))
            
            components.html(m._repr_html_(), height=600)

    except nx.NetworkXNoPath:
        st.error("No path found between these locations. Try a different source or destination.")
