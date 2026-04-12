"""lines of position lines (LOP) calculations and plotting"""

import math
from typing import List, Tuple

from tipos import LOP, Position


def solve_fix_least_squares(lops: List[LOP]) -> tuple[float, float]:
    """
    lops: lista de LOPs con atributos a y zn_rad

    Devuelve (x, y) en millas náuticas (Este, Norte)
    """

    sum_sin2 = 0.0
    sum_cos2 = 0.0
    sum_sin_cos = 0.0

    sum_a_sin = 0.0
    sum_a_cos = 0.0

    for lop in lops:
        a = lop.a
        zn = math.radians(lop.zn)

        s = math.sin(zn)
        c = math.cos(zn)

        sum_sin2 += s * s
        sum_cos2 += c * c
        sum_sin_cos += s * c

        sum_a_sin += a * s
        sum_a_cos += a * c

    det = sum_sin2 * sum_cos2 - sum_sin_cos**2

    if abs(det) < 1e-6:
        raise ValueError("Geometría mala (LOPs degeneradas)")

    x = (sum_a_sin * sum_cos2 - sum_a_cos * sum_sin_cos) / det
    y = (sum_sin2 * sum_a_cos - sum_sin_cos * sum_a_sin) / det

    return x, y


def apply_offset(dr: Position, x_east: float, y_north: float) -> Position:
    """
    Aplica desplazamiento al DR:
    - x en millas náuticas hacia el Este
    - y en millas náuticas hacia el Norte
    """
    lat = dr.lat + y_north / 60

    lon = dr.lon + x_east / (60 * math.cos(math.radians(dr.lat)))

    return Position(lat, lon)


def compute_fix_multi(
    dr: Position, lops: List[LOP]  # (a, zn_deg)
) -> Position:

    x, y = solve_fix_least_squares(lops)

    return apply_offset(dr, x, y)
