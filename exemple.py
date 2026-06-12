import streamlit as st
import requests
from PIL import Image
from io import BytesIO

st.set_page_config(page_title="Satélite Earth", layout="centered")

st.title("🌍 Imagen Satélite de la Tierra")
st.caption("Imagen en tiempo real desde NASA Worldview (GIBS)")

# Parámetros del mapa
lat = st.number_input("Latitud", value=41.4, format="%.4f")
lon = st.number_input("Longitud", value=2.17, format="%.4f")
zoom = st.slider("Zoom (radio en grados)", min_value=0.1, max_value=10.0, value=1.0, step=0.1)

# Calcular bounding box
bbox = f"{lon - zoom},{lat - zoom},{lon + zoom},{lat + zoom}"

# URL del servicio WMS de NASA GIBS (MODIS Terra, capa de color natural)
url = (
    "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
    "?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap"
    "&LAYERS=MODIS_Terra_CorrectedReflectance_TrueColor"
    f"&BBOX={bbox}"
    "&WIDTH=800&HEIGHT=600"
    "&SRS=EPSG:4326"
    "&FORMAT=image/jpeg"
    "&TIME=2024-01-01"
)

st.markdown("---")

if st.button("📡 Obtener imagen"):
    with st.spinner("Descargando imagen del satélite..."):
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
                img = Image.open(BytesIO(response.content))
                st.image(img, caption=f"Lat: {lat}, Lon: {lon} | Zoom: ±{zoom}°", use_container_width=True)
                st.success("✅ Imagen cargada desde NASA GIBS (MODIS Terra)")
            else:
                st.error(f"Error al obtener imagen. Código HTTP: {response.status_code}")
        except Exception as e:
            st.error(f"Error de conexión: {e}")

st.markdown(
    "<small style='color:gray'>Fuente: NASA GIBS · MODIS Terra True Color · EPSG:4326</small>",
    unsafe_allow_html=True,
)
