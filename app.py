import streamlit as st
import datetime
import math
import random
import re
from pathlib import Path
import folium
from streamlit_folium import st_folium
from skyfield.api import Loader, wgs84

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


def formatear_angulo_dms(valor, es_latitud=True):
    abs_val = abs(valor)
    grados = int(abs_val)
    minutos_float = (abs_val - grados) * 60
    minutos = int(minutos_float)
    segundos = int(round((minutos_float - minutos) * 60))

    if segundos == 60:
        segundos = 0
        minutos += 1
    if minutos == 60:
        minutos = 0
        grados += 1

    if es_latitud:
        hemisferio = "N" if valor >= 0 else "S"
    else:
        hemisferio = "E" if valor >= 0 else "W"

    return f"{grados:02d}º{minutos:02d}:{segundos:02d} {hemisferio}"


def formatear_lat_lon_dms(lat, lon):
    return (
        formatear_angulo_dms(lat, es_latitud=True),
        formatear_angulo_dms(lon, es_latitud=False),
    )


def formatear_navpac_dmmss(valor):
    grados = int(valor)
    minutos = int((valor - grados) * 60)
    return f"{grados}.{minutos:02d}"


def formatear_grados_mm(valor):
    signo = "-" if valor < 0 else ""
    abs_val = abs(valor)
    grados = int(abs_val)
    minutos_float = (abs_val - grados) * 60
    minutos = int(round(minutos_float))
    if minutos == 60:
        minutos = 0
        grados += 1

    return f"{signo}{grados:02d}º{minutos:02d}"


def decimal_a_dms_texto(valor, es_latitud=True):
    abs_val = abs(valor)
    grados = int(abs_val)
    minutos_float = (abs_val - grados) * 60
    minutos = int(minutos_float)
    segundos = int(round((minutos_float - minutos) * 60))

    if segundos == 60:
        segundos = 0
        minutos += 1
    if minutos == 60:
        minutos = 0
        grados += 1

    if es_latitud:
        hemi = "N" if valor >= 0 else "S"
    else:
        hemi = "E" if valor >= 0 else "W"

    return f"{grados:02d}º{minutos:02d}:{segundos:02d} {hemi}"


def dms_texto_a_decimal(texto, es_latitud=True):
    patron = r"^\s*([+-]?\d{1,3})\s*[°º]\s*(\d{1,2})\s*[:']\s*(\d{1,2})(?:\s*\"?)\s*([NSEWnsew])?\s*$"
    m = re.match(patron, texto)
    if not m:
        raise ValueError("Formato inválido. Usa DDºmm:ss (ej: 36º31:60 N)")

    grados_raw = int(m.group(1))
    minutos = int(m.group(2))
    segundos = int(m.group(3))
    hemi = m.group(4).upper() if m.group(4) else None

    if minutos < 0 or minutos > 59 or segundos < 0 or segundos > 59:
        raise ValueError("Minutos/segundos fuera de rango (00-59)")

    signo = -1 if grados_raw < 0 else 1
    grados = abs(grados_raw)
    valor = grados + (minutos / 60.0) + (segundos / 3600.0)

    if hemi:
        if es_latitud and hemi not in ("N", "S"):
            raise ValueError("Latitud debe usar N o S")
        if not es_latitud and hemi not in ("E", "W"):
            raise ValueError("Longitud debe usar E o W")
        signo = -1 if hemi in ("S", "W") else 1

    valor *= signo

    limite = 90 if es_latitud else 180
    if abs(valor) > limite:
        raise ValueError(f"Valor fuera de rango para {'latitud' if es_latitud else 'longitud'}")

    return valor


@st.cache_resource
def cargar_skyfield():
    base_dir = Path(__file__).resolve().parent
    ephem_path = base_dir.parent / "Polaris" / "de421.bsp"
    loader = Loader(str(base_dir / ".skyfield"))
    ts = loader.timescale()

    if ephem_path.exists():
        eph = loader(str(ephem_path))
    else:
        eph = loader("de421.bsp")

    return ts, eph


def altura_sol_aparente(lat, lon, dt_utc):
    ts, eph = cargar_skyfield()
    t = ts.from_datetime(dt_utc)

    earth = eph["earth"]
    sun = eph["sun"]
    observer = earth + wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon)
    apparent = observer.at(t).observe(sun).apparent()
    alt, _, _ = apparent.altaz()
    return alt.degrees


def distancia_nmi(lat1, lon1, lat2, lon2):
    # Distancia ortodrómica con radio terrestre medio en millas náuticas.
    r_nmi = 3440.065
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r_nmi * c


# --- INTERFAZ ---
st.title("⛵ NavPac Simulator: Cádiz ➡️ Canarias")

# --- CUADERNO DE BITÁCORA (DATOS PARA LA HP-41C) ---
with st.expander("📖 Cuaderno de Bitácora - Datos de Misión", expanded=True):
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("### 📍 Posición de Salida")
        cadiz_lat_dms, cadiz_lon_dms = formatear_lat_lon_dms(CADIZ[0], CADIZ[1])
        st.code(f"Cádiz\nLat: {cadiz_lat_dms}\nLon: {cadiz_lon_dms}", language="text")
    
    with col_b:
        st.markdown("### 📅 Cronómetro UTC")
        # Mostramos la hora de salida fija y la hora actual del simulador
        hora_salida = datetime.datetime(2026, 5, 15, 8, 0)
        st.write(f"**Salida:** {hora_salida.strftime('%d-%m-%Y %H:%M')} UTC")
        st.write(f"**Actual:** {st.session_state.hora_actual.strftime('%d-%m-%Y %H:%M')} UTC")
        st.caption("Usa esta fecha/hora para el Almanaque Náutico de la HP-41C.")

    with col_c:
        st.markdown("### 🏁 Destino")
        tenerife_lat_dms, tenerife_lon_dms = formatear_lat_lon_dms(
            TENERIFE[0], TENERIFE[1]
        )
        st.code(
            f"Tenerife\nLat: {tenerife_lat_dms}\nLon: {tenerife_lon_dms}",
            language="text",
        )

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
    lat_real, lon_real = st.session_state.pos_real[-1]
    dt_utc = st.session_state.hora_actual.replace(tzinfo=datetime.timezone.utc)

    try:
        hs_real = altura_sol_aparente(lat_real, lon_real, dt_utc)
        error_obs = 0.0
        if "Medio" in dificultad:
            error_obs = random.uniform(-0.15, 0.15)
        elif "Difícil" in dificultad:
            error_obs = random.uniform(-0.35, 0.35)

        hs_observada = hs_real + error_obs

        st.warning(f"Hs: {formatear_grados_mm(hs_observada)}")
        st.info(f"Para NavPac (SIGHT): **{formatear_navpac_dmmss(hs_observada)}**")
        st.caption(
            "Altura solar calculada astronómicamente con Skyfield en la posición real y hora UTC del simulador."
        )
    except Exception as exc:
        st.error(
            "No se pudo calcular la altura del Sol con efemérides. "
            "Verifica que exista de421.bsp o conexión para descargarla."
        )
        st.caption(f"Detalle técnico: {exc}")

# 3. EL MAPA DE LA VERDAD
st.header("3. Posicionamiento")
u_lat_dr, u_lon_dr = st.session_state.pos_dr[-1]
lat_dr_dms, lon_dr_dms = formatear_lat_lon_dms(u_lat_dr, u_lon_dr)
st.caption(f"Estima actual (DMS): Lat {lat_dr_dms} | Lon {lon_dr_dms}")
col_lat, col_lon = st.columns(2)

if "fix_lat_texto" not in st.session_state:
    st.session_state.fix_lat_texto = decimal_a_dms_texto(u_lat_dr, es_latitud=True)
if "fix_lon_texto" not in st.session_state:
    st.session_state.fix_lon_texto = decimal_a_dms_texto(u_lon_dr, es_latitud=False)

fix_lat_texto = col_lat.text_input(
    "Latitud de tu Fix (DDºmm:ss)",
    value=st.session_state.fix_lat_texto,
    help="Ejemplo: 36º31:59 N",
)
fix_lon_texto = col_lon.text_input(
    "Longitud de tu Fix (DDºmm:ss)",
    value=st.session_state.fix_lon_texto,
    help="Ejemplo: 006º17:00 W",
)

st.session_state.fix_lat_texto = fix_lat_texto
st.session_state.fix_lon_texto = fix_lon_texto

fix_valido = True
fix_error = None
try:
    fix_lat = dms_texto_a_decimal(fix_lat_texto, es_latitud=True)
    fix_lon = dms_texto_a_decimal(fix_lon_texto, es_latitud=False)
    st.caption(f"Fix decimal interno: Lat {fix_lat:.4f} | Lon {fix_lon:.4f}")
except ValueError as exc:
    fix_valido = False
    fix_error = str(exc)
    st.warning(f"Formato de Fix inválido: {fix_error}")

if "revelado" not in st.session_state:
    st.session_state.revelado = False
if "fix_revelado" not in st.session_state:
    st.session_state.fix_revelado = None

if st.button("🗺️ Revelar Posición Real"):
    if not fix_valido:
        st.error("No se puede revelar con Fix inválido. Revisa el formato DDºmm:ss.")
        st.stop()

    st.session_state.revelado = True
    st.session_state.fix_revelado = (fix_lat, fix_lon)

if st.session_state.revelado and st.session_state.fix_revelado is not None:
    fix_lat_mapa, fix_lon_mapa = st.session_state.fix_revelado
    lat_real, lon_real = st.session_state.pos_real[-1]
    lat_real_dms, lon_real_dms = formatear_lat_lon_dms(lat_real, lon_real)
    error_nmi = distancia_nmi(lat_real, lon_real, fix_lat_mapa, fix_lon_mapa)

    st.success(f"Posición real: Lat {lat_real_dms} | Lon {lon_real_dms}")
    st.info(f"Error de tu Fix: {error_nmi:.2f} nmi")

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
    folium.Marker((fix_lat_mapa, fix_lon_mapa), icon=folium.Icon(color="green", icon="star")).add_to(m)
    st_folium(m, width=800, height=450)
