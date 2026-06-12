import streamlit as st
import requests
import json
from datetime import datetime, timedelta, timezone

st.set_page_config(
    page_title="Meteograma GFS · Nivells de Pressió",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.block-container { padding: 1.2rem 1.8rem 2rem 1.8rem; max-width: 1300px; }

h1 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.25rem; font-weight: 600;
    color: #0f172a; letter-spacing: -0.3px; margin-bottom: 0;
}
.sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; color: #64748b; margin-top: 3px; margin-bottom: 1rem;
}
.info-pill {
    display:inline-block; background:#1e293b; color:#94a3b8;
    font-family:'IBM Plex Mono',monospace; font-size:0.7rem;
    padding:3px 10px; border-radius:3px; margin-bottom:0.8rem;
}
.day-header {
    font-family:'IBM Plex Mono',monospace; font-size:0.7rem;
    font-weight:600; color:#334155; text-transform:uppercase;
    letter-spacing:1px; padding: 4px 0 2px 0;
    border-bottom: 1px solid #e2e8f0; margin-bottom:2px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1>📡 Meteograma GFS · Nivells de Pressió</h1>', unsafe_allow_html=True)
st.markdown('<div class="sub">GFS 0.25° · Temperatura 400/500/850 hPa + Precipitació · Fins a 150 hores vista</div>', unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────
if "lat" not in st.session_state:
    st.session_state.lat = 41.6488
if "lon" not in st.session_state:
    st.session_state.lon = 0.5734  # Lleida com a defecte (zona interior típica)
if "data" not in st.session_state:
    st.session_state.data = None
if "fetch_now" not in st.session_state:
    st.session_state.fetch_now = True

col_map, col_right = st.columns([1, 2], gap="large")

# ══════════════════════════════════════════════════════════
# MAPA
# ══════════════════════════════════════════════════════════
with col_map:
    st.markdown("**Clica al mapa** per seleccionar punt:")

    map_html = f"""<!DOCTYPE html><html><head>
    <meta charset="utf-8"/>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
      body{{margin:0;padding:0;}}
      #map{{width:100%;height:400px;}}
      #info{{
        position:absolute;bottom:8px;left:50%;transform:translateX(-50%);
        background:rgba(15,23,42,0.88);color:#7dd3fc;
        font-family:monospace;font-size:11px;padding:4px 12px;
        border-radius:3px;z-index:1000;pointer-events:none;white-space:nowrap;
      }}
    </style>
    </head><body>
    <div id="map"></div>
    <div id="info">Lat: {st.session_state.lat:.4f} · Lon: {st.session_state.lon:.4f}</div>
    <script>
      var map = L.map('map').setView([41.7, 1.8], 7);
      L.tileLayer(
        'https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
        {{attribution:'OSM', maxZoom:12, subdomains:'abc'}}
      ).addTo(map);

      // Rectangle Catalunya aprox
      L.rectangle([[40.5,0.15],[42.9,3.35]],
        {{color:'#38bdf8',weight:1.2,fillOpacity:0.05,dashArray:'5'}}).addTo(map);

      var mk = L.circleMarker([{st.session_state.lat},{st.session_state.lon}],
        {{radius:7,color:'white',weight:2,fillColor:'#f43f5e',fillOpacity:1}}).addTo(map);

      map.on('click', function(e){{
        var la = e.latlng.lat.toFixed(4), lo = e.latlng.lng.toFixed(4);
        mk.setLatLng(e.latlng);
        document.getElementById('info').innerText = 'Lat: '+la+' · Lon: '+lo;
        window.parent.postMessage({{type:'streamlit:setComponentValue',value:la+','+lo}},'*');
      }});
    </script></body></html>"""

    st.components.v1.html(map_html, height=410)

    st.markdown("**O escriu les coordenades:**")
    c1, c2 = st.columns(2)
    with c1:
        lat_in = st.number_input("Latitud", value=st.session_state.lat, format="%.4f", step=0.05)
    with c2:
        lon_in = st.number_input("Longitud", value=st.session_state.lon, format="%.4f", step=0.05)

    forecast_h = st.slider("Hores de pronòstic", min_value=24, max_value=150, value=120, step=6)

    if st.button("🔄 Carregar dades GFS", type="primary", use_container_width=True):
        st.session_state.lat = lat_in
        st.session_state.lon = lon_in
        st.session_state.fetch_now = True
        st.rerun()

    st.markdown(f'<div class="info-pill">📍 {st.session_state.lat:.4f}°N &nbsp;·&nbsp; {st.session_state.lon:.4f}°E</div>', unsafe_allow_html=True)
    st.markdown("""
    **Nivells de pressió GFS:**
    - 🔴 **400 hPa** · ~7.2 km · troposfera alta
    - 🟠 **500 hPa** · ~5.6 km · nivell clàssic sinòptic
    - 🔵 **850 hPa** · ~1.5 km · baixa troposfera
    """)

# ══════════════════════════════════════════════════════════
# FETCH + METEOGRAMA
# ══════════════════════════════════════════════════════════
with col_right:
    if st.session_state.fetch_now:
        lat = st.session_state.lat
        lon = st.session_state.lon
        fdays = min(7, (forecast_h // 24) + 1)

        url = (
            f"https://api.open-meteo.com/v1/gfs"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly=temperature_850hPa,temperature_500hPa,temperature_400hPa,"
            f"precipitation,precipitation_probability"
            f"&models=gfs_seamless"
            f"&forecast_days={fdays}"
            f"&forecast_hours={forecast_h}"
            f"&timezone=Europe%2FMadrid"
        )

        with st.spinner("Descarregant GFS..."):
            try:
                r = requests.get(url, timeout=20)
                d = r.json()
                if "error" in d:
                    st.error(f"Error API: {d.get('reason', d)}")
                    st.stop()
                st.session_state.data = d
                st.session_state.fetch_now = False
            except Exception as e:
                st.error(f"Error de connexió: {e}")
                st.stop()

    if st.session_state.data is None:
        st.info("Clica 'Carregar dades GFS' per generar el meteograma.")
        st.stop()

    d = st.session_state.data
    h = d["hourly"]
    times_raw = h["time"]
    t850 = h["temperature_850hPa"]
    t500 = h["temperature_500hPa"]
    t400 = h["temperature_400hPa"]
    precip = h["precipitation"]
    prob = h.get("precipitation_probability", [None]*len(times_raw))

    # Agrupa per dies
    days_dict = {}
    for i, tr in enumerate(times_raw):
        dt = datetime.fromisoformat(tr)
        day_key = dt.strftime("%A %d %b")  # "Dilluns 13 Jun"
        if day_key not in days_dict:
            days_dict[day_key] = {"labels":[], "t850":[], "t500":[], "t400":[], "precip":[], "prob":[]}
        days_dict[day_key]["labels"].append(dt.strftime("%Hh"))
        days_dict[day_key]["t850"].append(t850[i])
        days_dict[day_key]["t500"].append(t500[i])
        days_dict[day_key]["t400"].append(t400[i])
        days_dict[day_key]["t850"].append if False else None
        days_dict[day_key]["precip"].append(precip[i])
        days_dict[day_key]["prob"].append(prob[i])

    def js(lst):
        return json.dumps([x if x is not None else "null" for x in lst])

    # Construeix JSON de dies per Chart.js
    days_json = json.dumps({k: v for k,v in days_dict.items()})

    chart_html = f"""<!DOCTYPE html><html><head>
<meta charset="utf-8"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  body {{ margin:0; padding:0; font-family:'IBM Plex Mono',monospace; background:transparent; }}
  .wrap {{ display:flex; flex-direction:column; gap:0; }}

  .day-block {{
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-bottom: 10px;
    overflow: hidden;
  }}
  .day-head {{
    background: #1e293b;
    color: #94a3b8;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 5px 14px;
  }}
  .charts-row {{
    display: flex;
    gap: 0;
    background: #fff;
  }}
  .chart-col {{
    flex: 2;
    padding: 8px 10px;
    border-right: 1px solid #f1f5f9;
  }}
  .chart-col-narrow {{
    flex: 1;
    padding: 8px 10px;
  }}
  .chart-label {{
    font-size: 9px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
  }}
  canvas {{ display:block; }}
</style>
</head><body>
<div class="wrap" id="root"></div>
<script>
var days = {days_json};
var root = document.getElementById('root');

var chartInstances = [];
var dayKeys = Object.keys(days);

dayKeys.forEach(function(dayName) {{
  var dd = days[dayName];

  var block = document.createElement('div');
  block.className = 'day-block';

  var head = document.createElement('div');
  head.className = 'day-head';
  head.textContent = dayName + '  ·  ' + dd.labels.length + ' passos';
  block.appendChild(head);

  var row = document.createElement('div');
  row.className = 'charts-row';

  // ── Temperatura nivells ──
  var colT = document.createElement('div');
  colT.className = 'chart-col';
  var lblT = document.createElement('div');
  lblT.className = 'chart-label';
  lblT.textContent = 'Temperatura (°C)  ·  400 / 500 / 850 hPa';
  colT.appendChild(lblT);
  var cvT = document.createElement('canvas');
  cvT.height = 80;
  colT.appendChild(cvT);
  row.appendChild(colT);

  // ── Precipitació ──
  var colP = document.createElement('div');
  colP.className = 'chart-col-narrow';
  var lblP = document.createElement('div');
  lblP.className = 'chart-label';
  lblP.textContent = 'Precip. (mm) / Prob. (%)';
  colP.appendChild(lblP);
  var cvP = document.createElement('canvas');
  cvP.height = 80;
  colP.appendChild(cvP);
  row.appendChild(colP);

  block.appendChild(row);
  root.appendChild(block);

  var baseOpts = {{
    responsive: true,
    animation: false,
    interaction: {{ mode:'index', intersect:false }},
    plugins: {{
      legend: {{ display:true, labels:{{ font:{{size:8,family:'IBM Plex Mono'}}, boxWidth:10, padding:6 }} }},
      tooltip: {{ bodyFont:{{size:9}}, titleFont:{{size:9}} }}
    }},
    scales: {{
      x: {{ ticks:{{ font:{{size:8}}, maxRotation:0, autoSkip:true, maxTicksLimit:8 }}, grid:{{color:'#f8fafc'}} }},
      y: {{ ticks:{{ font:{{size:8}} }}, grid:{{color:'#f1f5f9'}} }}
    }}
  }};

  // Temperatura chart
  var optT = JSON.parse(JSON.stringify(baseOpts));
  new Chart(cvT, {{
    type:'line',
    data:{{
      labels: dd.labels,
      datasets:[
        {{ label:'400 hPa (~7.2km)', data:dd.t400, borderColor:'#dc2626', fill:false, tension:0.35, pointRadius:0, borderWidth:2 }},
        {{ label:'500 hPa (~5.6km)', data:dd.t500, borderColor:'#f97316', fill:false, tension:0.35, pointRadius:0, borderWidth:2 }},
        {{ label:'850 hPa (~1.5km)', data:dd.t850, borderColor:'#3b82f6', fill:false, tension:0.35, pointRadius:0, borderWidth:2 }},
      ]
    }},
    options: optT
  }});

  // Precipitació chart
  var optP = JSON.parse(JSON.stringify(baseOpts));
  optP.scales.yProb = {{
    type:'linear', position:'right', min:0, max:100,
    ticks:{{ font:{{size:8}}, callback: function(v){{return v+'%';}} }},
    grid:{{ drawOnChartArea:false }}
  }};
  optP.plugins.legend.display = false;
  new Chart(cvP, {{
    type:'bar',
    data:{{
      labels: dd.labels,
      datasets:[
        {{ type:'bar',  label:'Precip (mm)', data:dd.precip, backgroundColor:'rgba(59,130,246,0.65)', borderColor:'#2563eb', borderWidth:0, yAxisID:'y' }},
        {{ type:'line', label:'Prob (%)',     data:dd.prob,   borderColor:'#8b5cf6', fill:false, tension:0.3, pointRadius:0, borderWidth:1.5, yAxisID:'yProb', borderDash:[3,2] }}
      ]
    }},
    options: optP
  }});
}});
</script>
</body></html>"""

    # Resum ràpid
    t850c = [x for x in t850 if x is not None]
    t500c = [x for x in t500 if x is not None]
    t400c = [x for x in t400 if x is not None]
    pc    = [x for x in precip if x is not None]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("T 850 hPa (rang)", f"{min(t850c):.0f} / {max(t850c):.0f} °C")
    m2.metric("T 500 hPa (rang)", f"{min(t500c):.0f} / {max(t500c):.0f} °C")
    m3.metric("T 400 hPa (rang)", f"{min(t400c):.0f} / {max(t400c):.0f} °C")
    m4.metric("Precip. acum.", f"{sum(pc):.1f} mm")

    st.markdown(f"**{len(times_raw)} passos temporals · {len(days_dict)} dies** — GFS Seamless 0.25°")

    st.components.v1.html(chart_html, height=len(days_dict)*145 + 40, scrolling=True)

    st.caption(f"Font: Open-Meteo · GFS NOAA 0.25° · Actualització cada 6h · {datetime.now().strftime('%d/%m/%Y %H:%M')}")
