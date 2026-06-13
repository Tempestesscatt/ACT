import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Lameteo.cat · Visor meteorològic",
    page_icon="🌦️",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding: 0rem 1rem 0rem 1rem;
    max-width: 100%;
}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<style>
body {
  margin: 0;
  background: #07111f;
  font-family: Inter, Arial, sans-serif;
  color: white;
}

.app {
  height: 850px;
  display: grid;
  grid-template-columns: 310px 1fr;
  background: #07111f;
  border-radius: 24px;
  overflow: hidden;
  border: 1px solid rgba(120,180,255,.22);
}

.sidebar {
  background: rgba(8,15,28,.96);
  padding: 18px;
  border-right: 1px solid rgba(120,180,255,.18);
}

.brand {
  background: linear-gradient(135deg,#10223d,#07111f);
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(120,220,255,.28);
  margin-bottom: 18px;
}

.brand h1 {
  margin: 0;
  font-size: 24px;
}

.brand p {
  margin: 6px 0 0;
  color: #9fb4cc;
  font-size: 13px;
}

.layer {
  background: rgba(255,255,255,.06);
  border: 1px solid rgba(120,180,255,.16);
  border-radius: 15px;
  padding: 12px;
  margin-bottom: 10px;
}

.layer label {
  font-weight: 700;
  font-size: 14px;
}

.layer small {
  display: block;
  color: #8fa6c2;
  margin-top: 4px;
}

.mapbox {
  position: relative;
}

#map {
  height: 850px;
  width: 100%;
  background: #0b1320;
}

.topbar {
  position: absolute;
  z-index: 999;
  top: 18px;
  right: 18px;
  background: rgba(7,15,28,.82);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(120,180,255,.28);
  border-radius: 16px;
  padding: 8px;
}

.topbar button {
  background: #121d31;
  color: white;
  border: 1px solid rgba(120,180,255,.25);
  padding: 10px 12px;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 700;
}

.topbar button:hover {
  background: #2dd4ff;
  color: #06111f;
}

.info {
  position: absolute;
  z-index: 999;
  right: 18px;
  bottom: 24px;
  width: 280px;
  background: rgba(7,15,28,.86);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(120,180,255,.28);
  border-radius: 18px;
  padding: 14px;
  font-size: 13px;
}

.info b {
  color: #66e3ff;
}

@media(max-width: 800px) {
  .app {
    grid-template-columns: 1fr;
    height: 900px;
  }
  .sidebar {
    max-height: 260px;
    overflow: auto;
  }
  #map {
    height: 640px;
  }
}
</style>
</head>

<body>
<div class="app">
  <div class="sidebar">
    <div class="brand">
      <h1>🌦️ Lameteo.cat</h1>
      <p>Radar, satèl·lit i models meteorològics en temps real</p>
    </div>

    <div class="layer">
      <label><input type="checkbox" id="radar" checked> Radar de pluja</label>
      <small>RainViewer · temps real</small>
    </div>

    <div class="layer">
      <label><input type="checkbox" id="sat"> Satèl·lit EUMETSAT</label>
      <small>Natural color / visible</small>
    </div>

    <div class="layer">
      <label><input type="checkbox" id="ecmwf_msl"> ECMWF · Pressió MSL</label>
      <small>Model europeu</small>
    </div>

    <div class="layer">
      <label><input type="checkbox" id="ecmwf_t850"> ECMWF · Temperatura 850 hPa</label>
      <small>Model europeu</small>
    </div>

    <div class="layer">
      <label><input type="checkbox" id="ecmwf_z500"> ECMWF · Z500</label>
      <small>Geopotencial 500 hPa</small>
    </div>
  </div>

  <div class="mapbox">
    <div id="map"></div>

    <div class="topbar">
      <button onclick="goCat()">Catalunya</button>
      <button onclick="goIberia()">Península</button>
      <button onclick="goEurope()">Europa</button>
    </div>

    <div class="info">
      <b>Fonts actives</b><br>
      Radar: RainViewer<br>
      Satèl·lit: EUMETSAT WMS<br>
      Models: ECMWF ecCharts WMS<br><br>
      ⚠️ Algunes capes poden requerir clau/API o permisos.
    </div>
  </div>
</div>

<script>
const map = L.map('map', {
  center: [41.65, 1.8],
  zoom: 7,
  zoomControl: true
});

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '© OpenStreetMap · CartoDB'
}).addTo(map);

let radarLayer = null;

async function loadRadar() {
  const response = await fetch('https://api.rainviewer.com/public/weather-maps.json');
  const data = await response.json();
  const frames = data.radar.past;
  const last = frames[frames.length - 1];
  const url = data.host + last.path + '/256/{z}/{x}/{y}/2/1_1.png';

  radarLayer = L.tileLayer(url, {
    opacity: 0.75,
    attribution: 'RainViewer'
  });

  if (document.getElementById('radar').checked) {
    radarLayer.addTo(map);
  }
}

loadRadar();

const eumetsat = L.tileLayer.wms('https://view.eumetsat.int/geoserver/ows', {
  layers: 'msg_fes:rgb_natural',
  format: 'image/png',
  transparent: true,
  opacity: 0.65,
  attribution: 'EUMETSAT'
});

const ecmwf_msl = L.tileLayer.wms('https://eccharts.ecmwf.int/wms/', {
  layers: 'msl_public',
  format: 'image/png',
  transparent: true,
  opacity: 0.65,
  attribution: 'ECMWF'
});

const ecmwf_t850 = L.tileLayer.wms('https://eccharts.ecmwf.int/wms/', {
  layers: 't850_public',
  format: 'image/png',
  transparent: true,
  opacity: 0.65,
  attribution: 'ECMWF'
});

const ecmwf_z500 = L.tileLayer.wms('https://eccharts.ecmwf.int/wms/', {
  layers: 'z500_public',
  format: 'image/png',
  transparent: true,
  opacity: 0.65,
  attribution: 'ECMWF'
});

function toggle(id, layer) {
  document.getElementById(id).addEventListener('change', e => {
    if (e.target.checked) {
      layer.addTo(map);
    } else {
      map.removeLayer(layer);
    }
  });
}

document.getElementById('radar').addEventListener('change', e => {
  if (!radarLayer) return;
  if (e.target.checked) radarLayer.addTo(map);
  else map.removeLayer(radarLayer);
});

toggle('sat', eumetsat);
toggle('ecmwf_msl', ecmwf_msl);
toggle('ecmwf_t850', ecmwf_t850);
toggle('ecmwf_z500', ecmwf_z500);

function goCat() {
  map.setView([41.65, 1.8], 7);
}

function goIberia() {
  map.setView([40.2, -3.5], 5);
}

function goEurope() {
  map.setView([48.5, 8], 4);
}
</script>
</body>
</html>
"""

st.title("🌦️ Lameteo.cat · Visor meteorològic")
st.caption("Radar, satèl·lit i models meteorològics en una sola pàgina.")

components.html(html, height=870)
