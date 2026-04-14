import streamlit as st
import datetime
import math
import random
import re
from pathlib import Path
import folium
from streamlit_folium import st_folium
from skyfield.api import Loader, wgs84, Star

from angulos import (
    formatear_angulo_dms,
    formatear_lat_lon_dms,
    formatear_navpac_dmmss,
    dms_texto_a_decimal,
    formatear_grados_minutos_decimal,
    formatear_grados_mm,
)

# --- CONFIGURACIÓN Y ESTADO ---
st.set_page_config(page_title="NavPac Simulator MVP", layout="wide")

nav_tab, fix_tab = st.tabs(["Navegacion", "FIX"])

with nav_tab:

    # Coordenadas de puntos clave
    CADIZ = (36.5333, -6.2833)
    TENERIFE = (28.4667, -16.2500)

    # Catálogo de cuerpos celestes navegables
    # Valor: string = clave en efemérides JPL | Star = estrella con coord J2000

    CUERPOS_CELESTES = {
        "Sol": "sun",
        "Luna": "moon",
        "Venus": "venus",
        "Marte": "mars",
        "Júpiter": "jupiter barycenter",
        "Saturno": "saturn barycenter",
        "Polaris": Star(ra_hours=2.5303, dec_degrees=89.2641),
        "Vega": Star(ra_hours=18.6157, dec_degrees=38.7836),
        "Sirius": Star(ra_hours=6.7525, dec_degrees=-16.7161),
        "Arcturus": Star(ra_hours=14.2612, dec_degrees=19.1822),
        "Canopus": Star(ra_hours=6.3992, dec_degrees=-52.6957),
        "Rigel": Star(ra_hours=5.2423, dec_degrees=-8.2017),
        "Procyon": Star(ra_hours=7.6553, dec_degrees=5.2250),
        "Betelgeuse": Star(ra_hours=5.9195, dec_degrees=7.4071),
        "Altair": Star(ra_hours=19.8459, dec_degrees=8.8683),
        "Aldebaran": Star(ra_hours=4.5987, dec_degrees=16.5093),
        "Deneb": Star(ra_hours=20.6905, dec_degrees=45.2803),
        "Fomalhaut": Star(ra_hours=22.9608, dec_degrees=-29.6222),
        "Regulus": Star(ra_hours=10.1395, dec_degrees=11.9672),
        "Spica": Star(ra_hours=13.4198, dec_degrees=-11.1614),
        "Antares": Star(ra_hours=16.4901, dec_degrees=-26.4320),
    }

    # Mapeo de estrellas a su número NavPac (según la imagen)
    NAVPAC_STAR_INDEX = {
        "Polaris": 0,
        "Vega": 49,
        "Sirius": 18,
        "Arcturus": 37,
        "Canopus": 17,
        "Rigel": 11,
        "Procyon": 20,
        "Betelgeuse": 16,
        "Altair": 51,
        "Aldebaran": 10,
        "Deneb": 53,
        "Fomalhaut": 56,
        "Regulus": 26,
        "Antares": 42,
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
        observer = eph["earth"] + wgs84.latlon(
            latitude_degrees=lat, longitude_degrees=lon
        )
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
            st.code(
                f"Cádiz\nLat: {cadiz_lat_dms}\nLon: {cadiz_lon_dms}", language="text"
            )

        with col_b:
            st.markdown("### 📅 Cronómetro UTC")
            # Mostramos la hora de salida fija y la hora actual del simulador
            hora_salida = datetime.datetime(2026, 5, 15, 8, 0)
            st.write(f"**Salida:** {hora_salida.strftime('%d-%m-%Y %H:%M')} UTC")
            st.write(
                f"**Actual:** {st.session_state.hora_actual.strftime('%d-%m-%Y %H:%M')} UTC"
            )
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

    # --- SIDEBAR: CONFIGURACIÓN ---
    dificultad = st.sidebar.radio(
        "🌊 Estado del Mar",
        options=["Calma (Fácil)", "Moderado (Medio)", "Temporal (Difícil)"],
    )

    # 1. EL TIMÓN
    st.header("1. Órdenes a Máquinas")
    c1, c2, c3 = st.columns(3)
    rumbo = c1.number_input("Rumbo (º)", 0, 359, 229)
    velocidad = c2.number_input("Velocidad (nudos)", 0, 20, 6)
    # Input for time in HH:MM format
    horas_hhmm = c3.text_input(
        "Tiempo (HH:MM)",
        value="04:00",
        help="Introduce el tiempo en formato HH:MM (ejemplo: 12:30)",
    )
    # Convert HH:MM to decimal hours
    _horas_match = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", horas_hhmm)
    if _horas_match:
        horas = int(_horas_match.group(1)) + int(_horas_match.group(2)) / 60.0
    else:
        st.error("Formato de tiempo inválido. Usa HH:MM (ejemplo: 12:30)")
        horas = 0.0

    if st.button("Navegar"):
        st.session_state.hora_previa = st.session_state.hora_actual
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
            deriva_vel = {
                "Calma (Fácil)": 0.15,
                "Moderado (Medio)": 0.35,
                "Temporal (Difícil)": 0.8,
            }.get(dificultad, 0.15)
            deriva_rumbo = random.uniform(0, 360)
            n_lat_re, n_lon_re = mover_barco(
                u_lat_re, u_lon_re, deriva_rumbo, deriva_vel * horas
            )
        else:
            err_r, err_v = 0, 0
            if "Medio" in dificultad:
                err_r, err_v = random.uniform(-3, 3), random.uniform(-0.5, 0.5)
            elif "Difícil" in dificultad:
                err_r, err_v = random.uniform(-7, 7), random.uniform(-1.2, 1.2)
            vel_real = max(0.0, velocidad + err_v)
            n_lat_re, n_lon_re = mover_barco(
                u_lat_re, u_lon_re, rumbo + err_r, vel_real * horas
            )

        st.session_state.pos_real = st.session_state.pos_real + [(n_lat_re, n_lon_re)]

        # Registrar en bitácora
        diff_nmi = distancia_nmi(n_lat_dr, n_lon_dr, n_lat_re, n_lon_re)
        nueva_entrada = {
            "Fecha Salida UTC": st.session_state.hora_previa.strftime("%d-%m-%Y %H:%M"),
            "Rumbo (º)": rumbo,
            "Vel (kn)": velocidad,
            "Horas": horas,
            "Fecha Llegada UTC": st.session_state.hora_actual.strftime("%d-%m-%Y %H:%M"),
            "Dist DR (nmi)": round(distancia, 1),
            "Lat Estima": formatear_angulo_dms(n_lat_dr, es_latitud=True),
            "Lon Estima": formatear_angulo_dms(n_lon_dr, es_latitud=False),
            "Lat Real": formatear_angulo_dms(n_lat_re, es_latitud=True),
            "Lon Real": formatear_angulo_dms(n_lon_re, es_latitud=False),
            "Error (nmi)": round(diff_nmi, 2),
        }
        st.session_state.log_navegacion = st.session_state.log_navegacion + [
            nueva_entrada
        ]

        st.success(
            f"Navegación completada. Hora actual: {st.session_state.hora_actual.strftime('%H:%M')} UTC"
        )
        st.rerun()

    # 2. Dead Reckoning
    st.header("2. Dead Reckoning")

    st.write(
        f"Use `DR` in NavPac with the inputs above (Rumbo = `{rumbo}º`, Velocidad x Tiempo = `{velocidad * horas} nmi`) to see your estimated position based on Dead Reckoning. Enter it below:"
    )

    # Input DR lat/lon (DDºmm:ss),  two  columns
    col_dr_lat, col_dr_lon = st.columns(2)
    u_lat_dr, u_lon_dr = st.session_state.pos_dr[-1]
    dr_lat_texto = col_dr_lat.text_input(
        "DR Latitude",
        placeholder="Ejemplo: 36º32:00 N",
        value=formatear_angulo_dms(u_lat_dr, es_latitud=True)
    )
    dr_lon_texto = col_dr_lon.text_input(
        "DR Longitude",
        placeholder="Ejemplo: 06º17:00 W",
        value=formatear_angulo_dms(u_lon_dr, es_latitud=False)
    )

    if st.button("Update DR Position"):
        try:
            dr_lat = dms_texto_a_decimal(dr_lat_texto, es_latitud=True)
            dr_lon = dms_texto_a_decimal(dr_lon_texto, es_latitud=False)
            st.session_state.pos_dr[-1] = (dr_lat, dr_lon)
            st.success("DR position updated.")
        except ValueError as exc:
            st.error(f"Invalid DR position format: {exc}")

    # 3. SEXTANTE
    st.header("3. Observación Astronómica")

    _lat_obs, _lon_obs = st.session_state.pos_dr[-1]
    _dt_utc = st.session_state.hora_actual.replace(tzinfo=datetime.timezone.utc)

    try:
        _visibles = cuerpos_visibles(_lat_obs, _lon_obs, _dt_utc)
    except Exception as _exc:
        _visibles = {}
        st.error(f"Error al calcular cuerpos visibles: {_exc}")

    if not _visibles:
        st.warning(
            "No hay cuerpos celestes visibles (alt > 5°) a esta hora y posición. Avanza el tiempo."
        )
    else:

        # Ordenar: Sol y Luna siempre arriba si visibles, luego el resto por altitud descendente
        _ordenados = sorted(_visibles.items(), key=lambda x: -x[1][0])
        _sol_visible = "Sol" in _visibles
        _luna_visible = "Luna" in _visibles
        _hay_estrellas = any(isinstance(CUERPOS_CELESTES[n], Star) for n in _visibles)

        # Construir lista con Sol y Luna primero si están
        _ordenados_final = []
        if _sol_visible:
            _ordenados_final.append(("Sol", _visibles["Sol"]))
        if _luna_visible:
            _ordenados_final.append(("Luna", _visibles["Luna"]))
        for n, v in _ordenados:
            if n not in ("Sol", "Luna"):
                _ordenados_final.append((n, v))

        if _sol_visible:
            st.caption("☀️ El Sol está sobre el horizonte. Observación diurna posible.")
        if _hay_estrellas:
            st.caption("⭐ Estrellas visibles: condiciones de crepúsculo o noche.")

        _opciones_mapa = {
            f"{n}  —  alt {formatear_grados_mm(a)}  az {int(z):03d}°": n
            for n, (a, z) in _ordenados_final
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
            _col_obs_2.caption(
                "Astro puntual: se usa el centro del cuerpo para la lectura."
            )

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
                # if "Medio" in dificultad:
                #     _error_obs_min = random.uniform(-0.15, 0.15)
                # elif "Difícil" in dificultad:
                #     _error_obs_min = random.uniform(-0.35, 0.35)

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

            # PARA SIGHT en NAVPAC
            # st.warning(
            #     f"Hs ({_obs['cuerpo']}{_detalle_limbo}): "
            #     f"{formatear_grados_minutos_decimal(_obs['hs'])}"
            # )
            # st.info(
            #     f"Para NavPac SIGHT (DD.MMSS): **{formatear_navpac_dmmss(_obs['hs'])}**"
            # )

            # Mostrar nombre del cuerpo en mayúsculas, y para Sol/Luna añadir L/U según limbo
            # Mostrar SUN/MOON en vez de Sol/Luna
            if _obs["cuerpo"] == "Sol":
                cuerpo_upper = "SUN"
            elif _obs["cuerpo"] == "Luna":
                cuerpo_upper = "MOON"
            else:
                cuerpo_upper = _obs["cuerpo"].upper()
            cuerpo_navpac = cuerpo_upper
            if cuerpo_upper in ("SUN", "MOON"):
                if _obs["limbo"] == "Inferior":
                    cuerpo_navpac += "L"
                elif _obs["limbo"] == "Superior":
                    cuerpo_navpac += "U"
            # # Añadir número NavPac si es estrella conocida
            # if _obs['cuerpo'] in NAVPAC_STAR_INDEX:
            #     st.success(f"Body Name: {cuerpo_navpac} (No. {NAVPAC_STAR_INDEX[_obs['cuerpo']]})")
            # else:
            #     st.success(f"Body Name: {cuerpo_navpac}")

            st.markdown(
                f"""
    ### Observation Details
    Enter this in NavPac's `SIGHT` program. Then run `DR` to see your position estimate based on this observation.
    - Date: `{st.session_state.hora_actual.strftime("%m.%d%Y")}`
    - Time: `{st.session_state.hora_actual.strftime("%H:%M")} UTC`
    - He: `{_altura_ojo_ft:.1f} ft`
    - Hs: `{formatear_navpac_dmmss(_obs['hs'])}` ({formatear_grados_minutos_decimal(_obs['hs'])})
    - Body: {f"`{NAVPAC_STAR_INDEX[_obs['cuerpo']]}` (`{cuerpo_navpac}`)" if _obs['cuerpo'] in NAVPAC_STAR_INDEX else f"`{cuerpo_navpac}`"}
    """
            )

    # 4. EL MAPA DE LA VERDAD
    st.header("4. Posicionamiento")
    u_lat_dr, u_lon_dr = st.session_state.pos_dr[-1]
    lat_dr_dms, lon_dr_dms = formatear_lat_lon_dms(u_lat_dr, u_lon_dr)
    st.caption(f"Estima actual (DMS): Lat {lat_dr_dms} | Lon {lon_dr_dms}")
    col_lat, col_lon = st.columns(2)

    if "fix_lat_texto" not in st.session_state:
        st.session_state.fix_lat_texto = formatear_angulo_dms(u_lat_dr, es_latitud=True)
    if "fix_lon_texto" not in st.session_state:
        st.session_state.fix_lon_texto = formatear_angulo_dms(
            u_lon_dr, es_latitud=False
        )

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
            st.error(
                "No se puede revelar con Fix inválido. Revisa el formato DDºmm:ss."
            )
            st.stop()

        st.session_state.revelado = True
        st.session_state.fix_revelado = (fix_lat, fix_lon)

        # Registrar Fix en bitácora
        lat_real_fix, lon_real_fix = st.session_state.pos_real[-1]
        err_fix = distancia_nmi(lat_real_fix, lon_real_fix, fix_lat, fix_lon)
        nueva_fix = {
            "Paso": len(st.session_state.log_fixes) + 1,
            "Fecha/Hora UTC": st.session_state.hora_actual.strftime("%d-%m-%Y %H:%M"),
            "Lat Fix": formatear_angulo_dms(fix_lat, es_latitud=True),
            "Lon Fix": formatear_angulo_dms(fix_lon, es_latitud=False),
            "Lat Real": formatear_angulo_dms(lat_real_fix, es_latitud=True),
            "Lon Real": formatear_angulo_dms(lon_real_fix, es_latitud=False),
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
            location=(lat, lon),
            radius=5,
            color="blue",
            fill=True,
            fill_opacity=0.85,
            tooltip=tooltip,
        ).add_to(m)

    # --- Track real + marcadores (solo si revelado) ---
    if st.session_state.revelado:
        if len(st.session_state.pos_real) > 1:
            folium.PolyLine(st.session_state.pos_real, color="red", weight=2).add_to(m)
        for i, (lat, lon) in enumerate(st.session_state.pos_real):
            tooltip = "Salida (real)" if i == 0 else f"Posición real #{i}"
            folium.CircleMarker(
                location=(lat, lon),
                radius=5,
                color="red",
                fill=True,
                fill_opacity=0.85,
                tooltip=tooltip,
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

with fix_tab:
    st.title("FIX calculator")

    st.markdown(
        f"""

```
Assumed position (DR):
Latitude : {lat_dr_dms}
Longitude: {lon_dr_dms}
```             

"""
    )
    # Input DR lat/lon (DDºmm:ss),  two  columns

    from angulos import parse_dms

    # we write the converted decimal DR position below the inputs, or an error if the format is invalid
    dr_lat_decimal = parse_dms(dr_lat_texto)
    dr_lon_decimal = parse_dms(dr_lon_texto)
    st.write(f"DR Latitude (decimal): {dr_lat_decimal}")
    st.write(f"DR Longitude (decimal): {dr_lon_decimal}")

    # now we can input up to 3 altitude intercept (a float A|T) and the azimuth (ZN float, ZN represents the azimuth measured from the north)

    st.caption("Up to 3 altitude intercepts (a) and azimuths (ZN):")
    # First row: a1, a2, a3
    col_a1, col_a2, col_a3 = st.columns(3)
    a1 = col_a1.text_input("a1 (altitude intercept)", value="10.5 A")
    a2 = col_a2.text_input("a2 (altitude intercept)", value="8.2 T")
    a3 = col_a3.text_input("a3 (altitude intercept)", value="")
    # Second row: zn1, zn2, zn3
    col_zn1, col_zn2, col_zn3 = st.columns(3)
    zn1 = col_zn1.text_input("ZN1 (azimuth from north)", value=45.0)
    zn2 = col_zn2.text_input("ZN2 (azimuth from north)", value=120.0)
    zn3 = col_zn3.text_input("ZN3 (azimuth from north)", value="")

    # Show FIX:
    from lop import compute_fix_multi
    from tipos import LOP, Position

    dr = Position(lat=dr_lat_decimal, lon=dr_lon_decimal)

    lops = []
    for a, zn in [(a1, zn1), (a2, zn2), (a3, zn3)]:
        if not a.strip() or not zn.strip():
            continue
        try:
            a_val = float(a[:-1].strip())
            zn_val = float(zn)
            lops.append(LOP(a_val, zn_val))
        except ValueError:
            st.warning(
                f"Invalid input for a or ZN: '{a}' or '{zn}'. Skipping this LOP."
            )

    if len(lops) >= 2:
        fix = compute_fix_multi(dr, lops)

        st.write("### Fix result:")
        st.markdown(
            f"""

```
Fix Latitude : {formatear_angulo_dms(fix.lat, es_latitud=True)}
Fix Longitude: {formatear_angulo_dms(fix.lon, es_latitud=False)}
```             

"""
        )

    else:
        st.warning(
            "Please enter at least two valid altitude intercept (a) and azimuth (ZN) to compute the FIX."
        )
