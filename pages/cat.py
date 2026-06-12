import streamlit as st
import requests
import json
from datetime import datetime
import urllib.parse

st.set_page_config(
    page_title="Meteograma AROME · Catalunya",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Space+Mono:wght@400;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}
.block-container { padding: 1.5rem 2rem 2rem 2rem; max-width: 1200px; }

h1 {
    font-family: 'Space Mono', monospace;
    font-size: 1.4rem;
    font-weight: 700;
    color: #0f172a;
    letter-spacing: -0.5px;
    margin-bottom: 0;
}
.subtitle {
    font-size: 0.8rem;
    color: #64748b;
    margin-top: 2px;
    margin-bottom: 1.2rem;
    font-family: 'Space Mono', monospace;
}
.info-box {
    background: #f0f9ff;
    border-left: 3px solid #0ea5e9;
    padding: 8px 14px;
    border-radius: 4px;
    font-size: 0.82rem;
    color: #0c4a6e;
    margin-bottom: 1rem;
}
.coords-badge {
    background: #0f172a;
    color: #38bdf8;
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    padding: 4px 10px;
    border-radius: 4px;
    display: inline-block;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1>🛰 Meteograma AROME · Catalunya</h1>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Model Météo-France AROME HD · 1.3 km resolució · via Open-Meteo API</div>', unsafe_allow_html=True)

# ── Session state per coordenades ──────────────────────────────────────────
if "lat" not in st.session_state:
    st.session_state.lat = 41.4033
if "lon" not in st.session_state:
    st.session_state.lon = 2.1734

# ── Layout: mapa esquerra / meteograma dreta ───────────────────────────────
col_map, col_chart = st.columns([1, 1.6], gap="large")

with col_map:
    st.markdown("**Clica al mapa per seleccionar un punt**")
    st.markdown('<div class="info-box">📍 Clica sobre qualsevol punt de Catalunya per generar el meteograma AROME de les properes 48h.</div>', unsafe_allow_html=True)

    map_html = f"""
    <!DOCTYPE html><html><head>
    <meta charset="utf-8"/>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
      body {{ margin:0; padding:0; font-family: monospace; }}
      #map {{ width:100%; height:440px; }}
      #coords {{
        position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%);
        background: rgba(15,23,42,0.85); color: #38bdf8;
        padding: 5px 12px; border-radius: 4px; font-size: 12px; z-index: 1000;
        pointer-events: none;
      }}
    </style>
    </head><body>
    <div id="map"></div>
    <div id="coords">Lat: {st.session_state.lat:.4f} · Lon: {st.session_state.lon:.4f}</div>
    <script>
      var initLat = {st.session_state.lat};
      var initLon = {st.session_state.lon};

      var map = L.map('map', {{zoomControl: true}}).setView([41.8, 1.8], 7);

      L.tileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{{z}}/{{y}}/{{x}}',
        {{ attribution: 'Esri', maxZoom: 13 }}
      ).addTo(map);

      // Bounding box aproximat de Catalunya
      var catBounds = [[40.5, 0.15], [42.9, 3.35]];
      L.rectangle(catBounds, {{color:'#0ea5e9', weight:1.5, fillOpacity:0.04, dashArray:'4'}}).addTo(map);

      var marker = L.marker([initLat, initLon], {{
        icon: L.divIcon({{
          className: '',
          html: '<div style="width:14px;height:14px;background:#f43f5e;border:2.5px solid white;border-radius:50%;box-shadow:0 0 6px rgba(244,63,94,0.6)"></div>',
          iconSize:[14,14], iconAnchor:[7,7]
        }})
      }}).addTo(map);

      map.on('click', function(e) {{
        var lat = e.latlng.lat.toFixed(4);
        var lon = e.latlng.lng.toFixed(4);
        marker.setLatLng(e.latlng);
        document.getElementById('coords').innerText = 'Lat: ' + lat + ' · Lon: ' + lon;
        // Envia al parent de Streamlit
        window.parent.postMessage({{type:'streamlit:setComponentValue', value: lat + ',' + lon}}, '*');
      }});
    </script>
    </body></html>
    """

    click_data = st.components.v1.html(map_html, height=450)

    st.markdown("**O introdueix coordenades manualment:**")
    c1, c2 = st.columns(2)
    with c1:
        lat_in = st.number_input("Latitud", value=st.session_state.lat, format="%.4f", step=0.01, key="lat_in")
    with c2:
        lon_in = st.number_input("Longitud", value=st.session_state.lon, format="%.4f", step=0.01, key="lon_in")

    if st.button("📡 Generar meteograma", type="primary", use_container_width=True):
        st.session_state.lat = lat_in
        st.session_state.lon = lon_in
        st.session_state.fetch = True
        st.rerun()

with col_chart:
    lat = st.session_state.lat
    lon = st.session_state.lon

    st.markdown(f'<div class="coords-badge">📍 {lat:.4f}°N · {lon:.4f}°E</div>', unsafe_allow_html=True)

    # Fetch AROME data
    api_url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,apparent_temperature,precipitation,precipitation_probability,"
        f"windspeed_10m,windgusts_10m,cloudcover,cape"
        f"&models=meteofrance_arome_france_hd"
        f"&forecast_days=2"
        f"&timezone=Europe%2FMadrid"
    )

    with st.spinner("Descarregant dades AROME..."):
        try:
            r = requests.get(api_url, timeout=15)
            d = r.json()

            if "error" in d:
                st.error(f"Error API: {d.get('reason', d)}")
            else:
                hourly = d["hourly"]
                times_raw = hourly["time"]
                temp     = hourly["temperature_2m"]
                feels    = hourly["apparent_temperature"]
                precip   = hourly["precipitation"]
                prob     = hourly["precipitation_probability"]
                wind     = hourly["windspeed_10m"]
                gusts    = hourly["windgusts_10m"]
                cloud    = hourly["cloudcover"]
                cape_v   = hourly.get("cape", [0]*len(times_raw))

                # Format time labels
                labels = []
                for t in times_raw:
                    dt = datetime.fromisoformat(t)
                    labels.append(dt.strftime("%d/%m %Hh"))

                # Build JS arrays
                def js_arr(lst):
                    clean = [x if x is not None else "null" for x in lst]
                    return json.dumps(clean)

                chart_html = f"""
                <!DOCTYPE html><html><head>
                <meta charset="utf-8"/>
                <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
                <style>
                  body {{ margin:0; padding:0; background:transparent; font-family:'Inter',sans-serif; }}
                  .wrap {{ display:flex; flex-direction:column; gap:8px; padding:4px; }}
                  .chart-box {{ background:#fff; border:1px solid #e2e8f0; border-radius:8px; padding:10px 14px; }}
                  .chart-title {{ font-size:11px; font-weight:600; color:#475569; margin-bottom:4px; text-transform:uppercase; letter-spacing:0.5px; }}
                  canvas {{ display:block; }}
                </style>
                </head><body>
                <div class="wrap">

                  <!-- 1. Temperatura -->
                  <div class="chart-box">
                    <div class="chart-title">🌡 Temperatura (°C)</div>
                    <canvas id="cTemp" height="70"></canvas>
                  </div>

                  <!-- 2. Precipitació + probabilitat -->
                  <div class="chart-box">
                    <div class="chart-title">🌧 Precipitació (mm) i probabilitat (%)</div>
                    <canvas id="cPrecip" height="70"></canvas>
                  </div>

                  <!-- 3. Vent -->
                  <div class="chart-box">
                    <div class="chart-title">💨 Vent i ratxes (km/h)</div>
                    <canvas id="cWind" height="70"></canvas>
                  </div>

                  <!-- 4. Nuvolositat -->
                  <div class="chart-box">
                    <div class="chart-title">☁ Nuvolositat (%)</div>
                    <canvas id="cCloud" height="50"></canvas>
                  </div>

                </div>

                <script>
                  var labels = {json.dumps(labels)};
                  var temp   = {js_arr(temp)};
                  var feels  = {js_arr(feels)};
                  var precip = {js_arr(precip)};
                  var prob   = {js_arr(prob)};
                  var wind   = {js_arr(wind)};
                  var gusts  = {js_arr(gusts)};
                  var cloud  = {js_arr(cloud)};

                  var baseOpts = {{
                    responsive: true,
                    animation: false,
                    plugins: {{
                      legend: {{ labels: {{ font: {{ size: 10, family: 'Inter' }}, boxWidth: 12, padding: 8 }} }},
                      tooltip: {{ mode:'index', intersect:false }}
                    }},
                    scales: {{
                      x: {{
                        ticks: {{ font:{{size:9}}, maxRotation:45, autoSkip:true, maxTicksLimit:16 }},
                        grid: {{ color:'#f1f5f9' }}
                      }},
                      y: {{ ticks:{{font:{{size:9}}}}, grid:{{color:'#f1f5f9'}} }}
                    }}
                  }};

                  // ── Temperatura ──
                  new Chart(document.getElementById('cTemp'), {{
                    type: 'line',
                    data: {{
                      labels: labels,
                      datasets: [
                        {{ label:'Temperatura (°C)', data:temp, borderColor:'#f43f5e', backgroundColor:'rgba(244,63,94,0.08)', fill:true, tension:0.35, pointRadius:0, borderWidth:2 }},
                        {{ label:'Sensació (°C)',    data:feels, borderColor:'#fb923c', borderDash:[4,3], fill:false, tension:0.35, pointRadius:0, borderWidth:1.5 }}
                      ]
                    }},
                    options: JSON.parse(JSON.stringify(baseOpts))
                  }});

                  // ── Precipitació ──
                  var optPrecip = JSON.parse(JSON.stringify(baseOpts));
                  optPrecip.scales.y1 = {{ type:'linear', position:'right', min:0, max:100, ticks:{{font:{{size:9}}, callback:v=>v+'%'}}, grid:{{drawOnChartArea:false}} }};
                  new Chart(document.getElementById('cPrecip'), {{
                    type: 'bar',
                    data: {{
                      labels: labels,
                      datasets: [
                        {{ type:'bar',  label:'Precipitació (mm)', data:precip, backgroundColor:'rgba(14,165,233,0.7)', borderColor:'#0ea5e9', borderWidth:0.5, yAxisID:'y' }},
                        {{ type:'line', label:'Probabilitat (%)',   data:prob,   borderColor:'#6366f1', fill:false, tension:0.3, pointRadius:0, borderWidth:1.5, yAxisID:'y1', borderDash:[3,2] }}
                      ]
                    }},
                    options: optPrecip
                  }});

                  // ── Vent ──
                  new Chart(document.getElementById('cWind'), {{
                    type: 'line',
                    data: {{
                      labels: labels,
                      datasets: [
                        {{ label:'Vent (km/h)',   data:wind,  borderColor:'#10b981', backgroundColor:'rgba(16,185,129,0.08)', fill:true, tension:0.3, pointRadius:0, borderWidth:2 }},
                        {{ label:'Ratxes (km/h)', data:gusts, borderColor:'#059669', borderDash:[4,2], fill:false, tension:0.3, pointRadius:0, borderWidth:1.5 }}
                      ]
                    }},
                    options: JSON.parse(JSON.stringify(baseOpts))
                  }});

                  // ── Nuvolositat ──
                  var optCloud = JSON.parse(JSON.stringify(baseOpts));
                  optCloud.scales.y.min = 0; optCloud.scales.y.max = 100;
                  new Chart(document.getElementById('cCloud'), {{
                    type: 'line',
                    data: {{
                      labels: labels,
                      datasets: [
                        {{ label:'Nuvolositat (%)', data:cloud, borderColor:'#94a3b8', backgroundColor:'rgba(148,163,184,0.25)', fill:true, tension:0.4, pointRadius:0, borderWidth:1.5 }}
                      ]
                    }},
                    options: optCloud
                  }});

                </script>
                </body></html>
                """

                st.components.v1.html(chart_html, height=640, scrolling=False)

                # ── Resum numèric ─────────────────────────────────────────
                with st.expander("📊 Resum de les properes 48h", expanded=False):
                    t_clean = [x for x in temp if x is not None]
                    p_clean = [x for x in precip if x is not None]
                    w_clean = [x for x in gusts if x is not None]
                    mc1, mc2, mc3, mc4 = st.columns(4)
                    mc1.metric("T màx", f"{max(t_clean):.1f}°C")
                    mc2.metric("T mín", f"{min(t_clean):.1f}°C")
                    mc3.metric("Precip. total", f"{sum(p_clean):.1f} mm")
                    mc4.metric("Ratxa màx", f"{max(w_clean):.0f} km/h")

        except Exception as e:
            st.error(f"Error de connexió: {e}")

st.caption("Dades: Open-Meteo API · Météo-France AROME HD (1.3 km) · Actualització cada hora")
