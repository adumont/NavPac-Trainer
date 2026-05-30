import math

from celnav_core.config import EARTH_RADIUS_NMI

CADIZ = (36.5333, -6.2833)
TENERIFE = (28.4667, -16.2500)

BODY_NAME_EN = {
    "Sun",
    "Moon",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Polaris",
    "Vega",
    "Sirius",
    "Arcturus",
    "Canopus",
    "Rigel",
    "Procyon",
    "Betelgeuse",
    "Altair",
    "Aldebaran",
    "Deneb",
    "Fomalhaut",
    "Regulus",
    "Antares",
}


def mover_barco(lat, lon, rumbo, distancia):
    R = EARTH_RADIUS_NMI
    lat1, lon1, brng = math.radians(lat), math.radians(lon), math.radians(rumbo)
    d = distancia / R

    lat2 = math.asin(
        math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(brng)
    )
    lon2 = lon1 + math.atan2(
        math.sin(brng) * math.sin(d) * math.cos(lat1),
        math.cos(d) - math.sin(lat1) * math.sin(lat2),
    )
    return math.degrees(lat2), math.degrees(lon2)
