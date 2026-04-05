import streamlit as st
import pandas as pd
import networkx as nx
import folium
import random
import streamlit.components.v1 as components

st.set_page_config(layout="wide", page_title="Smart Route Optimizer")

st.title("🌍 Smart Route Optimizer")

# =========================
# LOAD AND CLEAN DATA
# =========================
@st.cache_data
def load_data():
    # Load dataset
    df = pd.read_csv("bookings.csv", encoding="latin1", on_bad_lines='skip')
    df.columns = df.columns.str.strip()
    # Convert distance to numeric and drop rows without distance
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
    df = df.dropna(subset=['Ride Distance'])
    return df

df = load_data()
cities = sorted(set(df['Pickup Location']).union(set(df['Drop Location'])))

# =========================
# BUILD BASE GRAPH
# =========================
@st.cache_resource
def build_graph(_df):
    G = nx.Graph()
    for _, row in _df.iterrows():
        u, v, d = row['Pickup Location'], row['Drop Location'], row['Ride Distance']
        # We take the minimum distance if multiple entries exist for the same route
        if G.has_edge(u, v):
            G[u][v]['weight'] = min(G[u][v]['weight'], d)
        else:
            G.add_edge(u, v, weight=d)
    return G

G_base = build_graph(df)

# Fixed Coordinates so cities don't "jump"
@st.cache_data
def get_coords(city_list):
    random.seed(42) 
    return {city: (random.uniform(28.4, 28.7), random.uniform(77.0, 77.3)) for city in city_list}

coords = get_coords(cities)

# =========================
# DYNAMIC ENVIRONMENT LOGIC
# =========================
def apply_dynamic_conditions(G):
    dynamic_G = G.copy()
    edge_events = {}
    
    for u, v in dynamic_G.edges():
        r = random.random()
        if r < 0.15:
            dynamic_G[u][v]['weight'] *= 2.5
            edge_events[(u, v)] = "🚧 Blocked (Heavy Delay)"
        elif r < 0.35:
            dynamic_G[u][v]['weight'] *= 1.6
            edge_events[(u, v)] = "🚦 Traffic Jam"
        else:
            edge_events[(u, v)] = "✅ Clear"
            
    return dynamic_G, edge_events

# =========================
# UI SIDEBAR / INPUTS
# =========================
col1, col2 = st.columns(2)
with col1:
    start_node = st.selectbox("🟢 Source", cities, index=0)
with col2:
    end_node = st.selectbox("🔴 Destination", cities, index=min(1, len(cities)-1))

if st.button("🚀 Calculate Smart Route"):
    # 1. Apply Dynamic Traffic
    temp_G, events = apply_dynamic_conditions(G_base)
    
    try:
        # 2. Find Shortest Path based on Dynamic Weights
        path = nx.shortest_path(temp_G, source=start_node, target=end_node, weight='weight')
        
        # 3. Calculate Step-by-Step Distance accurately
        path_details = []
        total_dist = 0.0
        
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            step_dist = temp_G[u][v]['weight']
            total_dist += step_dist
            path_details.append((u, v, step_dist, events.get((u, v), "Clear")))

        # =========================
        # DISPLAY RESULTS
        # =========================
        st.success(f"✅ Optimal Route Calculated")
        
        m_col1, m_col2 = st.columns([1, 2])
        
        with m_col1:
            st.metric("Total Distance", f"{total_dist:.2f} km")
            st.write("### 🧭 Step-by-Step Breakdown")
            for u, v, d, status in path_details:
                st.write(f"**{u}** → **{v}**")
                st.caption(f"Dist: {d:.2f} km | Status: {status}")
                st.divider()

        with m_col2:
            # Create Folium Map
            m = folium.Map(location=coords[start_node], zoom_start=12, tiles="cartodbpositron")

            # Draw Route Path
            route_coords = [coords[city] for city in path]
            folium.PolyLine(route_coords, color="black", weight=5, opacity=0.8).add_to(m)

            # Add Markers
            folium.Marker(coords[start_node], tooltip="START", icon=folium.Icon(color='green')).add_to(m)
            folium.Marker(coords[end_node], tooltip="END", icon=folium.Icon(color='red')).add_to(m)

            # Custom Legend HTML
            legend_html = """
                 <div style="position: fixed; bottom: 50px; left: 50px; width: 150px; height: 110px; 
                             background-color: white; border:2px solid grey; z-index:9999; font-size:12px;
                             padding: 10px; border-radius: 5px;">
                 <b>Map Legend</b><br>
                 <i style="background: black; width: 10px; height: 10px; display: inline-block;"></i> Route Path<br>
                 <i style="background: green; width: 10px; height: 10px; display: inline-block;"></i> Start Point<br>
                 <i style="background: red; width: 10px; height: 10px; display: inline-block;"></i> End Point
                 </div>
                 """
            m.get_root().html.add_child(folium.Element(legend_html))
            
            # Render Map
            components.html(m._repr_html_(), height=500)

    except nx.NetworkXNoPath:
        st.error("No path exists between these two locations.")
