from dataclasses import dataclass


@dataclass
class Position:
    lat: float  # grados decimales
    lon: float  # grados decimales


@dataclass
class LOP:
    a: float  # distancia a la LOP en millas náuticas
    zn: float  # rumbo de la LOP en grados (0 = Norte, 90 = Este)
