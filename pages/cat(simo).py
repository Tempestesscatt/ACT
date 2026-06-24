import streamlit as st
import requests
from PIL import Image
from io import BytesIO
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from datetime import datetime, timedelta
import time
import random

# Configuració de la pàgina
st.set_page_config(
    page_title="Radar Meteocat - Catalunya",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Títol principal
st.title("🌦️ Radar Meteorològic de Catalunya")
st.markdown("Dades en temps real del [Servei Meteorològic de Catalunya](https://www.meteo.cat/observacions/radar)")

# Configuració de la graella de tiles
TILE_CONFIG = {
    'min_x': 124,    # Tile més a l'oest
    'max_x': 133,    # Tile més a l'est  
    'min_y': 157,    # Tile més al nord
    'max_y': 164,    # Tile més al sud
    'base_params': '6/08/000/000',  # Paràmetres fixos de la URL
    'tile_size': 256  # Píxels per tile
}

# Extensió geogràfica real de la imatge combinada
# Aquests valors s'han de calibrar amb la cobertura real
GEO_EXTENT = {
    'lon_min': -0.5,   # Longitud oest
    'lon_max': 4.5,    # Longitud est
    'lat_min': 38.5,   # Latitud sud  
    'lat_max': 44.0    # Latitud nord
}

# Headers per evitar bloquejos del servidor
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
    'Accept-Language': 'ca,es;q=0.9,en;q=0.8',
    'Referer': 'https://www.meteo.cat/observacions/radar',
    'Origin': 'https://www.meteo.cat',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

# Crear una sessió persistent per millorar el rendiment
session = requests.Session()
session.headers.update(HEADERS)

def descarregar_tile(url, max_intents=3):
    """
    Descarrega un tile individual amb reintents i backoff exponencial
    """
    for intent in range(max_intents):
        try:
            # Delay aleatori per semblar tràfic humà
            time.sleep(random.uniform(0.05, 0.2))
            
            response = session.get(url, timeout=15)
            
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
            elif response.status_code == 404:
                return None  # Tile no existeix
            elif response.status_code == 403:
                st.warning(f"⚠️ Accés bloquejat - intent {intent + 1}/{max_intents}")
                time.sleep(2 ** intent)
            else:
                st.warning(f"⚠️ Error {response.status_code} - intent {intent + 1}/{max_intents}")
                time.sleep(1)
                
        except requests.exceptions.Timeout:
            st.warning(f"⏰ Timeout - intent {intent + 1}/{max_intents}")
            time.sleep(1)
        except Exception as e:
            st.warning(f"❌ Error: {str(e)[:50]} - intent {intent + 1}/{max_intents}")
            time.sleep(1)
    
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def descarregar_radar_sencer(date_str, hour, minute):
    """
    Descarrega tots els tiles que formen la imatge completa del radar
    """
    tiles_descarregats = {}
    errors = []
    
    cols = TILE_CONFIG['max_x'] - TILE_CONFIG['min_x'] + 1
    rows = TILE_CONFIG['max_y'] - TILE_CONFIG['min_y'] + 1
    total_tiles = cols * rows
    
    progress_bar = st.progress(0, text="Iniciant descàrrega...")
    contador = 0
    
    for y in range(TILE_CONFIG['min_y'], TILE_CONFIG['max_y'] + 1):
        for x in range(TILE_CONFIG['min_x'], TILE_CONFIG['max_x'] + 1):
            # Construir URL seguint el patró exacte
            url = (f"https://static-m.meteo.cat/tiles/combinada/"
                   f"{date_str}/{hour}/{minute}/"
                   f"{TILE_CONFIG['base_params']}/"
                   f"{x}/000/000/{y}.png")
            
            # Actualitzar progrés
            contador += 1
            progress_bar.progress(
                contador / total_tiles,
                text=f"Descarregant tile {contador}/{total_tiles} ({x},{y})"
            )
            
            # Descarregar tile
            tile = descarregar_tile(url)
            
            if tile:
                tiles_descarregats[(x, y)] = tile
            else:
                errors.append((x, y))
    
    # Informe final
    if errors:
        progress_bar.progress(100, text=f"✅ {len(tiles_descarregats)}/{total_tiles} tiles | ⚠️ {len(errors)} errors")
    else:
        progress_bar.progress(100, text=f"✅ Tots els tiles descarregats ({total_tiles})")
    
    return tiles_descarregats, errors

def crear_imatge_completa(tiles):
    """
    Combina tots els tiles en una única imatge
    """
    if not tiles:
        return None
    
    cols = TILE_CONFIG['max_x'] - TILE_CONFIG['min_x'] + 1
    rows = TILE_CONFIG['max_y'] - TILE_CONFIG['min_y'] + 1
    
    # Crear imatge buida amb fons transparent
    img_completa = Image.new('RGBA', 
                             (cols * TILE_CONFIG['tile_size'], 
                              rows * TILE_CONFIG['tile_size']), 
                             (0, 0, 0, 0))
    
    # Col·locar cada tile a la seva posició correcta
    for (x, y), tile in tiles.items():
        col = x - TILE_CONFIG['min_x']
        row = y - TILE_CONFIG['min_y']
        pos_x = col * TILE_CONFIG['tile_size']
        pos_y = row * TILE_CONFIG['tile_size']
        img_completa.paste(tile, (pos_x, pos_y))
    
    return img_completa

def crear_mapa_cartopy(imatge_radar, titol):
    """
    Crea un mapa amb Cartopy i superposa el radar
    """
    fig = plt.figure(figsize=(14, 10))
    ax = plt.axes(projection=ccrs.PlateCarree())
    
    # Definir l'àrea geogràfica
    ax.set_extent([
        GEO_EXTENT['lon_min'], 
        GEO_EXTENT['lon_max'],
        GEO_EXTENT['lat_min'], 
        GEO_EXTENT['lat_max']
    ], crs=ccrs.PlateCarree())
    
    # Afegir elements geogràfics
    ax.add_feature(cfeature.LAND, facecolor='#2d2d2d', alpha=0.3)
    ax.add_feature(cfeature.OCEAN, facecolor='#1a1a2e', alpha=0.5)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor='white', alpha=0.6)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5, edgecolor='white', alpha=0.4, linestyle='--')
    
    # Afegir gridlines
    gl = ax.gridlines(
        draw_labels=True, 
        linewidth=0.5, 
        color='gray', 
        alpha=0.3, 
        linestyle='--'
    )
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 8, 'color': 'gray'}
    gl.ylabel_style = {'size': 8, 'color': 'gray'}
    
    # Superposar la imatge del radar
    if imatge_radar:
        # Convertir a array numpy
        img_array = np.array(imatge_radar)
        
        # Extensió geogràfica de la imatge
        extent = [
            GEO_EXTENT['lon_min'], 
            GEO_EXTENT['lon_max'],
            GEO_EXTENT['lat_min'], 
            GEO_EXTENT['lat_max']
        ]
        
        # Mostrar imatge amb transparència
        ax.imshow(
            img_array, 
            extent=extent, 
            transform=ccrs.PlateCarree(),
            alpha=0.75,
            zorder=10,
            interpolation='bilinear'
        )
    
    # Títol i estil
    ax.set_title(titol, fontsize=14, fontweight='bold', pad=20)
    
    # Fons fosc
    fig.patch.set_facecolor('#0e1117')
    ax.set_facecolor('#0e1117')
    
    plt.tight_layout()
    return fig

def obtenir_ultima_hora_disponible():
    """
    Calcula l'última hora disponible arrodonida als 6 minuts
    """
    # El radar s'actualitza cada 6 minuts, amb un retard d'uns 5-10 minuts
    ara = datetime.utcnow() - timedelta(minutes=8)  # Marge de retard
    minut_arrodonit = (ara.minute // 6) * 6
    return ara.replace(minute=minut_arrodonit, second=0, microsecond=0)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("🎛️ Controls del Radar")
    st.divider()
    
    # Obtenir última hora disponible
    ultima_hora = obtenir_ultima_hora_disponible()
    
    # Selectors de data i hora
    st.subheader("📅 Data i Hora")
    
    col1, col2 = st.columns(2)
    with col1:
        data_seleccionada = st.date_input(
            "Data",
            value=ultima_hora.date(),
            max_value=datetime.utcnow().date()
        )
    
    with col2:
        hores_disponibles = list(range(24))
        hora_seleccionada = st.selectbox(
            "Hora (UTC)",
            hores_disponibles,
            index=ultima_hora.hour
        )
    
    minuts_disponibles = list(range(0, 60, 6))
    minut_seleccionat = st.selectbox(
        "Minuts",
        minuts_disponibles,
        index=ultima_hora.minute // 6
    )
    
    # Formatar data i hora
    data_str = data_seleccionada.strftime("%Y/%m/%d")
    hora_str = f"{hora_seleccionada:02d}"
    minut_str = f"{minut_seleccionat:02d}"
    
    # Informació de la selecció
    st.info(f"📡 **Selecció:** {data_str} {hora_str}:{minut_str} UTC")
    
    # Botons d'acció
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        boto_carregar = st.button(
            "🔄 Carregar",
            type="primary",
            use_container_width=True
        )
    
    with col2:
        boto_ultim = st.button(
            "🕐 Últim",
            type="secondary",
            use_container_width=True
        )
    
    if boto_ultim:
        # Actualitzar a l'última hora disponible
        st.session_state.data_radar = ultima_hora.strftime("%Y/%m/%d")
        st.session_state.hora_radar = f"{ultima_hora.hour:02d}"
        st.session_state.minut_radar = f"{ultima_hora.minute:02d}"
        st.session_state.carregar = True
        st.rerun()
    
    if boto_carregar:
        st.session_state.data_radar = data_str
        st.session_state.hora_radar = hora_str
        st.session_state.minut_radar = minut_str
        st.session_state.carregar = True
    
    # Informació addicional
    st.divider()
    st.subheader("ℹ️ Informació")
    st.markdown("""
    - 🔄 Actualització: **cada 6 minuts**
    - 🌍 Cobertura: **Catalunya, Balears, Sud França**
    - 📡 Font: **Servei Meteorològic de Catalunya**
    - ⏰ Hora: **UTC**
    """)
    
    # Llegenda de colors
    st.divider()
    st.subheader("🎨 Intensitat de Precipitació")
    
    colors_llegenda = [
        ("🟢", "Molt fluixa"),
        ("🟡", "Fluixa"),
        ("🟠", "Moderada"),
        ("🔴", "Forta"),
        ("🟣", "Molt forta"),
        ("⚪", "Granís o calamarsa"),
    ]
    
    for emoji, descripcio in colors_llegenda:
        st.markdown(f"{emoji} **{descripcio}**")
    
    # Crèdits
    st.divider()
    st.markdown(
        "<small>Desenvolupat amb Streamlit, Cartopy i Matplotlib</small>", 
        unsafe_allow_html=True
    )

# ==================== CONTINGUT PRINCIPAL ====================

# Inicialitzar estat de sessió
if 'carregar' not in st.session_state:
    st.session_state.carregar = False
    # Per defecte, carregar l'última hora disponible
    ultima = obtenir_ultima_hora_disponible()
    st.session_state.data_radar = ultima.strftime("%Y/%m/%d")
    st.session_state.hora_radar = f"{ultima.hour:02d}"
    st.session_state.minut_radar = f"{ultima.minute:02d}"
    st.session_state.carregar = True

# Carregar i mostrar radar
if st.session_state.carregar:
    data = st.session_state.data_radar
    hora = st.session_state.hora_radar
    minut = st.session_state.minut_radar
    
    st.markdown(f"### 📡 Radar del {data} a les {hora}:{minut} UTC")
    
    # Descarregar tiles
    with st.spinner(f"⏳ Descarregant dades del radar..."):
        tiles, errors = descarregar_radar_sencer(data, hora, minut)
    
    if tiles:
        # Crear imatge completa
        with st.spinner("🎨 Processant imatge..."):
            imatge_radar = crear_imatge_completa(tiles)
        
        if imatge_radar:
            # Crear pestanyes per diferents visualitzacions
            tab1, tab2 = st.tabs(["🗺️ Mapa amb Cartopy", "📸 Imatge Directa"])
            
            with tab1:
                # Mostrar mapa amb Cartopy
                titol = f"Radar Meteorològic - {data} {hora}:{minut} UTC"
                fig = crear_mapa_cartopy(imatge_radar, titol)
                st.pyplot(fig)
            
            with tab2:
                # Mostrar imatge crua
                st.image(
                    imatge_radar, 
                    caption=f"Imatge del radar - {data} {hora}:{minut} UTC",
                    use_column_width=True
                )
            
            # Estadístiques
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Tiles descarregats", f"{len(tiles)}")
            with col2:
                mida_mb = imatge_radar.size[0] * imatge_radar.size[1] * 4 / (1024 * 1024)
                st.metric("Resolució", f"{imatge_radar.size[0]}x{imatge_radar.size[1]}")
            with col3:
                st.metric("Errors", f"{len(errors)}")
            
            # Botó per descarregar la imatge
            buf = BytesIO()
            imatge_radar.save(buf, format='PNG')
            st.download_button(
                label="💾 Descarregar Imatge PNG",
                data=buf.getvalue(),
                file_name=f"radar_mtc_{data.replace('/', '')}_{hora}{minut}.png",
                mime="image/png",
                use_container_width=True
            )
        else:
            st.error("❌ No s'ha pogut crear la imatge del radar")
    else:
        st.error(f"❌ No s'han pogut descarregar els tiles del radar")
        st.info("💡 Consells:\n"
                "- Comprova que la data i hora siguin correctes\n"
                "- El radar pot no estar disponible per dates futures\n"
                "- Prova amb l'opció 'Últim' per veure el radar més recent")
    
    # Reset
    st.session_state.carregar = False

# Peu de pàgina
st.divider()
st.markdown(
    "<p style='text-align: center; color: gray;'>"
    "📡 Dades del <a href='https://www.meteo.cat/observacions/radar' style='color: #ff6b35;'>"
    "Servei Meteorològic de Catalunya</a> | "
    "Desenvolupat amb ❤️ i Python"
    "</p>", 
    unsafe_allow_html=True
)
