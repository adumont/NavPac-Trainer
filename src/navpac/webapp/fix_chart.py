import math

import matplotlib.pyplot as plt
import numpy as np

from celnav_core.models import Fix, Position


def _nmi_offsets(lat: float, lon: float, ref: Position) -> tuple[float, float]:
    dy = (lat - ref.lat) * 60.0
    dx = (lon - ref.lon) * 60.0 * math.cos(math.radians(ref.lat))
    return dy, dx


def _plot_latlon_grid(ax, dr: Position, half: float):
    step = max(1.0, round(5.0 / math.cos(math.radians(dr.lat)) * 4) / 4)
    lat0 = round(dr.lat / step) * step
    lon0 = round(dr.lon / step) * step
    for lat_i in np.arange(lat0 - 10 * step, lat0 + 10 * step + 0.5 * step, step):
        offy, _ = _nmi_offsets(lat_i, dr.lon, dr)
        if -half <= offy <= half:
            ax.axhline(offy, color="lightgray", linewidth=0.5)
            ax.text(
                half * 0.98,
                offy,
                f"{lat_i:.1f}°",
                fontsize=7,
                color="gray",
                ha="right",
                va="center",
            )
    for lon_i in np.arange(lon0 - 10 * step, lon0 + 10 * step + 0.5 * step, step):
        _, offx = _nmi_offsets(dr.lat, lon_i, dr)
        if -half <= offx <= half:
            ax.axvline(offx, color="lightgray", linewidth=0.5)
            ax.text(
                offx,
                half * 0.98,
                f"{lon_i:.1f}°",
                fontsize=7,
                color="gray",
                ha="center",
                va="top",
            )


def _plot_lop(ax, a: float, zn: float, color, half: float, label: str):
    az_r = math.radians(zn)
    cx = a * math.sin(az_r)
    cy = a * math.cos(az_r)
    ax.plot([0, cx], [0, cy], color=color, linewidth=1, linestyle=":")
    ax.plot(cx, cy, marker="o", color=color, markersize=5)
    hl = half * 2.5
    sx = cx + hl * math.cos(az_r)
    sy = cy - hl * math.sin(az_r)
    ex = cx - hl * math.cos(az_r)
    ey = cy + hl * math.sin(az_r)
    ax.plot([sx, ex], [sy, ey], color=color, linewidth=2, label=label)
    mx, my = (sx + ex) / 2, (sy + ey) / 2
    lw = half * 0.06
    ax.text(mx + lw, my + lw, label, color=color, fontweight="bold", fontsize=9)


def _plot_compass(
    ax,
    intercepts: list[tuple[float, float]],
    half: float,
    colors,
    center: tuple[float, float] = (0, 0),
):
    cx = half * 0.7 + center[0]
    cy = half * 0.7 + center[1]
    cr = half * 0.15
    ax.add_patch(plt.Circle((cx, cy), cr, fill=False, color="gray", linewidth=1))
    for angle_deg, label in [(0, "N"), (90, "E"), (180, "S"), (270, "W")]:
        a = math.radians(angle_deg)
        x = cx + cr * math.sin(a)
        y = cy + cr * math.cos(a)
        ax.plot(x, y, marker="+", color="gray", markersize=3)
        ax.text(
            cx + cr * 1.25 * math.sin(a),
            cy + cr * 1.25 * math.cos(a),
            label,
            color="gray",
            fontweight="bold",
            fontsize=8,
            ha="center",
            va="center",
        )
    for i, (a, zn) in enumerate(intercepts):
        color = colors[i % len(colors)]
        az_r = math.radians(zn)
        tx = cx + cr * 0.85 * math.sin(az_r)
        ty = cy + cr * 0.85 * math.cos(az_r)
        ax.plot([cx, tx], [cy, ty], color=color, linewidth=2)
        label_angle = zn + 5 if zn < 180 else zn - 5
        la = math.radians(label_angle)
        body_label = f"LOP{i + 1}"
        ax.text(
            cx + cr * 1.4 * math.sin(la),
            cy + cr * 1.4 * math.cos(la),
            f"{body_label} {zn:.0f}°",
            color=color,
            fontsize=7,
            fontweight="bold",
            ha="center",
            va="center",
        )


def plot_fix_chart(
    dr: Position,
    intercepts: list[tuple[float, float]],
    fix: Fix,
    zoom: float = 1.5,
) -> plt.Figure:
    max_intercept = max(abs(a) for a, _ in intercepts) if intercepts else 10.0
    half = max(max_intercept * zoom, 4.0)

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.set_aspect("equal")
    ax.set_title("Fix LOP Chart", fontsize=14, fontweight="bold")
    ax.set_xlabel("<-- West -- East --> (nmi)")
    ax.set_ylabel("<-- South -- North --> (nmi)")
    ax.set_xlim(-half, half)
    ax.set_ylim(-half, half)
    ax.grid(True, linestyle=":", alpha=0.3)
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.axvline(0, color="gray", linewidth=0.5)

    _plot_latlon_grid(ax, dr, half)
    colors = plt.cm.Set1.colors
    for i, (a, zn) in enumerate(intercepts):
        _plot_lop(ax, a, zn, colors[i % len(colors)], half, f"LOP{i + 1}")

    off = half * 0.08
    ax.plot(0, 0, marker="s", color="blue", markersize=8, zorder=5)
    ax.text(off, off, "DR", color="blue", fontweight="bold", fontsize=10)
    fy, fx = _nmi_offsets(fix.lat, fix.lon, dr)
    ax.plot(fx, fy, marker="D", color="red", markersize=10, zorder=5)
    ax.text(fx + off, fy + off, "Fix", color="red", fontweight="bold", fontsize=10)

    _plot_compass(ax, intercepts, half, colors)
    if intercepts:
        ax.legend(loc="lower right", fontsize=9)
    plt.tight_layout()
    return fig
