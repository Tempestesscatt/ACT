import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Satèl·lit Earth", layout="wide")

st.title("🛰️ Visualitzador de Satèl·lit")
st.caption("Imatges de satèl·lit en temps real via Esri World Imagery")

col1, col2, col3 = st.columns(3)
with col1:
    lat = st.number_input("Latitud", value=41.4033, format="%.4f")
with col2:
    lon = st.number_input("Longitud", value=2.1734, format="%.4f")
with col3:
    zoom = st.slider("Zoom", min_value=1, max_value=18, value=10)

# Mapa amb capa satèl·lit d'Esri
m = folium.Map(
    location=[lat, lon],
    zoom_start=zoom,
    tiles=None,
)

# Capa satèl·lit Esri (funciona sense API key)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Imagery",
    name="Satèl·lit",
    overlay=False,
    control=True,
).add_to(m)

# Marcador a la posició
folium.Marker(
    [lat, lon],
    popup=f"Lat: {lat:.4f}, Lon: {lon:.4f}",
    icon=folium.Icon(color="red", icon="crosshairs", prefix="fa"),
).add_to(m)

st_folium(m, width="100%", height=600)

st.markdown(
    "<small style='color:gray'>Font: Esri World Imagery · Dades de satèl·lit · Sense API key</small>",
    unsafe_allow_html=True,
)
