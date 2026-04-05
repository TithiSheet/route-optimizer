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
    # Ensure your file is named bookings.csv or update this string
    df = pd.read_csv("bookings.csv", encoding="latin1", on_bad_lines='skip')
    df.columns = df.columns.str.strip()
    df['Ride Distance'] = pd.to_numeric(df['Ride Distance'], errors='coerce')
    # Use only rows with valid distances
    df = df.dropna(subset=['Ride Distance'])
    return df

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

# Fixed Coordinates (Caching prevents nodes from jumping)
@st.cache_data
def get_fixed_coords(city_list):
    random.seed(42)
    return {city: (random.uniform(28.4, 28.8), random.uniform(77.0, 77.4)) for city in city_list}

coords = get_fixed_coords(cities)

# =========================
# 3. DYNAMIC ENVIRONMENT
# =========================
def apply_dynamic_conditions(G):
    dynamic_G = G.copy()
    events = {}
    for u, v in dynamic_G.edges():
        r = random.random()
        if r < 0.15:
            dynamic_G[u][v]['weight'] *= 2.5
            events[(u, v)] = "🔴 Blocked"
        elif r < 0.30:
            dynamic_G[u][v]['weight'] *= 1.6
            events[(u, v)] = "🟠 Traffic"
        else:
            events[(u, v)] = "🟢 Clear"
    return dynamic_G, events

# =========================
# 4. USER INTERFACE
# =========================
col1, col2 = st.columns(2)
with col1:
    start_node = st.selectbox("🟢 Select Source", cities, index=cities.index("IGI Airport") if "IGI Airport" in cities else 0)
with col2:
    end_node = st.selectbox("🔴 Select Destination", cities, index=cities.index("Madipur") if "Madipur" in cities else 1)

if st.button("🚀 Find Smart Route"):
    # Apply dynamic weights
    temp_G, status_map = apply_dynamic_conditions(G_base)
    
    try:
        # Calculate Path
        path = nx.shortest_path(temp_G, source=start_node, target=end_node, weight='weight')
        
        # CALCULATE CORRECT TOTAL DISTANCE (Sum of steps)
        total_sum = 0.0
        step_details = []
        
        for i in range(len(path)-1):
            u, v = path[i], path[i+1]
            # Get the weight actually used in the graph
            weight = temp_G[u][v]['weight']
            total_sum += weight
            step_details.append({
                "from": u, "to": v, 
                "dist": weight, 
                "status": status_map.get((u, v), status_map.get((v, u), "Clear"))
            })

        # =========================
        # 5. DISPLAY RESULTS
        # =========================
        st.success(f"✅ Route Optimized Successfully")
        
        res_col1, res_col2 = st.columns([1, 2])
        
        with res_col1:
            st.metric("Total Calculated Distance", f"{total_sum:.2f} km")
            st.write(f"**Stops:** {len(path)-2} intermediate nodes")
            
            st.write("### 🧭 Step-by-Step Distance")
            for step in step_details:
                st.write(f"➡ **{step['from']}** → **{step['to']}** = `{step['dist']:.2f} km`")
                st.caption(f"Status: {step['status']}")
                st.divider()

        with res_col2:
            # Create Map
            m = folium.Map(location=coords[start_node], zoom_start=11, tiles="cartodbpositron")

            # Draw Route Path
            route_coords = [coords[city] for city in path]
            folium.PolyLine(route_coords, color="black", weight=5, opacity=0.7).add_to(m)

            # Markers for Source, Destination, and Middle Nodes
            for i, city in enumerate(path):
                if i == 0:
                    folium.Marker(coords[city], popup=f"Source: {city}", icon=folium.Icon(color='green', icon='play')).add_to(m)
                elif i == len(path) - 1:
                    folium.Marker(coords[city], popup=f"Destination: {city}", icon=folium.Icon(color='red', icon='stop')).add_to(m)
                else:
                    folium.Marker(coords[city], popup=f"Middle Node: {city}", icon=folium.Icon(color='blue', icon='info-sign')).add_to(m)

            # LEGEND HTML
            legend_html = """
                 <div style="position: fixed; bottom: 50px; left: 50px; width: 200px; height: 160px; 
                             background-color: white; border:2px solid grey; z-index:9999; font-size:14px;
                             padding: 10px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
                 <b>📍 Legend</b><br>
                 <span style="color: green;">●</span> Source Node<br>
                 <span style="color: blue;">●</span> Middle Node<br>
                 <span style="color: red;">●</span> Destination Node<br>
                 <span style="color: black;"><b>—</b></span> Route Path<br>
                 <hr style="margin:5px 0;">
                 <small>Weights updated based on dynamic traffic conditions.</small>
                 </div>
                 """
            m.get_root().html.add_child(folium.Element(legend_html))
            
            # Show Map
            components.html(m._repr_html_(), height=600)

    except nx.NetworkXNoPath:
        st.error("No path could be found between these locations under current traffic conditions.")
