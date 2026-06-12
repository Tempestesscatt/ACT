

import streamlit as st
import requests
import tempfile
import os
import warnings
import numpy as np
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

warnings.filterwarnings("ignore")
os.environ.setdefault("ECCODES_PYTHON_WARNINGS", "0")

try:
    import cfgrib
    import xarray as xr
    HAS_CFGRIB = True
except ImportError:
    HAS_CFGRIB = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec
    import matplotlib.dates as mdates
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ══════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════

TZ_MADRID   = ZoneInfo("Europe/Madrid")
MAX_RETRIES = 3
TIMEOUT     = 90

st.set_page_config(
    page_title="Meteograma GFS · Pressió",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.block-container { padding: 1rem 1.5rem 2rem 1.5rem; max-width: 1300px; }
h1 { font-family:'IBM Plex Mono',monospace; font-size:1.2rem; font-weight:600; color:#0f172a; margin-bottom:0; }
.sub { font-family:'IBM Plex Mono',monospace; font-size:0.7rem; color:#64748b; margin-top:2px; margin-bottom:0.8rem; }
.badge { display:inline-block; background:#1e293b; color:#7dd3fc; font-family:'IBM Plex Mono',monospace;
         font-size:0.68rem; padding:3px 10px; border-radius:3px; margin-bottom:0.6rem; }
.run-box { background:#f0fdf4; border-left:3px solid #22c55e; padding:6px 12px;
           border-radius:4px; font-size:0.78rem; color:#166534; margin-bottom:0.5rem; }
.err-box { background:#fef2f2; border-left:3px solid #ef4444; padding:6px 12px;
           border-radius:4px; font-size:0.78rem; color:#991b1b; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1>📡 Meteograma GFS · Nivells de Pressió</h1>', unsafe_allow_html=True)
st.markdown('<div class="sub">NOMADS NCEP · GFS 0.25° · Descàrrega GRIB2 directa · Sense API key · Fins 150h</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════
for k, v in [("lat", 41.6488), ("lon", 0.5734), ("data", None), ("run_info", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════
# RUN SELECTOR (igual que el teu script)
# ══════════════════════════════════════════════════════
def get_best_run():
    now_utc = datetime.now(timezone.utc)
    for delta_days in [0, -1]:
        d = now_utc + timedelta(days=delta_days)
        date_str = d.strftime('%Y%m%d')
        for run_h in [18, 12, 6, 0]:
            avail_h = 5 if run_h == 0 else 4.5
            run_dt  = datetime(d.year, d.month, d.day, run_h, tzinfo=timezone.utc)
            if now_utc >= run_dt + timedelta(hours=avail_h):
                return date_str, f"{run_h:02d}", run_dt
    yesterday = now_utc - timedelta(days=1)
    run_dt = datetime(yesterday.year, yesterday.month, yesterday.day, 18, tzinfo=timezone.utc)
    return yesterday.strftime('%Y%m%d'), '18', run_dt

def get_forecast_hours(base_dt, max_h=150, step=6):
    """Hores des de ara fins a max_h, pas step."""
    now_utc = datetime.now(timezone.utc)
    elapsed = (now_utc - base_dt).total_seconds() / 3600
    start_h = max(0, int(elapsed // step) * step)
    return list(range(start_h, max_h + 1, step))

# ══════════════════════════════════════════════════════
# DESCÀRREGA NOMADS (igual que el teu script)
# ══════════════════════════════════════════════════════
def download_grib(date_str, run_str, fhour, lat, lon, margin=2.0):
    """Baixa subregió GRIB2 de NOMADS per un punt (+/- margin)."""
    url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
    params = {
        'file':      f'gfs.t{run_str}z.pgrb2.0p25.f{fhour:03d}',
        'dir':       f'/gfs.{date_str}/{run_str}/atmos',
        'subregion': '',
        'leftlon':   str(max(-180, lon - margin)),
        'rightlon':  str(min(180,  lon + margin)),
        'toplat':    str(min(90,   lat + margin)),
        'bottomlat': str(max(-90,  lat - margin)),
        # Variables nivells de pressió
        'var_TMP':   'on',
        'var_APCP':  'on',  # precipitació acumulada (surface)
        'lev_400_mb': 'on',
        'lev_500_mb': 'on',
        'lev_850_mb': 'on',
        'lev_surface': 'on',
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=TIMEOUT)
            if r.status_code == 200 and len(r.content) > 500:
                return r.content
            elif r.status_code == 404:
                return None
        except Exception:
            pass
    return None

# ══════════════════════════════════════════════════════
# EXTRACCIO VALOR PUNTUAL DE GRIB2
# ══════════════════════════════════════════════════════
def extract_point(grib_bytes, filter_keys, var_candidates, target_lat, target_lon,
                  offset=0.0, scale=1.0):
    """Extreu el valor més proper a (lat, lon) del GRIB2."""
    if not HAS_CFGRIB or grib_bytes is None:
        return None
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.grib2', delete=False) as tmp:
            tmp.write(grib_bytes)
            tmp_path = tmp.name
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ds = xr.open_dataset(
                tmp_path, engine='cfgrib',
                filter_by_keys=filter_keys,
                backend_kwargs={'indexpath': ''}
            )
        name = next((c for c in var_candidates if c in ds.data_vars), None)
        if name is None:
            name = next((k for k in ds.data_vars for c in var_candidates
                         if c.lower() in k.lower()), None)
        if name is None:
            ds.close(); return None
        arr  = ds[name].values.astype(float)
        lats = ds['latitude'].values
        lons = ds['longitude'].values
        ds.close()
        while arr.ndim > 2:
            arr = arr[0]
        if lons.max() > 180:
            lons = np.where(lons > 180, lons - 360, lons)
        # Troba el punt més proper
        lon2d, lat2d = np.meshgrid(lons, lats)
        dist = (lat2d - target_lat)**2 + (lon2d - target_lon)**2
        ji = np.unravel_index(dist.argmin(), dist.shape)
        val = arr[ji]
        if np.isnan(val):
            return None
        return float(val) * scale + offset
    except Exception:
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except: pass

# ══════════════════════════════════════════════════════
# FETCH SÈRIE TEMPORAL
# ══════════════════════════════════════════════════════
def fetch_timeseries(date_str, run_str, base_dt, lat, lon, forecast_hours, progress_bar):
    """
    Per cada hora de forecast, baixa el GRIB2 i extreu:
      - T 850 hPa (°C)
      - T 500 hPa (°C)
      - T 400 hPa (°C)
      - Precipitació acumulada (mm) → diferencial entre passos
    """
    times   = []
    t850    = []
    t500    = []
    t400    = []
    precip_acum = []

    n = len(forecast_hours)
    for i, fhour in enumerate(forecast_hours):
        progress_bar.progress((i + 1) / n,
            text=f"Descarregant hora +{fhour}h ({i+1}/{n})…")

        grib = download_grib(date_str, run_str, fhour, lat, lon)
        dt_utc = base_dt + timedelta(hours=fhour)
        times.append(dt_utc.astimezone(TZ_MADRID))

        for arr, fk, cands, off in [
            (t850, {'typeOfLevel': 'isobaricInhPa', 'level': 850}, ['t', 'TMP'], -273.15),
            (t500, {'typeOfLevel': 'isobaricInhPa', 'level': 500}, ['t', 'TMP'], -273.15),
            (t400, {'typeOfLevel': 'isobaricInhPa', 'level': 400}, ['t', 'TMP'], -273.15),
        ]:
            v = extract_point(grib, fk, cands, lat, lon, offset=off)
            arr.append(v)

        p = extract_point(grib, {'typeOfLevel': 'surface'}, ['tp', 'APCP'], lat, lon)
        precip_acum.append(p if p is not None else 0.0)

        del grib

    # Converteix precipitació acumulada → incremental per pas
    precip_inc = [0.0]
    for i in range(1, len(precip_acum)):
        d = precip_acum[i] - precip_acum[i - 1]
        precip_inc.append(max(0.0, d))

    return {
        'times':   times,
        't850':    t850,
        't500':    t500,
        't400':    t400,
        'precip':  precip_inc,
        'date_str': date_str,
        'run_str':  run_str,
        'lat': lat, 'lon': lon,
    }

# ══════════════════════════════════════════════════════
# METEOGRAMA
# ══════════════════════════════════════════════════════
def plot_meteogram(data):
    times  = data['times']
    t850   = data['t850']
    t500   = data['t500']
    t400   = data['t400']
    precip = data['precip']
    lat    = data['lat']
    lon    = data['lon']
    run    = f"GFS {data['date_str']} {data['run_str']}Z"

    # Filtra Nones
    def clean(arr):
        return [x if x is not None else np.nan for x in arr]

    t850c = clean(t850); t500c = clean(t500); t400c = clean(t400)

    # Agrupa per dies per les línies divisòries
    day_changes = []
    prev_day = None
    for i, t in enumerate(times):
        if t.day != prev_day:
            if prev_day is not None:
                day_changes.append(i)
            prev_day = t.day

    fig = plt.figure(figsize=(14, 7), facecolor='#f8fafc')
    gs  = gridspec.GridSpec(2, 1, height_ratios=[2.5, 1], hspace=0.08)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)

    # ── Panel superior: temperatures ────────────────────────────
    ax1.set_facecolor('#f8fafc')
    ax1.spines[['top', 'right']].set_visible(False)
    ax1.spines[['left', 'bottom']].set_color('#cbd5e1')

    t_arr = np.array([(t - times[0]).total_seconds() / 3600 for t in times])

    def plot_temp(ax, arr, color, label, lw=2.0, ls='-', alpha=1.0):
        x = []; y = []
        for xi, yi in zip(t_arr, arr):
            if not np.isnan(yi):
                x.append(xi); y.append(yi)
        if x:
            ax.plot(x, y, color=color, linewidth=lw, linestyle=ls,
                    label=label, alpha=alpha, solid_capstyle='round')

    plot_temp(ax1, t400c, '#dc2626', '400 hPa (~7.2km)', lw=2.2)
    plot_temp(ax1, t500c, '#f97316', '500 hPa (~5.6km)', lw=2.2)
    plot_temp(ax1, t850c, '#3b82f6', '850 hPa (~1.5km)', lw=2.2)

    # Àrees de fons: dia/nit
    for i, t in enumerate(times):
        if i < len(times) - 1:
            h = t.hour
            if h >= 21 or h < 7:
                x0 = t_arr[i]; x1 = t_arr[i + 1]
                ax1.axvspan(x0, x1, color='#1e293b', alpha=0.04, zorder=0)

    # Línies de dia
    for idx in day_changes:
        x = t_arr[idx]
        ax1.axvline(x, color='#94a3b8', lw=0.8, ls='--', alpha=0.6)
        ax2.axvline(x, color='#94a3b8', lw=0.8, ls='--', alpha=0.6)

    # Grid horitzontal
    ax1.yaxis.grid(True, color='#e2e8f0', linewidth=0.6, zorder=0)
    ax1.set_axisbelow(True)
    ax1.set_ylabel('Temperatura (°C)', fontsize=9, color='#475569', labelpad=8)

    # Llegenda
    leg = ax1.legend(loc='upper right', fontsize=8.5,
                     frameon=True, framealpha=0.9,
                     edgecolor='#e2e8f0', facecolor='white')

    # Títol
    now_mad = datetime.now(timezone.utc).astimezone(TZ_MADRID).strftime('%d/%m/%Y %H:%M %Z')
    ax1.set_title(
        f'Meteograma GFS · {lat:.3f}°N {lon:.3f}°E\n'
        f'{run} · Generat: {now_mad}',
        fontsize=9.5, color='#1e293b', loc='left', pad=10,
        fontfamily='monospace'
    )
    ax1.set_title('NOMADS NCEP · Sense API key', fontsize=7.5,
                  color='#94a3b8', loc='right', pad=10)

    # ── Panel inferior: precipitació ─────────────────────────────
    ax2.set_facecolor('#f0f9ff')
    ax2.spines[['top', 'right']].set_visible(False)
    ax2.spines[['left', 'bottom']].set_color('#cbd5e1')

    bar_w = t_arr[1] - t_arr[0] if len(t_arr) > 1 else 6
    colors_bar = ['#1d4ed8' if p < 5 else '#2563eb' if p < 15
                  else '#1e40af' if p < 30 else '#1e3a8a' for p in precip]
    ax2.bar(t_arr, precip, width=bar_w * 0.85, color=colors_bar,
            alpha=0.75, align='center', zorder=3)
    ax2.yaxis.grid(True, color='#bae6fd', linewidth=0.5, zorder=0)
    ax2.set_axisbelow(True)
    ax2.set_ylabel('Precip.\n(mm/pas)', fontsize=8, color='#475569', labelpad=8)

    # Màxim precipitació
    max_p = max(precip) if precip else 0
    ax2.set_ylim(bottom=0, top=max(max_p * 1.3, 2))

    # ── Eix X compartit: etiquetes de dia + hora ──────────────────
    tick_pos = []; tick_labels = []
    for i, t in enumerate(times):
        if t.hour in [0, 6, 12, 18]:
            tick_pos.append(t_arr[i])
            if t.hour == 0:
                tick_labels.append(t.strftime('%a\n%d/%m'))
            else:
                tick_labels.append(t.strftime('%Hh'))

    ax2.set_xticks(tick_pos)
    ax2.set_xticklabels(tick_labels, fontsize=7.5, color='#475569')
    plt.setp(ax1.get_xticklabels(), visible=False)

    ax2.set_xlabel('Hora local Madrid', fontsize=8, color='#475569')
    ax1.set_xlim(t_arr[0] - bar_w / 2, t_arr[-1] + bar_w / 2)

    # Línies de referència temperatura
    for ref_t, col, ls in [(0, '#94a3b8', ':'), (-20, '#bae6fd', ':')]:
        for ax in [ax1]:
            ax.axhline(ref_t, color=col, lw=0.8, ls=ls, alpha=0.7)

    # Marca de 0°C
    ax1.text(t_arr[-1] + bar_w * 0.3, 0, '0°C', fontsize=7,
             color='#94a3b8', va='center')

    # Copyright
    fig.text(0.99, 0.01, '© tempestes.cat · GFS NOAA',
             ha='right', va='bottom', fontsize=6.5,
             color='#94a3b8', style='italic')

    plt.tight_layout(pad=1.2)
    return fig

# ══════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════
col_map, col_right = st.columns([1, 2.2], gap="large")

with col_map:
    st.markdown("**Selecciona el punt al mapa:**")

    lat_v = st.session_state.lat
    lon_v = st.session_state.lon

    map_html = f"""<!DOCTYPE html><html><head>
    <meta charset="utf-8"/>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
      body{{margin:0;padding:0;}}
      #map{{width:100%;height:380px;}}
      #info{{position:absolute;bottom:8px;left:50%;transform:translateX(-50%);
        background:rgba(15,23,42,0.85);color:#7dd3fc;font-family:monospace;
        font-size:11px;padding:4px 12px;border-radius:3px;z-index:1000;
        pointer-events:none;white-space:nowrap;}}
    </style></head><body>
    <div id="map"></div>
    <div id="info">Lat: {lat_v:.4f} · Lon: {lon_v:.4f}</div>
    <script>
      var map = L.map('map').setView([{lat_v},{lon_v}],6);
      L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
        {{attribution:'OSM',maxZoom:12,subdomains:'abc'}}).addTo(map);
      L.rectangle([[35.0,-6.0],[44.0,5.0]],
        {{color:'#38bdf8',weight:1.2,fillOpacity:0.04,dashArray:'5'}}).addTo(map);
      var mk = L.circleMarker([{lat_v},{lon_v}],
        {{radius:8,color:'white',weight:2.5,fillColor:'#f43f5e',fillOpacity:1}}).addTo(map);
      map.on('click',function(e){{
        var la=e.latlng.lat.toFixed(4), lo=e.latlng.lng.toFixed(4);
        mk.setLatLng(e.latlng);
        document.getElementById('info').innerText='Lat: '+la+' · Lon: '+lo;
        window.parent.postMessage({{type:'streamlit:setComponentValue',value:la+','+lo}},'*');
      }});
    </script></body></html>"""

    st.components.v1.html(map_html, height=390)

    st.markdown("**O escriu les coordenades:**")
    c1, c2 = st.columns(2)
    with c1:
        lat_in = st.number_input("Latitud", value=lat_v, format="%.4f", step=0.1)
    with c2:
        lon_in = st.number_input("Longitud", value=lon_v, format="%.4f", step=0.1)

    max_h = st.select_slider(
        "Horitzó de pronòstic",
        options=[24, 48, 72, 96, 120, 150],
        value=120
    )
    step_h = st.radio("Pas temporal", [3, 6, 12], index=1, horizontal=True)

    st.markdown("---")
    btn = st.button("📥 Descarregar GFS i generar meteograma",
                    type="primary", use_container_width=True)

    # Info del run disponible
    date_str, run_str, base_dt = get_best_run()
    run_local = base_dt.astimezone(TZ_MADRID).strftime('%d/%m %H:%M %Z')
    st.markdown(f'<div class="run-box">🛰 Run disponible: <b>GFS {date_str} {run_str}Z</b> ({run_local})</div>',
                unsafe_allow_html=True)

    if not HAS_CFGRIB:
        st.markdown('<div class="err-box">⚠️ cfgrib no instal·lat — instal·la el requirements.txt</div>',
                    unsafe_allow_html=True)
    if not HAS_MPL:
        st.markdown('<div class="err-box">⚠️ matplotlib no instal·lat</div>',
                    unsafe_allow_html=True)

    st.markdown("""
**Nivells:**
- 🔴 400 hPa · ~7.2 km · troposfera alta  
- 🟠 500 hPa · ~5.6 km · sinòptic clàssic  
- 🔵 850 hPa · ~1.5 km · baixa troposfera  
- 🌧 Precipitació incremental per pas
    """)

# ══════════════════════════════════════════════════════
# FETCH + PLOT
# ══════════════════════════════════════════════════════
with col_right:
    st.markdown(f'<div class="badge">📍 {st.session_state.lat:.4f}°N &nbsp;·&nbsp; {st.session_state.lon:.4f}°E</div>',
                unsafe_allow_html=True)

    if btn:
        if not HAS_CFGRIB:
            st.error("cfgrib no disponible. Instal·la requirements.txt primer.")
            st.stop()

        st.session_state.lat = lat_in
        st.session_state.lon = lon_in
        lat = lat_in; lon = lon_in

        forecast_hours = get_forecast_hours(base_dt, max_h=max_h, step=step_h)
        n_hours = len(forecast_hours)

        st.info(f"Descarregant {n_hours} passos GFS ({min(forecast_hours)}h → {max(forecast_hours)}h, pas {step_h}h)…")
        prog = st.progress(0, text="Iniciant descàrrega NOMADS…")

        try:
            data = fetch_timeseries(date_str, run_str, base_dt, lat, lon,
                                    forecast_hours, prog)
            prog.empty()
            st.session_state.data = data
            st.success(f"✅ {n_hours} passos descarregats correctament")
        except Exception as e:
            prog.empty()
            st.error(f"Error en la descàrrega: {e}")
            st.stop()

    if st.session_state.data is not None:
        data = st.session_state.data

        # Mètriques ràpides
        t850c = [x for x in data['t850'] if x is not None]
        t500c = [x for x in data['t500'] if x is not None]
        t400c = [x for x in data['t400'] if x is not None]
        pc    = [x for x in data['precip'] if x is not None]

        m1, m2, m3, m4 = st.columns(4)
        if t850c: m1.metric("850 hPa (rang)", f"{min(t850c):.1f} / {max(t850c):.1f} °C")
        if t500c: m2.metric("500 hPa (rang)", f"{min(t500c):.1f} / {max(t500c):.1f} °C")
        if t400c: m3.metric("400 hPa (rang)", f"{min(t400c):.1f} / {max(t400c):.1f} °C")
        if pc:    m4.metric("Precip. total", f"{sum(pc):.1f} mm")

        with st.spinner("Generant meteograma…"):
            fig = plot_meteogram(data)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        st.caption(
            f"Font: NOMADS NCEP · GFS 0.25° · "
            f"Run {data['date_str']} {data['run_str']}Z · "
            f"{len(data['times'])} passos · "
            f"Generat: {datetime.now(TZ_MADRID).strftime('%d/%m/%Y %H:%M %Z')}"
        )
    else:
        st.markdown("""
        <div style="display:flex;align-items:center;justify-content:center;
                    height:400px;color:#94a3b8;font-family:monospace;font-size:0.85rem;
                    background:#f8fafc;border:1px dashed #e2e8f0;border-radius:8px;
                    flex-direction:column;gap:8px;">
            <div style="font-size:2rem">📡</div>
            <div>Selecciona un punt al mapa</div>
            <div style="font-size:0.72rem">i clica "Descarregar GFS"</div>
        </div>
        """, unsafe_allow_html=True)
