import streamlit as st

st.set_page_config(page_title="Satèl·lit Earth", layout="wide")
st.title("🛰️ Visualitzador de Satèl·lit")

col1, col2, col3 = st.columns(3)
with col1:
    lat = st.number_input("Latitud", value=41.4033, format="%.4f")
with col2:
    lon = st.number_input("Longitud", value=2.1734, format="%.4f")
with col3:
    zoom = st.slider("Zoom", min_value=1, max_value=18, value=10)

html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    body {{ margin: 0; padding: 0; }}
    #map {{ width: 100%; height: 580px; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    var map = L.map('map').setView([{lat}, {lon}], {zoom});

    L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
      {{ attribution: 'Esri World Imagery', maxZoom: 18 }}
    ).addTo(map);

    L.marker([{lat}, {lon}])
      .addTo(map)
      .bindPopup('Lat: {lat:.4f}, Lon: {lon:.4f}')
      .openPopup();
  </script>
</body>
</html>
"""

st.components.v1.html(html, height=600)
st.caption("Font: Esri World Imagery · Leaflet.js · Sense API key")
