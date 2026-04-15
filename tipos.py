from dataclasses import dataclass


@dataclass
class Position:
    lat: float  # decimal degrees
    lon: float  # decimal degrees


@dataclass
class LOP:
    a: float  # intercept distance in nautical miles
    zn: float  # azimuth of the LOP in degrees (0 = North, 90 = East)
