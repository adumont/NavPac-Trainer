def formatear_angulo_dms(valor: float, es_latitud: bool = True) -> str:
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
    return (
        formatear_angulo_dms(lat, es_latitud=True),
        formatear_angulo_dms(lon, es_latitud=False),
    )


def formatear_position(pos) -> tuple[str, str]:
    return formatear_lat_lon_dms(pos.lat, pos.lon)


def formatear_grados_mm(valor: float) -> str:
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
    signo = "-" if valor < 0 else ""
    abs_val = abs(valor)
    grados = int(abs_val)
    minutos = round((abs_val - grados) * 60, decimales_minutos)

    if minutos >= 60:
        minutos = 0.0
        grados += 1

    ancho = 2 if decimales_minutos == 0 else 3 + decimales_minutos
    return f"{signo}{grados:02d}º{minutos:0{ancho}.{decimales_minutos}f}'"
