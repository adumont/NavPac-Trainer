import streamlit as st
import datetime
import random
import re

import folium
from streamlit_folium import st_folium
from skyfield.api import Star
import pandas as pd

from angulos import (
    formatear_angulo_dms,
    formatear_lat_lon_dms,
    formatear_navpac_dmmss,
    dms_texto_a_decimal,
    formatear_grados_minutos_decimal,
    formatear_grados_mm,
)

from navigation import (
    mover_barco,
    lectura_sextante,
    cuerpos_visibles,
    distancia_nmi,
    CADIZ,
    TENERIFE,
    RADIOS_CUERPOS_KM,
    CUERPOS_CELESTES,
    NAVPAC_STAR_INDEX,
)


PLACES = {
    "Cadiz": CADIZ,
    "Tenerife": TENERIFE,
    "San Juan (Caribbean)": (18.4655, -66.1057),
    "Havana (Caribbean)": (23.1136, -82.3666),
    "Mumbai (India)": (19.0760, 72.8777),
    "Chennai (India)": (13.0827, 80.2707),
    "Kochi (India)": (9.9312, 76.2673),
    "Cape Town (Africa)": (-33.9249, 18.4241),
    "Durban (Africa)": (-29.8587, 31.0218),
    "Dakar (Africa)": (14.7167, -17.4677),
    "Perth (Australia)": (-31.9505, 115.8605),
    "Sydney (Australia)": (-33.8688, 151.2093),
    "Brisbane (Australia)": (-27.4698, 153.0251),
    "Buenos Aires (Argentina)": (-34.6037, -58.3816),
    "Ushuaia (Argentina)": (-54.8019, -68.3030),
    "Valparaiso (Chile)": (-33.0472, -71.6127),
    "Punta Arenas (Chile)": (-53.1638, -70.9171),
    "San Diego (USA West Coast)": (32.7157, -117.1611),
    "Los Angeles (USA West Coast)": (34.0522, -118.2437),
    "San Francisco (USA West Coast)": (37.7749, -122.4194),
    "Seattle (USA West Coast)": (47.6062, -122.3321),
    "Tokyo (Japan)": (35.6762, 139.6503),
    "Yokohama (Japan)": (35.4437, 139.6380),
    "Kobe (Japan)": (34.6901, 135.1955),
}


def reset_voyage_state(from_coords: tuple[float, float]) -> None:
    st.session_state.hora_actual = datetime.datetime(2026, 5, 15, 8, 0)
    st.session_state.pos_real = [from_coords]
    st.session_state.pos_dr = [from_coords]
    st.session_state.fixes = []
    st.session_state.log_navegacion = []
    st.session_state.log_observaciones = []
    st.session_state.log_fixes = []
    st.session_state.revelado = False
    st.session_state.fix_revelado = None


def update_dr_position(dr_lat: float | str, dr_lon: float | str) -> None:
    try:
        if isinstance(dr_lat, str):
            dr_lat = dms_texto_a_decimal(dr_lat, es_latitud=True)
        if isinstance(dr_lon, str):
            dr_lon = dms_texto_a_decimal(dr_lon, es_latitud=False)

        st.session_state.pos_dr[-1] = (dr_lat, dr_lon)

        # Update the last log entry's DR position and recompute error
        if st.session_state.log_navegacion:
            st.session_state.log_navegacion[-1]["Lat DR"] = formatear_angulo_dms(
                dr_lat, es_latitud=True
            )
            st.session_state.log_navegacion[-1]["Lon DR"] = formatear_angulo_dms(
                dr_lon, es_latitud=False
            )

            n_lat_re, n_lon_re = st.session_state.pos_real[-1]
            diff_nmi = distancia_nmi(dr_lat, dr_lon, n_lat_re, n_lon_re)
            st.session_state.log_navegacion[-1]["Error (nmi)"] = round(diff_nmi, 2)

        st.success("DR position updated.")
    except ValueError as exc:
        st.error(f"Invalid DR position format: {exc}")


# --- CONFIGURATION AND STATE ---
st.set_page_config(
    page_title="NavPac Trainer", layout="wide", page_icon=":material/explore:"
)

if "iniciado" not in st.session_state:
    st.session_state.route_from = "Cadiz"
    st.session_state.route_to = "Tenerife"
    reset_voyage_state(PLACES[st.session_state.route_from])
    st.session_state.iniciado = True

if "log_navegacion" not in st.session_state:
    st.session_state.log_navegacion = []
if "log_fixes" not in st.session_state:
    st.session_state.log_fixes = []
if "route_from" not in st.session_state:
    st.session_state.route_from = "Cadiz"
if "route_to" not in st.session_state:
    st.session_state.route_to = "Tenerife"

from_name = st.session_state.route_from
to_name = st.session_state.route_to
from_coords = PLACES[from_name]
to_coords = PLACES[to_name]

# --- SIDEBAR: CONFIGURATION ---
dificultad = st.sidebar.radio(
    "🌊 Sea State",
    options=["Calm (Easy)", "Moderate (Medium)", "Storm (Hard)"],
)

# -- TABS ---
tab_ruta, tab_nav, tab_sextant, tab_fix = st.tabs(
    ["Route", "Navigation", "Sextant", "Fix Calculator"]
)

with tab_ruta:
    st.title(f"⛵ NavPac Trainer: {from_name} ➡️ {to_name}")

    col_from, col_to, col_apply = st.columns([1, 1, 0.7])
    selected_from = col_from.selectbox(
        "From:",
        options=list(PLACES.keys()),
        index=list(PLACES.keys()).index(from_name),
        key="route_from_selector",
    )
    valid_destinations = [name for name in PLACES.keys() if name != selected_from]
    selected_to = col_to.selectbox(
        "To:",
        options=valid_destinations,
        index=valid_destinations.index(to_name) if to_name in valid_destinations else 0,
        key="route_to_selector",
    )

    if col_apply.button("Apply Route", use_container_width=True):
        st.session_state.route_from = selected_from
        st.session_state.route_to = selected_to
        reset_voyage_state(PLACES[selected_from])
        st.success(f"Route set: {selected_from} ➡️ {selected_to}. Voyage reset.")
        st.rerun()

    route_nmi = distancia_nmi(from_coords[0], from_coords[1], to_coords[0], to_coords[1])
    st.caption(f"Planned great-circle distance: {route_nmi:.1f} nmi")

    with st.expander("📖 Logbook - Mission Data", expanded=True):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("### 📍 Departure Position")
            dep_lat_dms, dep_lon_dms = formatear_lat_lon_dms(
                from_coords[0], from_coords[1]
            )
            st.code(
                f"{from_name}\nLat: {dep_lat_dms}\nLon: {dep_lon_dms}", language="text"
            )

        with col_b:
            st.markdown("### 📅 UTC Clock")
            # Show fixed departure time and current simulator time
            hora_salida = datetime.datetime(2026, 5, 15, 8, 0)
            st.write(f"**Departure:** {hora_salida.strftime('%d-%m-%Y %H:%M')} UTC")
            st.write(
                f"**Current:** {st.session_state.hora_actual.strftime('%d-%m-%Y %H:%M')} UTC"
            )
            st.caption("Use this date/time for the HP-41C Nautical Almanac.")

        with col_c:
            st.markdown("### 🏁 Destination")
            dest_lat_dms, dest_lon_dms = formatear_lat_lon_dms(to_coords[0], to_coords[1])
            st.code(
                f"{to_name}\nLat: {dest_lat_dms}\nLon: {dest_lon_dms}",
                language="text",
            )

with tab_nav:
    # 1. THE HELM
    st.subheader("Engine Orders")
    c1, c2, c3 = st.columns(3)
    rumbo = c1.number_input("Course (º)", 0, 359, 229)
    velocidad = c2.number_input("Speed (knots)", 0, 20, 6)
    # Input for time in HH:MM format
    horas_hhmm = c3.text_input(
        "Time (HH:MM)",
        value="04:00",
        help="Enter the time in HH:MM format (example: 12:30)",
    )
    # Convert HH:MM to decimal hours
    _horas_match = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", horas_hhmm)
    if _horas_match:
        horas = int(_horas_match.group(1)) + int(_horas_match.group(2)) / 60.0
    else:
        st.error("Invalid time format. Use HH:MM (example: 12:30)")
        horas = 0.0

    if st.button("Navigate"):
        st.session_state.hora_previa = st.session_state.hora_actual
        st.session_state.hora_actual += datetime.timedelta(hours=horas)
        distancia = velocidad * horas

        # Move DR (Dead Reckoning) — navigator does not apply drift corrections
        u_lat_dr, u_lon_dr = st.session_state.pos_dr[-1]
        n_lat_dr, n_lon_dr = mover_barco(u_lat_dr, u_lon_dr, rumbo, distancia)
        st.session_state.pos_dr = st.session_state.pos_dr + [(n_lat_dr, n_lon_dr)]

        # Move Real with error and drift (also when speed=0)
        u_lat_re, u_lon_re = st.session_state.pos_real[-1]

        if velocidad == 0:
            # Ship stopped: only currents/drift act according to difficulty
            deriva_vel = {
                "Calm (Easy)": 0.15,
                "Moderate (Medium)": 0.35,
                "Storm (Hard)": 0.8,
            }.get(dificultad, 0.15)
            deriva_rumbo = random.uniform(0, 360)
            n_lat_re, n_lon_re = mover_barco(
                u_lat_re, u_lon_re, deriva_rumbo, deriva_vel * horas
            )
        else:
            err_r, err_v = 0, 0
            if "Medium" in dificultad:
                err_r, err_v = random.uniform(-3, 3), random.uniform(-0.5, 0.5)
            elif "Hard" in dificultad:
                err_r, err_v = random.uniform(-7, 7), random.uniform(-1.2, 1.2)
            vel_real = max(0.0, velocidad + err_v)
            n_lat_re, n_lon_re = mover_barco(
                u_lat_re, u_lon_re, rumbo + err_r, vel_real * horas
            )

        st.session_state.pos_real = st.session_state.pos_real + [(n_lat_re, n_lon_re)]

        # Log entry
        diff_nmi = distancia_nmi(n_lat_dr, n_lon_dr, n_lat_re, n_lon_re)
        nueva_entrada = {
            "Departure Date UTC": st.session_state.hora_previa.strftime(
                "%d-%m-%Y %H:%M"
            ),
            "Course (º)": rumbo,
            "Speed (kn)": velocidad,
            "Hours": horas,
            "Arrival Date UTC": st.session_state.hora_actual.strftime("%d-%m-%Y %H:%M"),
            "Dist DR (nmi)": round(distancia, 1),
            "Lat DR": formatear_angulo_dms(n_lat_dr, es_latitud=True),
            "Lon DR": formatear_angulo_dms(n_lon_dr, es_latitud=False),
            "Lat Real": formatear_angulo_dms(n_lat_re, es_latitud=True),
            "Lon Real": formatear_angulo_dms(n_lon_re, es_latitud=False),
            "Error (nmi)": round(diff_nmi, 2),
        }
        st.session_state.log_navegacion = st.session_state.log_navegacion + [
            nueva_entrada
        ]

        st.success(
            f"Navigation completed. Current time: {st.session_state.hora_actual.strftime('%H:%M')} UTC"
        )
        st.rerun()

    # 2. Dead Reckoning
    st.subheader("Dead Reckoning")

    st.write(
        f"Use `DR` in NavPac with the inputs above (Course = `{rumbo}º`, Speed x Time = `{velocidad * horas} nmi`) to see your estimated position based on Dead Reckoning. Enter it below:"
    )

    # Input DR lat/lon (DDºmm:ss),  two  columns
    col_dr_lat, col_dr_lon = st.columns(2)
    u_lat_dr, u_lon_dr = st.session_state.pos_dr[-1]
    dr_lat_texto = col_dr_lat.text_input(
        "DR Latitude",
        placeholder="Example: 36º32:00 N",
        value=formatear_angulo_dms(u_lat_dr, es_latitud=True),
    )
    dr_lon_texto = col_dr_lon.text_input(
        "DR Longitude",
        placeholder="Example: 06º17:00 W",
        value=formatear_angulo_dms(u_lon_dr, es_latitud=False),
    )

    if st.button("Update DR Position"):
        update_dr_position(dr_lat_texto, dr_lon_texto)

    # --- NAVIGATION LOG TABLE ---
    if st.session_state.log_navegacion:
        st.subheader("Navigation Log")
        df = pd.DataFrame(st.session_state.log_navegacion)

        if (
            "show_real_data" not in st.session_state
            or not st.session_state.show_real_data
        ):
            df = df.drop(columns=["Lat Real", "Lon Real", "Error (nmi)"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.toggle("Show real data", value=False, key="show_real_data")

with tab_sextant:
    # 3. SEXTANT
    st.header("3. Celestial Observation")

    _lat_obs, _lon_obs = st.session_state.pos_dr[-1]
    _dt_utc = st.session_state.hora_actual.replace(tzinfo=datetime.timezone.utc)

    try:
        _visibles = cuerpos_visibles(_lat_obs, _lon_obs, _dt_utc)
    except Exception as _exc:
        _visibles = {}
        st.error(f"Error calculating visible bodies: {_exc}")

    if not _visibles:
        st.warning(
            "No celestial bodies visible (alt > 5°) at this time and position. Advance the time."
        )
    else:

        # Sort: Sun and Moon always on top if visible, then rest by descending altitude
        _ordenados = sorted(_visibles.items(), key=lambda x: -x[1][0])
        _sol_visible = "Sol" in _visibles
        _luna_visible = "Luna" in _visibles
        _hay_estrellas = any(isinstance(CUERPOS_CELESTES[n], Star) for n in _visibles)

        # Build list with Sun and Moon first if present
        _ordenados_final = []
        if _sol_visible:
            _ordenados_final.append(("Sol", _visibles["Sol"]))
        if _luna_visible:
            _ordenados_final.append(("Luna", _visibles["Luna"]))
        for n, v in _ordenados:
            if n not in ("Sol", "Luna"):
                _ordenados_final.append((n, v))

        if _sol_visible:
            st.caption("☀️ The Sun is above the horizon. Daytime observation possible.")
        if _hay_estrellas:
            st.caption("⭐ Visible stars: twilight or night conditions.")

        _opciones_mapa = {
            f"{n}  —  alt {formatear_grados_mm(a)}  az {int(z):03d}°": n
            for n, (a, z) in _ordenados_final
        }
        _sel_str = st.selectbox("Body to observe:", list(_opciones_mapa.keys()))
        _cuerpo_sel = _opciones_mapa[_sel_str]
        _usa_limbo = _cuerpo_sel in RADIOS_CUERPOS_KM

        _col_obs_1, _col_obs_2 = st.columns(2)
        _altura_ojo_ft = _col_obs_1.number_input(
            "Height of Eye (ft)",
            min_value=0.0,
            max_value=100.0,
            value=10.0,
            step=0.5,
            help="Used to apply the dip correction in the Hs reading.",
        )
        _altura_ojo_m = _altura_ojo_ft * 0.3048

        if _usa_limbo:
            _limbo = _col_obs_2.selectbox(
                "Observed limb",
                options=["Lower", "Upper"],
                index=0,
                help="For Sun and Moon, the sextant reading depends on the observed limb.",
            )
        else:
            _limbo = "Center"
            _col_obs_2.caption(
                "Point source: the center of the body is used for the reading."
            )

        if st.button("🔭 Take Sight", key="btn_tomar_altura"):
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
                # elif "Hard" in dificultad:
                #     _error_obs_min = random.uniform(-0.35, 0.35)

                _hs_obs = _obs_real["hs"] + (_error_obs_min / 60.0)
                _obs = {
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

                # Show body name in uppercase, and for Sun/Moon add L/U according to limb
                # Show SUN/MOON instead of Sol/Luna
                if _obs["cuerpo"] == "Sol":
                    cuerpo_upper = "SUN"
                elif _obs["cuerpo"] == "Luna":
                    cuerpo_upper = "MOON"
                else:
                    cuerpo_upper = _obs["cuerpo"].upper()
                cuerpo_navpac = cuerpo_upper
                if cuerpo_upper in ("SUN", "MOON"):
                    if _obs["limbo"] == "Lower":
                        cuerpo_navpac += "L"
                    elif _obs["limbo"] == "Upper":
                        cuerpo_navpac += "U"

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

                entrada_observacion = {
                    "Date/Time UTC": st.session_state.hora_actual.strftime(
                        "%d-%m-%Y %H:%M"
                    ),
                    "DR": f"{formatear_angulo_dms(_lat_obs, es_latitud=True)}, {formatear_angulo_dms(_lon_obs, es_latitud=False)}",
                    "Height of Eye (ft)": _obs["altura_ojo_ft"],
                    "Refraction (min)": round(_obs["refraccion_min"], 2),
                    "Dip (min)": round(_obs["dip_min"], 2),
                    "Body": cuerpo_navpac,
                    "Azimuth (º)": round(_obs["az"], 2),
                    "Semi-diameter (min)": round(_obs["semidiametro_min"], 2),
                    "Hs (DMMSS)": formatear_navpac_dmmss(_obs["hs"]),
                    "Hs (decimal)": round(_obs["hs"], 4),
                }
                st.session_state.log_observaciones = (
                    st.session_state.log_observaciones + [entrada_observacion]
                )
            except Exception as exc:
                st.error(f"Error computing altitude for {_cuerpo_sel}: {exc}")

        if st.session_state.log_observaciones:
            st.subheader("Sight Log")
            import pandas as pd

            df_obs = pd.DataFrame(st.session_state.log_observaciones)
            st.dataframe(df_obs, use_container_width=True, hide_index=True)
        else:
            st.info(
                "You haven't taken any sights yet. Use the '\U0001f52d Take Sight' button to record your first celestial observation."
            )

    # 4. THE MAP OF TRUTH
    st.header("4. Positioning")
    u_lat_dr, u_lon_dr = st.session_state.pos_dr[-1]
    lat_dr_dms, lon_dr_dms = formatear_lat_lon_dms(u_lat_dr, u_lon_dr)
    st.caption(f"Current DR (DMS): Lat {lat_dr_dms} | Lon {lon_dr_dms}")
    col_lat, col_lon = st.columns(2)

    if "fix_lat_texto" not in st.session_state:
        st.session_state.fix_lat_texto = formatear_angulo_dms(u_lat_dr, es_latitud=True)
    if "fix_lon_texto" not in st.session_state:
        st.session_state.fix_lon_texto = formatear_angulo_dms(
            u_lon_dr, es_latitud=False
        )

    fix_lat_texto = col_lat.text_input(
        "Your Fix Latitude (DDºmm:ss)",
        value=st.session_state.fix_lat_texto,
        help="Example: 36º31:59 N",
    )
    fix_lon_texto = col_lon.text_input(
        "Your Fix Longitude (DDºmm:ss)",
        value=st.session_state.fix_lon_texto,
        help="Example: 006º17:00 W",
    )

    st.session_state.fix_lat_texto = fix_lat_texto
    st.session_state.fix_lon_texto = fix_lon_texto

    fix_valido = True
    fix_error = None
    try:
        fix_lat = dms_texto_a_decimal(fix_lat_texto, es_latitud=True)
        fix_lon = dms_texto_a_decimal(fix_lon_texto, es_latitud=False)
        st.caption(f"Internal decimal fix: Lat {fix_lat:.4f} | Lon {fix_lon:.4f}")
    except ValueError as exc:
        fix_valido = False
        fix_error = str(exc)
        st.warning(f"Invalid Fix format: {fix_error}")

    if "revelado" not in st.session_state:
        st.session_state.revelado = False
    if "fix_revelado" not in st.session_state:
        st.session_state.fix_revelado = None

    if st.button("🗺️ Reveal Real Position"):
        if not fix_valido:
            st.error("Cannot reveal with invalid Fix. Check DDºmm:ss format.")
            st.stop()

        st.session_state.revelado = True
        st.session_state.fix_revelado = (fix_lat, fix_lon)

        # Log Fix
        lat_real_fix, lon_real_fix = st.session_state.pos_real[-1]
        err_fix = distancia_nmi(lat_real_fix, lon_real_fix, fix_lat, fix_lon)
        nueva_fix = {
            "Step": len(st.session_state.log_fixes) + 1,
            "Date/Time UTC": st.session_state.hora_actual.strftime("%d-%m-%Y %H:%M"),
            "Lat Fix": formatear_angulo_dms(fix_lat, es_latitud=True),
            "Lon Fix": formatear_angulo_dms(fix_lon, es_latitud=False),
            "Lat Real": formatear_angulo_dms(lat_real_fix, es_latitud=True),
            "Lon Real": formatear_angulo_dms(lon_real_fix, es_latitud=False),
            "Fix/Real Error (nmi)": round(err_fix, 2),
        }
        st.session_state.log_fixes = st.session_state.log_fixes + [nueva_fix]

    if st.session_state.revelado and st.session_state.fix_revelado is not None:
        fix_lat_mapa, fix_lon_mapa = st.session_state.fix_revelado
        lat_real, lon_real = st.session_state.pos_real[-1]
        lat_real_dms, lon_real_dms = formatear_lat_lon_dms(lat_real, lon_real)
        error_nmi = distancia_nmi(lat_real, lon_real, fix_lat_mapa, fix_lon_mapa)
        st.success(f"Real position: Lat {lat_real_dms} | Lon {lon_real_dms}")
        st.info(f"Your Fix error: {error_nmi:.2f} nmi")

    # Map: DR always visible; real track only when revealed
    m = folium.Map(location=[u_lat_dr, u_lon_dr], zoom_start=6)

    # --- DR line (blue) with marker at each waypoint ---
    if len(st.session_state.pos_dr) > 1:
        folium.PolyLine(st.session_state.pos_dr, color="blue", weight=2).add_to(m)
    for i, (lat, lon) in enumerate(st.session_state.pos_dr):
        tooltip = "Departure (DR)" if i == 0 else f"DR #{i}"
        folium.CircleMarker(
            location=(lat, lon),
            radius=5,
            color="blue",
            fill=True,
            fill_opacity=0.85,
            tooltip=tooltip,
        ).add_to(m)

    # --- Real track + markers (only if revealed) ---
    if st.session_state.revelado:
        if len(st.session_state.pos_real) > 1:
            folium.PolyLine(st.session_state.pos_real, color="red", weight=2).add_to(m)
        for i, (lat, lon) in enumerate(st.session_state.pos_real):
            tooltip = "Departure (real)" if i == 0 else f"Real position #{i}"
            folium.CircleMarker(
                location=(lat, lon),
                radius=5,
                color="red",
                fill=True,
                fill_opacity=0.85,
                tooltip=tooltip,
            ).add_to(m)
        # User's Fix
        if st.session_state.fix_revelado is not None:
            fix_lat_mapa, fix_lon_mapa = st.session_state.fix_revelado
            folium.Marker(
                (fix_lat_mapa, fix_lon_mapa),
                icon=folium.Icon(color="green", icon="star"),
                tooltip="Your Fix",
            ).add_to(m)

    # Destination
    folium.Marker(
        to_coords,
        icon=folium.Icon(color="orange", icon="flag"),
        tooltip=f"Destination: {to_name}",
    ).add_to(m)

    st_folium(m, width=800, height=450)

    # Legend
    col_l1, col_l2, col_l3, col_l4 = st.columns(4)
    col_l1.caption("🔵 Blue line/points: your DR (Dead Reckoning)")
    col_l4.caption(f"🟠 Orange flag: Destination ({to_name})")
    if st.session_state.revelado:
        col_l2.caption("🔴 Red line/points: real position of the ship")
        col_l3.caption("🟢 Green star: your entered Fix")

    # --- FIXES TABLE ---
    if st.session_state.log_fixes:
        st.subheader("Fixes Log")
        df_fixes = pd.DataFrame(st.session_state.log_fixes)
        st.dataframe(df_fixes, use_container_width=True, hide_index=True)


with tab_fix:
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

    # now we can input up to 3 altitude intercept (a float A|T) and the azimuth (ZN float, ZN represents the azimuth measured from the north)

    st.caption("Up to 3 altitude intercepts (a) and azimuths (ZN):")
    # First row: a1, a2, a3

    def reset_update_dr_with_fix_flag():
        st.session_state.update_dr_with_fix_clicked = (
            False  # Reset the flag when a new fix is computed
        )

    col_a1, col_a2, col_a3 = st.columns(3)
    a1 = col_a1.text_input(
        "a1 (altitude intercept)",
        value="10.5 A",
        on_change=reset_update_dr_with_fix_flag,
    )
    a2 = col_a2.text_input(
        "a2 (altitude intercept)",
        value="8.2 T",
        on_change=reset_update_dr_with_fix_flag,
    )
    a3 = col_a3.text_input(
        "a3 (altitude intercept)", value="", on_change=reset_update_dr_with_fix_flag
    )
    # Second row: zn1, zn2, zn3
    col_zn1, col_zn2, col_zn3 = st.columns(3)
    zn1 = col_zn1.text_input(
        "ZN1 (azimuth from north)", value=45.0, on_change=reset_update_dr_with_fix_flag
    )
    zn2 = col_zn2.text_input(
        "ZN2 (azimuth from north)", value=120.0, on_change=reset_update_dr_with_fix_flag
    )
    zn3 = col_zn3.text_input(
        "ZN3 (azimuth from north)", value="", on_change=reset_update_dr_with_fix_flag
    )
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
        if "update_dr_with_fix_clicked" not in st.session_state:
            st.session_state.update_dr_with_fix_clicked = False

        if not st.session_state.update_dr_with_fix_clicked:
            with st.container(horizontal=True):
                if st.button("Update DR Position with FIX"):
                    update_dr_position(fix.lat, fix.lon)
                    st.session_state.update_dr_with_fix_clicked = True
                    st.rerun()
                st.write(
                    "⚠️ After updating DR with a FIX you won't be able to recalculate a fix until you take new sights from a new current position."
                )

    else:
        st.warning(
            "Please enter at least two valid altitude intercept (a) and azimuth (ZN) to compute the FIX."
        )
