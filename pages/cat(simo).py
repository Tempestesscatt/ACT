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

st.set_page_config(
    page_title="Radar Meteocat - Catalunya",
    page_icon="🌦️",
    layout="wide"
)

st.title("🌦️ Radar Meteorològic de Catalunya")
st.markdown("Dades del radar del [Meteocat](https://www.meteo.cat/observacions/radar)")

# Configuració de la graella de tiles
TILE_CONFIG = {
    'min_x': 124,
    'max_x': 133,
    'min_y': 157,
    'max_y': 164,
    'base_params': '6/08/000/000',  # Paràmetres fixos
    'tile_size': 256
}

# Headers per evitar bans
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
    'Accept-Language': 'ca,es;q=0.9,en;q=0.8',
    'Referer': 'https://www.meteo.cat/observacions/radar',
    'Origin': 'https://www.meteo.cat',
    'Connection': 'keep-alive',
}

def download_tile_with_retry(url, max_retries=3):
    """Descarrega un tile amb reintents i backoff exponencial"""
    for attempt in range(max_retries):
        try:
            # Afegir delay aleatori per semblar humà
            time.sleep(random.uniform(0.1, 0.3))
            
            response = requests.get(url, headers=HEADERS, timeout=10)
            
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
            elif response.status_code == 403:
                st.warning(f"⚠️ Accés bloquejat (403) - intent {attempt + 1}/{max_retries}")
                time.sleep(2 ** attempt)  # Backoff exponencial
            elif response.status_code == 404:
                return None  # Tile no disponible
            else:
                time.sleep(1)
                
        except Exception as e:
            st.warning(f"⚠️ Error descarregant tile: {e} - intent {attempt + 1}/{max_retries}")
            time.sleep(1)
    
    return None

def download_radar_tiles(date_str, hour, minute):
    """Descarrega tots els tiles del radar per una data/hora concreta"""
    
    tiles = {}
    cols = TILE_CONFIG['max_x'] - TILE_CONFIG['min_x'] + 1
    rows = TILE_CONFIG['max_y'] - TILE_CONFIG['min_y'] + 1
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_tiles = cols * rows
    downloaded = 0
    
    for y_idx, y in enumerate(range(TILE_CONFIG['min_y'], TILE_CONFIG['max_y'] + 1)):
        for x_idx, x in enumerate(range(TILE_CONFIG['min_x'], TILE_CONFIG['max_x'] + 1)):
            url = f"https://static-m.meteo.cat/tiles/combinada/{date_str}/{hour}/{minute}/{TILE_CONFIG['base_params']}/{x}/000/000/{y}.png"
            
            status_text.text(f"Descarregant tile ({x}, {y})... {downloaded}/{total_tiles}")
            
            tile = download_tile_with_retry(url)
            if tile:
                tiles[(x, y)] = tile
                downloaded += 1
            
            progress_bar.progress((downloaded) / total_tiles)
            time.sleep(0.05)  # Petit delay per no saturar el servidor
    
    status_text.text(f"✅ Descarregats {downloaded}/{total_tiles} tiles")
    return tiles

def create_radar_image(tiles):
    """Crea una imatge completa a partir dels tiles descarregats"""
    
    if not tiles:
        return None
    
    cols = TILE_CONFIG['max_x'] - TILE_CONFIG['min_x'] + 1
    rows = TILE_CONFIG['max_y'] - TILE_CONFIG['min_y'] + 1
    
    # Crear imatge buida
    full_img = Image.new('RGBA', (cols * TILE_CONFIG['tile_size'], rows * TILE_CONFIG['tile_size']), (0, 0, 0, 0))
    
    # Col·locar cada tile a la seva posició
    for (x, y), tile in tiles.items():
        col = x - TILE_CONFIG['min_x']
        row = y - TILE_CONFIG['min_y']
        full_img.paste(tile, (col * TILE_CONFIG['tile_size'], row * TILE_CONFIG['tile_size']))
    
    return full_img

def plot_radar_on_map(radar_image):
    """Mostra el radar sobre un mapa de Cartopy"""
    
    fig, ax = plt.subplots(figsize=(12, 10), subplot_kw={'projection': ccrs.PlateCarree()})
    
    # Configurar mapa
    ax.set_extent([-0.5, 4.5, 38.5, 44], crs=ccrs.PlateCarree())
    
    # Afegir característiques geogràfiques
    ax.add_feature(cfeature.COASTLINE, linewidth=1)
    ax.add_feature(cfeature.BORDERS, linewidth=1, linestyle=':')
    ax.add_feature(cfeature.OCEAN, color='lightblue', alpha=0.3)
    ax.add_feature(cfeature.LAND, color='lightgray', alpha=0.3)
    
    # Afegir gridlines
    gl = ax.gridlines(draw_labels=True, alpha=0.3)
    gl.top_labels = False
    gl.right_labels = False
    
    # Sobreposar el radar
    if radar_image:
        # Convertir PIL a numpy array
        radar_array = np.array(radar_image)
        
        # Extensió geogràfica dels tiles
        extent = [-0.5, 4.5, 38.5, 44]  # Ajusta segons cobertura real
        
        ax.imshow(radar_array, extent=extent, transform=ccrs.PlateCarree(), alpha=0.7, zorder=10)
    
    ax.set_title('Radar Meteorològic - Meteocat', fontsize=14, fontweight='bold')
    
    return fig

def get_latest_radar_time():
    """Obté l'hora actual arrodonida als 6 minuts més propers"""
    now = datetime.utcnow()
    minute = (now.minute // 6) * 6
    return now.replace(minute=minute, second=0, microsecond=0)

# Sidebar amb controls
with st.sidebar:
    st.header("⚙️ Controls")
    
    # Selecció de data i hora
    latest_time = get_latest_radar_time()
    
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input("Data", latest_time.date())
    with col2:
        hours = list(range(24))
        minutes = list(range(0, 60, 6))
        selected_hour = st.selectbox("Hora (UTC)", hours, index=latest_time.hour)
        selected_minute = st.selectbox("Minuts", minutes, index=latest_time.minute // 6)
    
    # Format date
    date_str = selected_date.strftime("%Y/%m/%d")
    hour_str = f"{selected_hour:02d}"
    minute_str = f"{selected_minute:02d}"
    
    st.info(f"📅 Data seleccionada: {date_str} {hour_str}:{minute_str} UTC")
    
    # Botons
    if st.button("🔄 Carregar Radar", type="primary"):
        st.session_state.load_radar = True
        st.session_state.radar_time = (date_str, hour_str, minute_str)
    
    if st.button("🕐 Últim radar disponible"):
        latest = get_latest_radar_time()
        date_str = latest.strftime("%Y/%m/%d")
        hour_str = f"{latest.hour:02d}"
        minute_str = f"{latest.minute:02d}"
        st.session_state.load_radar = True
        st.session_state.radar_time = (date_str, hour_str, minute_str)
        st.rerun()
    
    st.divider()
    st.markdown("### ℹ️ Informació")
    st.markdown("""
    - Les imatges s'actualitzen cada **6 minuts**
    - Cobertura: Catalunya, Balears i sud de França
    - Font: Servei Meteorològic de Catalunya
    - El radar mostra la **precipitació en temps real**
    """)
    
    st.divider()
    st.markdown("### 🎨 Llegenda")
    legend_colors = [
        ("🟢 Verd", "Precipitació fluixa"),
        ("🟡 Groc", "Precipitació moderada"),
        ("🟠 Taronja", "Precipitació forta"),
        ("🔴 Vermell", "Precipitació molt forta"),
        ("🟣 Lila", "Precipitació torrencial"),
    ]
    for color, desc in legend_colors:
        st.markdown(f"{color} - {desc}")

# Àrea principal
col1, col2 = st.columns([2, 1])

with col1:
    # Carregar i mostrar radar
    if 'load_radar' in st.session_state and st.session_state.load_radar:
        date_str, hour_str, minute_str = st.session_state.radar_time
        
        with st.spinner(f"Descarregant radar del {date_str} a les {hour_str}:{minute_str} UTC..."):
            tiles = download_radar_tiles(date_str, hour_str, minute_str)
            
            if tiles:
                radar_img = create_radar_image(tiles)
                
                if radar_img:
                    st.success(f"✅ Radar carregat correctament ({len(tiles)} tiles)")
                    
                    # Mostrar amb Cartopy
                    fig = plot_radar_on_map(radar_img)
                    st.pyplot(fig)
                    
                    # També mostrar imatge crua
                    with st.expander("Veure imatge crua del radar"):
                        st.image(radar_img, caption=f"Radar {date_str} {hour_str}:{minute_str} UTC", use_column_width=True)
                else:
                    st.error("❌ No s'ha pogut crear la imatge del radar")
            else:
                st.error("❌ No s'han pogut descarregar els tiles del radar")
                st.info("💡 Prova amb una hora més recent o comprova la connexió")
        
        st.session_state.load_radar = False
    else:
        st.info("👈 Selecciona una data i hora al panel lateral i fes clic a 'Carregar Radar'")
        
        # Mostrar mapa buit de Catalunya
        fig, ax = plt.subplots(figsize=(12, 10), subplot_kw={'projection': ccrs.PlateCarree()})
        ax.set_extent([-0.5, 4.5, 38.5, 44], crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.COASTLINE, linewidth=1)
        ax.add_feature(cfeature.BORDERS, linewidth=1, linestyle=':')
        ax.add_feature(cfeature.OCEAN, color='lightblue', alpha=0.3)
        ax.add_feature(cfeature.LAND, color='lightgray', alpha=0.3)
        gl = ax.gridlines(draw_labels=True, alpha=0.3)
        gl.top_labels = False
        gl.right_labels = False
        ax.set_title('Mapa de Catalunya - Esperant dades del radar...', fontsize=14)
        st.pyplot(fig)

with col2:
    st.subheader("📊 Estadístiques")
    
    if 'radar_time' in st.session_state:
        date_str, hour_str, minute_str = st.session_state.radar_time
        st.metric("Data", f"{date_str}")
        st.metric("Hora UTC", f"{hour_str}:{minute_str}")
    
    st.metric("Tiles horitzontals", TILE_CONFIG['max_x'] - TILE_CONFIG['min_x'] + 1)
    st.metric("Tiles verticals", TILE_CONFIG['max_y'] - TILE_CONFIG['min_y'] + 1)
    st.metric("Total tiles", (TILE_CONFIG['max_x'] - TILE_CONFIG['min_x'] + 1) * (TILE_CONFIG['max_y'] - TILE_CONFIG['min_y'] + 1))

# Auto-refresh
if st.checkbox("🔄 Auto-actualitzar cada 6 minuts"):
    st.markdown("L'app s'actualitzarà automàticament...")
    time.sleep(360)  # 6 minuts
    st.rerun()

st.markdown("---")
st.markdown("📡 Dades del [Servei Meteorològic de Catalunya](https://www.meteo.cat) | Desenvolupat amb Streamlit i Cartopy")
