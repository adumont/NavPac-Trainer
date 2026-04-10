import streamlit as st
import datetime
import math
import random
import folium
from streamlit_folium import st_folium

# --- CONFIGURACIÓN Y ESTADO ---
st.set_page_config(page_title="NavPac Simulator MVP", layout="wide")

# Coordenadas de puntos clave
CADIZ = (36.5333, -6.2833)
TENERIFE = (28.4667, -16.2500)

if "iniciado" not in st.session_state:
    st.session_state.hora_actual = datetime.datetime(2026, 5, 15, 8, 0)
    st.session_state.pos_real = [CADIZ]
    st.session_state.pos_dr = [CADIZ]
    st.session_state.fixes = []
    st.session_state.iniciado = True


# --- MATEMÁTICA NAVAL ---
def mover_barco(lat, lon, rumbo, distancia):
    R = 3440.065  # Radio terrestre en millas náuticas
    lat1, lon1, brng = math.radians(lat), math.radians(lon), math.radians(rumbo)
    d = distancia / R

    lat2 = math.asin(
        math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(brng)
    )
    # Corrección: aquí usamos lon1 y lat1 correctamente
    lon2 = lon1 + math.atan2(
        math.sin(brng) * math.sin(d) * math.cos(lat1),
        math.cos(d) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)


# --- INTERFAZ ---
st.title("⛵ NavPac Simulator: Cádiz ➡️ Canarias")

# --- CUADERNO DE BITÁCORA (DATOS PARA LA HP-41C) ---
with st.expander("📖 Cuaderno de Bitácora - Datos de Misión", expanded=True):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("### 📍 Posición de Salida")
        st.code(f"Cádiz\nLat: {CADIZ[0]}º N\nLon: {abs(CADIZ[1])}º W", language="text")
    
    with col_b:
        st.markdown("### 📅 Cronómetro UTC")
        # Mostramos la hora de salida fija y la hora actual del simulador
        hora_salida = datetime.datetime(2026, 5, 15, 8, 0)
        st.write(f"**Salida:** {hora_salida.strftime('%d-%m-%Y %H:%M')} UTC")
        st.write(f"**Actual:** {st.session_state.hora_actual.strftime('%d-%m-%Y %H:%M')} UTC")
        st.caption("Usa esta fecha/hora para el Almanaque Náutico de la HP-41C.")

    with col_c:
        st.markdown("### 🏁 Destino")
        st.code(f"Tenerife\nLat: {TENERIFE[0]}º N\nLon: {abs(TENERIFE[1])}º W", language="text")

    st.info("💡 Consejo NavPac: Recuerda que para el programa 'SIGHT', la hora UTC es vital para obtener el GHA y la Dec del astro.")

# --- SIDEBAR: CONFIGURACIÓN ---
dificultad = st.sidebar.radio(
    "🌊 Estado del Mar",
    options=["Calma (Fácil)", "Moderado (Medio)", "Temporal (Difícil)"],
)

# 1. EL TIMÓN
st.header("1. Órdenes a Máquinas")
c1, c2, c3 = st.columns(3)
rumbo = c1.number_input("Rumbo (º)", 0, 359, 225)
velocidad = c2.number_input("Velocidad (nudos)", 1, 20, 6)
horas = c3.number_input("Tiempo (Horas)", 1, 48, 12)

if st.button("Navegar"):
    st.session_state.hora_actual += datetime.timedelta(hours=horas)
    distancia = velocidad * horas

    # Mover Estima (DR)
    u_lat_dr, u_lon_dr = st.session_state.pos_dr[-1]
    n_lat_dr, n_lon_dr = mover_barco(u_lat_dr, u_lon_dr, rumbo, distancia)
    st.session_state.pos_dr.append((n_lat_dr, n_lon_dr))

    # Mover Real con error
    err_r, err_v = 0, 0
    if "Medio" in dificultad:
        err_r, err_v = random.uniform(-3, 3), random.uniform(-0.5, 0.5)
    elif "Difícil" in dificultad:
        err_r, err_v = random.uniform(-7, 7), random.uniform(-1.2, 1.2)

    u_lat_re, u_lon_re = st.session_state.pos_real[-1]
    n_lat_re, n_lon_re = mover_barco(
        u_lat_re, u_lon_re, rumbo + err_r, (velocidad + err_v) * horas
    )
    st.session_state.pos_real.append((n_lat_re, n_lon_re))
    st.success(
        f"Navegación completada. Hora actual: {st.session_state.hora_actual.strftime('%H:%M')} UTC"
    )
    st.rerun()

# 2. SEXTANTE
st.header("2. Observación Astronómica")
if st.button("🔭 Tomar Altura del Sol"):
    lat_real = st.session_state.pos_real[-1][0]
    # Simulación de altura del sol (Hs)
    hs_base = 90 - abs(lat_real - 18)
    error = random.uniform(-0.1, 0.1) if "Fácil" not in dificultad else 0
    hs = hs_base + error

    grados = int(hs)
    minutos = (hs - grados) * 60
    # Formato para HP-41C (D.MMSS)
    st.warning(f"Hs: {grados}º {minutos:.1f}'")
    st.info(f"Para NavPac (SIGHT): **{grados}.{int(minutos):02d}**")

# 3. EL MAPA DE LA VERDAD
st.header("3. Posicionamiento")
u_lat_dr, u_lon_dr = st.session_state.pos_dr[-1]
col_lat, col_lon = st.columns(2)
fix_lat = col_lat.number_input(
    "Latitud de tu Fix", value=float(u_lat_dr), format="%.4f"
)
fix_lon = col_lon.number_input(
    "Longitud de tu Fix", value=float(u_lon_dr), format="%.4f"
)

if st.button("🗺️ Revelar Posición Real"):
    m = folium.Map(location=[u_lat_dr, u_lon_dr], zoom_start=6)
    folium.PolyLine(
        st.session_state.pos_dr, color="blue", weight=2, label="Estima"
    ).add_to(m)
    folium.PolyLine(
        st.session_state.pos_real, color="red", weight=2, label="Real"
    ).add_to(m)
    folium.Marker(st.session_state.pos_real[-1], icon=folium.Icon(color="red")).add_to(
        m
    )
    folium.Marker(
        (fix_lat, fix_lon), icon=folium.Icon(color="green", icon="star")
    ).add_to(m)
    st_folium(m, width=800, height=450)
