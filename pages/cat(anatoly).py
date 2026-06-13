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
    padding-top: 1rem;
    max-width: 100%;
}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("🌦️ Lameteo.cat · Visor meteorològic professional")
st.caption("Radar, satèl·lit i models meteorològics separats en pestanyes.")

tab1, tab2, tab3 = st.tabs(["🌧️ Radar", "🛰️ Satèl·lit", "🌍 Model europeu"])

with tab1:
    st.subheader("🌧️ Radar de pluja en directe")
    radar_html = """
    <iframe 
    src="https://www.rainviewer.com/map.html?loc=41.65,1.8,7&oFa=0&oC=1&oU=0&oCS=1&oF=0&oAP=1&c=1&o=83&lm=1&layer=radar&sm=1&sn=1"
    style="width:100%;height:820px;border:0;border-radius:22px;overflow:hidden;">
    </iframe>
    """
    components.html(radar_html, height=850)

with tab2:
    st.subheader("🛰️ Satèl·lit EUMETSAT")
    sat_layer = st.selectbox(
        "Capa de satèl·lit",
        {
            "Color natural": "msg_fes:rgb_natural",
            "Infraroig IR 10.8": "msg_fes:ir108",
            "Airmass RGB": "msg_fes:airmass",
            "Dust RGB": "msg_fes:dust",
            "Vapor d’aigua": "msg_fes:wv062"
        }
    )

    sat_html = f"""
    <html>
    <head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
    body {{margin:0;background:#07111f;}}
    #map {{height:820px;border-radius:22px;overflow:hidden;}}
    </style>
    </head>
    <body>
    <div id="map"></div>
    <script>
    const map = L.map('map').setView([46, 7], 4);

    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      attribution: 'OpenStreetMap · CartoDB'
    }}).addTo(map);

    L.tileLayer.wms('https://view.eumetsat.int/geoserver/ows', {{
      layers: '{sat_layer}',
      format: 'image/png',
      transparent: true,
      opacity: 0.85,
      attribution: 'EUMETSAT'
    }}).addTo(map);
    </script>
    </body>
    </html>
    """
    components.html(sat_html, height=850)

with tab3:
    st.subheader("🌍 Model europeu ECMWF")
    model_layer = st.selectbox(
        "Variable del model europeu",
        {
            "Pressió nivell del mar": "msl_public",
            "Temperatura 850 hPa": "t850_public",
            "Geopotencial 500 hPa": "z500_public",
            "Vent 850 hPa": "ws850_public",
            "Ensemble Z500 mitjana": "z500_mean_public",
            "Ensemble T850 mitjana": "t850_mean_public",
            "Ensemble MSLP mitjana": "msl_mean_public"
        }
    )

    model_html = f"""
    <html>
    <head>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
    body {{margin:0;background:#07111f;}}
    #map {{height:820px;border-radius:22px;overflow:hidden;}}
    </style>
    </head>
    <body>
    <div id="map"></div>
    <script>
    const map = L.map('map').setView([44, 3], 5);

    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      attribution: 'OpenStreetMap · CartoDB'
    }}).addTo(map);

    L.tileLayer.wms('https://eccharts.ecmwf.int/wms/', {{
      layers: '{model_layer}',
      format: 'image/png',
      transparent: true,
      opacity: 0.78,
      attribution: 'ECMWF'
    }}).addTo(map);
    </script>
    </body>
    </html>
    """
    components.html(model_html, height=850)

st.info("⚠️ Si alguna capa ECMWF o EUMETSAT no carrega, pot requerir API, token o permisos del compte.")
