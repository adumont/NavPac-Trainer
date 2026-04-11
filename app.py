import streamlit as st
import datetime
import math
import random
import re
from pathlib import Path
import folium
from streamlit_folium import st_folium
from skyfield.api import Loader, wgs84, Star

# --- CONFIGURACIÓN Y ESTADO ---
st.set_page_config(page_title="NavPac Simulator MVP", layout="wide")

# Coordenadas de puntos clave
CADIZ = (36.5333, -6.2833)
TENERIFE = (28.4667, -16.2500)

# Catálogo de cuerpos celestes navegables
# Valor: string = clave en efemérides JPL | Star = estrella con coord J2000
CUERPOS_CELESTES = {
    "Sol":        "sun",
    "Luna":       "moon",
    "Venus":      "venus",
    "Marte":      "mars",
    "Júpiter":    "jupiter barycenter",
    "Saturno":    "saturn barycenter",
    "Polaris":    Star(ra_hours=2.5303,  dec_degrees=89.2641),
    "Vega":       Star(ra_hours=18.6157, dec_degrees=38.7836),
    "Sirius":     Star(ra_hours=6.7525,  dec_degrees=-16.7161),
    "Arcturus":   Star(ra_hours=14.2612, dec_degrees=19.1822),
    "Canopus":    Star(ra_hours=6.3992,  dec_degrees=-52.6957),
    "Rigel":      Star(ra_hours=5.2423,  dec_degrees=-8.2017),
    "Procyon":    Star(ra_hours=7.6553,  dec_degrees=5.2250),
    "Betelgeuse": Star(ra_hours=5.9195,  dec_degrees=7.4071),
    "Altair":     Star(ra_hours=19.8459, dec_degrees=8.8683),
    "Aldebaran":  Star(ra_hours=4.5987,  dec_degrees=16.5093),
    "Deneb":      Star(ra_hours=20.6905, dec_degrees=45.2803),
    "Fomalhaut":  Star(ra_hours=22.9608, dec_degrees=-29.6222),
    "Regulus":    Star(ra_hours=10.1395, dec_degrees=11.9672),
    "Spica":      Star(ra_hours=13.4198, dec_degrees=-11.1614),
    "Antares":    Star(ra_hours=16.4901, dec_degrees=-26.4320),
}

RADIOS_CUERPOS_KM = {
    "Sol": 695700.0,
    "Luna": 1737.4,
}

if "iniciado" not in st.session_state:
    st.session_state.hora_actual = datetime.datetime(2026, 5, 15, 8, 0)
    st.session_state.pos_real = [CADIZ]
    st.session_state.pos_dr = [CADIZ]
    st.session_state.fixes = []
    st.session_state.log_navegacion = []
    st.session_state.iniciado = True

if "log_navegacion" not in st.session_state:
    st.session_state.log_navegacion = []
if "log_fixes" not in st.session_state:
    st.session_state.log_fixes = []


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
    signo = "-" if valor < 0 else ""
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

    return f"{signo}{grados}.{minutos:02d}{segundos:02d}"


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


def formatear_grados_minutos_decimal(valor, decimales_minutos=1):
    signo = "-" if valor < 0 else ""
    abs_val = abs(valor)
    grados = int(abs_val)
    minutos = round((abs_val - grados) * 60, decimales_minutos)

    if minutos >= 60:
        minutos = 0.0
        grados += 1

    ancho = 2 if decimales_minutos == 0 else 3 + decimales_minutos
    return f"{signo}{grados:02d}º{minutos:0{ancho}.{decimales_minutos}f}'"


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


def observacion_aparente(nombre, lat, lon, dt_utc):
    ts, eph = cargar_skyfield()
    t = ts.from_datetime(dt_utc)
    observer = eph["earth"] + wgs84.latlon(latitude_degrees=lat, longitude_degrees=lon)
    cuerpo_id = CUERPOS_CELESTES[nombre]
    cuerpo = eph[cuerpo_id] if isinstance(cuerpo_id, str) else cuerpo_id
    return observer.at(t).observe(cuerpo).apparent()


def altura_cuerpo(nombre, lat, lon, dt_utc):
    """Devuelve la altitud verdadera del centro (sin refracción) y azimut."""
    apparent = observacion_aparente(nombre, lat, lon, dt_utc)
    alt, az, _ = apparent.altaz()
    return alt.degrees, az.degrees


def correccion_dip_minutos(altura_ojo_m):
    if altura_ojo_m <= 0:
        return 0.0
    return 1.76 * math.sqrt(altura_ojo_m)


def semidiametro_minutos(nombre, distancia_km):
    radio_km = RADIOS_CUERPOS_KM.get(nombre)
    if radio_km is None or distancia_km <= 0:
        return 0.0
    return math.degrees(math.asin(min(1.0, radio_km / distancia_km))) * 60.0


def lectura_sextante(nombre, lat, lon, dt_utc, altura_ojo_m=3.048, limbo="Centro"):
    apparent = observacion_aparente(nombre, lat, lon, dt_utc)
    alt_true, az, _ = apparent.altaz()
    alt_refr, _, _ = apparent.altaz(
        temperature_C="standard",
        pressure_mbar="standard",
    )

    alt_centro_real = alt_true.degrees
    refraccion_min = max(0.0, (alt_refr.degrees - alt_centro_real) * 60.0)
    dip_min = correccion_dip_minutos(altura_ojo_m)
    semidiametro_cuerpo_min = semidiametro_minutos(nombre, apparent.distance().km)

    ajuste_limbo_min = 0.0
    if semidiametro_cuerpo_min > 0:
        if limbo == "Inferior":
            ajuste_limbo_min = -semidiametro_cuerpo_min
        elif limbo == "Superior":
            ajuste_limbo_min = semidiametro_cuerpo_min

    hs = alt_centro_real + (refraccion_min + dip_min + ajuste_limbo_min) / 60.0
    return {
        "hs": hs,
        "az": az.degrees,
        "alt_centro_real": alt_centro_real,
        "refraccion_min": refraccion_min,
        "dip_min": dip_min,
        "semidiametro_min": semidiametro_cuerpo_min,
        "limbo": limbo,
    }


def cuerpos_visibles(lat, lon, dt_utc, alt_min=5.0):
    """Devuelve dict {nombre: (alt, az)} para cuerpos por encima de alt_min grados."""
    resultado = {}
    for nombre in CUERPOS_CELESTES:
        try:
            alt, az = altura_cuerpo(nombre, lat, lon, dt_utc)
            if alt >= alt_min:
                resultado[nombre] = (alt, az)
        except Exception:
            pass
    return resultado


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
velocidad = c2.number_input("Velocidad (nudos)", 0, 20, 6)
horas = c3.number_input("Tiempo (Horas)", 1, 48, 12)

if st.button("Navegar"):
    st.session_state.hora_actual += datetime.timedelta(hours=horas)
    distancia = velocidad * horas

    # Mover Estima (DR) — el navegante no aplica correcciones de deriva
    u_lat_dr, u_lon_dr = st.session_state.pos_dr[-1]
    n_lat_dr, n_lon_dr = mover_barco(u_lat_dr, u_lon_dr, rumbo, distancia)
    st.session_state.pos_dr = st.session_state.pos_dr + [(n_lat_dr, n_lon_dr)]

    # Mover Real con error y deriva (también cuando velocidad=0)
    u_lat_re, u_lon_re = st.session_state.pos_real[-1]

    if velocidad == 0:
        # Barco parado: solo actúan corrientes/deriva según dificultad
        deriva_vel = {"Calma (Fácil)": 0.15, "Moderado (Medio)": 0.35, "Temporal (Difícil)": 0.8}.get(dificultad, 0.15)
        deriva_rumbo = random.uniform(0, 360)
        n_lat_re, n_lon_re = mover_barco(u_lat_re, u_lon_re, deriva_rumbo, deriva_vel * horas)
    else:
        err_r, err_v = 0, 0
        if "Medio" in dificultad:
            err_r, err_v = random.uniform(-3, 3), random.uniform(-0.5, 0.5)
        elif "Difícil" in dificultad:
            err_r, err_v = random.uniform(-7, 7), random.uniform(-1.2, 1.2)
        vel_real = max(0.0, velocidad + err_v)
        n_lat_re, n_lon_re = mover_barco(u_lat_re, u_lon_re, rumbo + err_r, vel_real * horas)

    st.session_state.pos_real = st.session_state.pos_real + [(n_lat_re, n_lon_re)]

    # Registrar en bitácora
    diff_nmi = distancia_nmi(n_lat_dr, n_lon_dr, n_lat_re, n_lon_re)
    nueva_entrada = {
        "Fecha/Hora UTC": st.session_state.hora_actual.strftime("%d-%m-%Y %H:%M"),
        "Rumbo (º)": rumbo,
        "Vel (kn)": velocidad,
        "Horas": horas,
        "Dist DR (nmi)": round(distancia, 1),
        "Lat Estima": formatear_angulo_dms(n_lat_dr, es_latitud=True),
        "Lon Estima": formatear_angulo_dms(n_lon_dr, es_latitud=False),
        "Lat Real": formatear_angulo_dms(n_lat_re, es_latitud=True),
        "Lon Real": formatear_angulo_dms(n_lon_re, es_latitud=False),
        "Error (nmi)": round(diff_nmi, 2),
    }
    st.session_state.log_navegacion = st.session_state.log_navegacion + [nueva_entrada]

    st.success(
        f"Navegación completada. Hora actual: {st.session_state.hora_actual.strftime('%H:%M')} UTC"
    )
    st.rerun()

# 2. SEXTANTE
st.header("2. Observación Astronómica")

_lat_obs, _lon_obs = st.session_state.pos_dr[-1]
_dt_utc = st.session_state.hora_actual.replace(tzinfo=datetime.timezone.utc)

try:
    _visibles = cuerpos_visibles(_lat_obs, _lon_obs, _dt_utc)
except Exception as _exc:
    _visibles = {}
    st.error(f"Error al calcular cuerpos visibles: {_exc}")

if not _visibles:
    st.warning("No hay cuerpos celestes visibles (alt > 5°) a esta hora y posición. Avanza el tiempo.")
else:
    # Ordenar por altitud descendente y construir opciones legibles
    _ordenados = sorted(_visibles.items(), key=lambda x: -x[1][0])
    _sol_visible = "Sol" in _visibles
    _hay_estrellas = any(isinstance(CUERPOS_CELESTES[n], Star) for n in _visibles)

    if _sol_visible:
        st.caption("☀️ El Sol está sobre el horizonte. Observación diurna posible.")
    if _hay_estrellas:
        st.caption("⭐ Estrellas visibles: condiciones de crepúsculo o noche.")

    _opciones_mapa = {
        f"{n}  —  alt {formatear_grados_mm(a)}  az {int(z):03d}°": n
        for n, (a, z) in _ordenados
    }
    _sel_str = st.selectbox("Cuerpo a observar:", list(_opciones_mapa.keys()))
    _cuerpo_sel = _opciones_mapa[_sel_str]
    _usa_limbo = _cuerpo_sel in RADIOS_CUERPOS_KM

    _col_obs_1, _col_obs_2 = st.columns(2)
    _altura_ojo_ft = _col_obs_1.number_input(
        "Altura de ojo sobre el mar (ft)",
        min_value=0.0,
        max_value=100.0,
        value=10.0,
        step=0.5,
        help="Se usa para aplicar la depresión del horizonte en la lectura Hs.",
    )
    _altura_ojo_m = _altura_ojo_ft * 0.3048

    if _usa_limbo:
        _limbo = _col_obs_2.selectbox(
            "Limbo observado",
            options=["Inferior", "Superior"],
            index=0,
            help="Para Sol y Luna, la lectura del sextante depende del limbo observado.",
        )
    else:
        _limbo = "Centro"
        _col_obs_2.caption("Astro puntual: se usa el centro del cuerpo para la lectura.")

    if "ultima_observacion" not in st.session_state:
        st.session_state.ultima_observacion = None

    if st.button("🔭 Tomar Altura", key="btn_tomar_altura"):
        lat_real, lon_real = st.session_state.pos_real[-1]
        try:
            _obs_real = lectura_sextante(
                _cuerpo_sel,
                lat_real,
                lon_real,
                _dt_utc,
                altura_ojo_m=_altura_ojo_m,
                limbo=_limbo,
            )
            _error_obs_min = 0.0
            if "Medio" in dificultad:
                _error_obs_min = random.uniform(-0.15, 0.15)
            elif "Difícil" in dificultad:
                _error_obs_min = random.uniform(-0.35, 0.35)

            _hs_obs = _obs_real["hs"] + (_error_obs_min / 60.0)
            st.session_state.ultima_observacion = {
                "cuerpo": _cuerpo_sel,
                "hs": _hs_obs,
                "altura_ojo_ft": _altura_ojo_ft,
                "altura_ojo_m": _altura_ojo_m,
                "limbo": _limbo,
                "az": _obs_real["az"],
                "refraccion_min": _obs_real["refraccion_min"],
                "dip_min": _obs_real["dip_min"],
                "semidiametro_min": _obs_real["semidiametro_min"],
                "error_obs_min": _error_obs_min,
                "fecha": st.session_state.hora_actual.strftime("%d-%m-%Y %H:%M"),
            }
        except Exception as exc:
            st.error(f"Error al calcular la altura de {_cuerpo_sel}: {exc}")

    if st.session_state.ultima_observacion is not None:
        _obs = st.session_state.ultima_observacion
        _detalle_limbo = ""
        if _obs["limbo"] != "Centro":
            _detalle_limbo = f" · limbo {_obs['limbo'].lower()}"

        st.warning(
            f"Hs ({_obs['cuerpo']}{_detalle_limbo}): "
            f"{formatear_grados_minutos_decimal(_obs['hs'])}"
        )
        st.info(
            f"Para NavPac SIGHT (DD.MMSS): **{formatear_navpac_dmmss(_obs['hs'])}**"
        )

        _altura_obs_ft = _obs.get("altura_ojo_ft", _obs.get("altura_ojo_m", 0.0) / 0.3048)

        _partes_obs = [
            f"altura de ojo {_altura_obs_ft:.1f} ft",
            f"refracción +{_obs['refraccion_min']:.1f}'",
            f"dip +{_obs['dip_min']:.1f}'",
        ]
        if _obs["semidiametro_min"] > 0 and _obs["limbo"] != "Centro":
            signo_sd = "-" if _obs["limbo"] == "Inferior" else "+"
            _partes_obs.append(
                f"semidiámetro {signo_sd}{_obs['semidiametro_min']:.1f}'"
            )
        if abs(_obs["error_obs_min"]) > 1e-6:
            _partes_obs.append(f"error simulado {_obs['error_obs_min']:+.1f}'")

        st.caption(
            f"Lectura guardada: {_obs['fecha']} UTC · posición real del barco · "
            + " · ".join(_partes_obs)
        )

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

    # Registrar Fix en bitácora
    lat_real_fix, lon_real_fix = st.session_state.pos_real[-1]
    err_fix = distancia_nmi(lat_real_fix, lon_real_fix, fix_lat, fix_lon)
    nueva_fix = {
        "Paso": len(st.session_state.log_fixes) + 1,
        "Fecha/Hora UTC": st.session_state.hora_actual.strftime("%d-%m-%Y %H:%M"),
        "Lat Fix": decimal_a_dms_texto(fix_lat, es_latitud=True),
        "Lon Fix": decimal_a_dms_texto(fix_lon, es_latitud=False),
        "Lat Real": decimal_a_dms_texto(lat_real_fix, es_latitud=True),
        "Lon Real": decimal_a_dms_texto(lon_real_fix, es_latitud=False),
        "Error Fix/Real (nmi)": round(err_fix, 2),
    }
    st.session_state.log_fixes = st.session_state.log_fixes + [nueva_fix]

if st.session_state.revelado and st.session_state.fix_revelado is not None:
    fix_lat_mapa, fix_lon_mapa = st.session_state.fix_revelado
    lat_real, lon_real = st.session_state.pos_real[-1]
    lat_real_dms, lon_real_dms = formatear_lat_lon_dms(lat_real, lon_real)
    error_nmi = distancia_nmi(lat_real, lon_real, fix_lat_mapa, fix_lon_mapa)
    st.success(f"Posición real: Lat {lat_real_dms} | Lon {lon_real_dms}")
    st.info(f"Error de tu Fix: {error_nmi:.2f} nmi")

# Mapa: Estima siempre visible; track real solo cuando revelado
m = folium.Map(location=[u_lat_dr, u_lon_dr], zoom_start=6)

# --- Línea Estima (azul) con marcador en cada waypoint ---
if len(st.session_state.pos_dr) > 1:
    folium.PolyLine(st.session_state.pos_dr, color="blue", weight=2).add_to(m)
for i, (lat, lon) in enumerate(st.session_state.pos_dr):
    tooltip = "Salida (Estima)" if i == 0 else f"Estima #{i}"
    folium.CircleMarker(
        location=(lat, lon), radius=5, color="blue", fill=True,
        fill_opacity=0.85, tooltip=tooltip,
    ).add_to(m)

# --- Track real + marcadores (solo si revelado) ---
if st.session_state.revelado:
    if len(st.session_state.pos_real) > 1:
        folium.PolyLine(st.session_state.pos_real, color="red", weight=2).add_to(m)
    for i, (lat, lon) in enumerate(st.session_state.pos_real):
        tooltip = "Salida (real)" if i == 0 else f"Posición real #{i}"
        folium.CircleMarker(
            location=(lat, lon), radius=5, color="red", fill=True,
            fill_opacity=0.85, tooltip=tooltip,
        ).add_to(m)
    # Fix del navegante
    if st.session_state.fix_revelado is not None:
        fix_lat_mapa, fix_lon_mapa = st.session_state.fix_revelado
        folium.Marker(
            (fix_lat_mapa, fix_lon_mapa),
            icon=folium.Icon(color="green", icon="star"),
            tooltip="Tu Fix",
        ).add_to(m)

# Destino
folium.Marker(
    TENERIFE,
    icon=folium.Icon(color="orange", icon="flag"),
    tooltip="Destino: Tenerife",
).add_to(m)

st_folium(m, width=800, height=450)

# Leyenda
col_l1, col_l2, col_l3, col_l4 = st.columns(4)
col_l1.caption("🔵 Línea/puntos azules: tu Estima (Dead Reckoning)")
col_l4.caption("🟠 Bandera naranja: Destino (Tenerife)")
if st.session_state.revelado:
    col_l2.caption("🔴 Línea/puntos rojos: posición real del barco")
    col_l3.caption("🟢 Estrella verde: tu Fix introducido")

import pandas as pd

# --- TABLA BITÁCORA NAVEGACIÓN ---
if st.session_state.log_navegacion:
    st.header("4. Bitácora de Navegación")
    df = pd.DataFrame(st.session_state.log_navegacion)
    st.dataframe(df, use_container_width=True, hide_index=True)

# --- TABLA FIXES ---
if st.session_state.log_fixes:
    st.header("5. Registro de Fixes")
    df_fixes = pd.DataFrame(st.session_state.log_fixes)
    st.dataframe(df_fixes, use_container_width=True, hide_index=True)
