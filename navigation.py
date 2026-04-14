import math
from streamlit import cache_resource
from skyfield.api import Loader, wgs84, Star

# --- Constantes ---

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


@cache_resource
def cargar_skyfield():
    from pathlib import Path

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
