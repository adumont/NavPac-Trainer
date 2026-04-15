import math
import re
from dataclasses import dataclass

from tipos import Position


def parse_dms(value: str) -> float:
    """
    Converts DDºmm:ss (or variants) to decimal degrees.

    Supports:
    - 40º26'46"N
    - 40 26 46 N
    - -40º26:46
    - 3º42'W
    """
    value = value.strip().upper()

    sign = 1

    if "S" in value or "W" in value:
        sign = -1

    # remove letters
    value = re.sub(r"[NSEW]", "", value)

    parts = re.split(r"[^\d.]+", value)
    parts = [p for p in parts if p]

    if not parts:
        raise ValueError(f"Invalid format: {value}")

    deg = float(parts[0])
    minutes = float(parts[1]) if len(parts) > 1 else 0
    seconds = float(parts[2]) if len(parts) > 2 else 0

    decimal = deg + minutes / 60 + seconds / 3600

    return sign * decimal


def parse_lat_lon(lat_str: str, lon_str: str) -> Position:
    return Position(
        lat=parse_dms(lat_str),
        lon=parse_dms(lon_str),
    )


def dms_texto_a_decimal(texto: str, es_latitud: bool = True) -> float:
    """Converts a DMS text (DDºmm:ss H) to decimal degrees. Example: '36º31:39 N' -> 36.5275"""
    import re

    patron = r"^\s*([+-]?\d{1,3})\s*[°º]\s*(\d{1,2})\s*[:']\s*(\d{1,2})(?:\s*\"?)\s*([NSEWnsew])?\s*$"
    m = re.match(patron, texto)
    if not m:
        raise ValueError("Invalid format. Use DDºmm:ss (e.g. 36º31:60 N)")

    grados_raw = int(m.group(1))
    minutos = int(m.group(2))
    segundos = int(m.group(3))
    hemi = m.group(4).upper() if m.group(4) else None

    if minutos < 0 or minutos > 59 or segundos < 0 or segundos > 59:
        raise ValueError("Minutes/seconds out of range (00-59)")

    signo = -1 if grados_raw < 0 else 1
    grados = abs(grados_raw)
    valor = grados + (minutos / 60.0) + (segundos / 3600.0)

    if hemi:
        if es_latitud and hemi not in ("N", "S"):
            raise ValueError("Latitude must use N or S")
        if not es_latitud and hemi not in ("E", "W"):
            raise ValueError("Longitude must use E or W")
        signo = -1 if hemi in ("S", "W") else 1

    valor *= signo

    limite = 90 if es_latitud else 180
    if abs(valor) > limite:
        raise ValueError(
            f"Value out of range for {'latitude' if es_latitud else 'longitude'}"
        )

    return valor


def formatear_angulo_dms(valor: float, es_latitud: bool = True) -> str:
    """Formats a decimal angle to DMS with hemisphere. Example: 36.5275 -> '36º31:39 N'"""
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


def formatear_lat_lon_dms(lat: float, lon: float) -> tuple[str, str]:
    """Returns (lat_dms, lon_dms) tuple in DMS format for latitude and longitude.
    Example: 36.5275, -6.2833 -> ('36º31:39 N', '06º17:00 W')"""
    return (
        formatear_angulo_dms(lat, es_latitud=True),
        formatear_angulo_dms(lon, es_latitud=False),
    )


def formatear_position(pos: Position) -> tuple[str, str]:
    """Formats a Position to DMS with hemisphere. Example: Position(36.5275, -6.2833) -> ('36º31:39 N', '06º17:00 W')"""
    return formatear_lat_lon_dms(pos.lat, pos.lon)

def formatear_navpac_dmmss(valor: float) -> str:
    """Formats a decimal angle to DD.MMSS with rounded minutes and seconds.
    Example: 36.5275 -> 36.3159 (31 minutes and 39 seconds)"""
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


def formatear_grados_mm(valor: float) -> str:
    """Formats a decimal angle to DDMm with rounded minutes.
    Example: 36.5275 -> 36º31' (rounding minutes)"""
    signo = "-" if valor < 0 else ""
    abs_val = abs(valor)
    grados = int(abs_val)
    minutos_float = (abs_val - grados) * 60
    minutos = int(round(minutos_float))
    if minutos == 60:
        minutos = 0
        grados += 1

    return f"{signo}{grados:02d}º{minutos:02d}"


def formatear_grados_minutos_decimal(valor: float, decimales_minutos: int = 1) -> str:
    """Formats a decimal angle to DDM.mmm with the specified number of decimal places in minutes.
    Example: 36.5275 with decimales_minutos=1 -> 36º31.6'"""
    signo = "-" if valor < 0 else ""
    abs_val = abs(valor)
    grados = int(abs_val)
    minutos = round((abs_val - grados) * 60, decimales_minutos)

    if minutos >= 60:
        minutos = 0.0
        grados += 1

    ancho = 2 if decimales_minutos == 0 else 3 + decimales_minutos
    return f"{signo}{grados:02d}º{minutos:0{ancho}.{decimales_minutos}f}'"
