def dms_texto_a_decimal(texto, es_latitud=True):
    """Convierte un texto en formato DMS (DDºmm:ss H) a decimal. Ejemplo: '36º31:39 N' -> 36.5275"""
    import re

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
        raise ValueError(
            f"Valor fuera de rango para {'latitud' if es_latitud else 'longitud'}"
        )

    return valor


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
    """Devuelve tupla (lat_dms, lon_dms) con formato DMS para latitud y longitud.
    Ejemplo: 36.5275, -6.2833 -> ('36º31:39 N', '06º17:00 W')"""
    return (
        formatear_angulo_dms(lat, es_latitud=True),
        formatear_angulo_dms(lon, es_latitud=False),
    )


def formatear_navpac_dmmss(valor):
    """Formatea un ángulo decimal a DD.MMSS con minutos y segundos redondeados.
    Ejemplo: 36.5275 -> 36.3159 (31 minutos y 39 segundos)"""
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
    """Formatea un ángulo decimal a DDMm con minutos redondeados.
    Ejemplo: 36.5275 -> 36º31' (redondeando minutos)"""
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
    """Formatea un ángulo decimal a DDM.mmm con el número especificado de decimales en los minutos.
    Ejemplo: 36.5275 con decimales_minutos=1 -> 36º31.6'"""
    signo = "-" if valor < 0 else ""
    abs_val = abs(valor)
    grados = int(abs_val)
    minutos = round((abs_val - grados) * 60, decimales_minutos)

    if minutos >= 60:
        minutos = 0.0
        grados += 1

    ancho = 2 if decimales_minutos == 0 else 3 + decimales_minutos
    return f"{signo}{grados:02d}º{minutos:0{ancho}.{decimales_minutos}f}'"
