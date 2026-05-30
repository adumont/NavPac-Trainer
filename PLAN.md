# Migration Plan: NavPac-Trainer → celnav-core

## Context

**NavPac-Trainer** (`C:\Projects\NavPac-Trainer`) is a Streamlit-based celestial navigation trainer. It simulates ship voyages, generates sextant sights, and helps users practice celestial navigation with an HP-41C NavPac calculator workflow.

**celnav-core** (`C:\Projects\celnav-core`) is a shared celestial navigation Python library used by polaris2 and other projects. It provides ephemeris computation (`body_alt_az`), sextant sight simulation (`compute_ho`), sight reduction (`solve_fix_least_squares`, `compute_hc_zn`), angle utilities (`deg_to_ddmmss`, `format_angle`), and Pydantic models (`Position`, `Fix`, `SextantReading`, `SightReduction`).

**Goal:** Replace NavPac-Trainer's locally implemented celestial navigation logic with celnav-core as a dependency, eliminating duplicate code and benefiting from a shared, tested library.

---

## Architecture Overview

### Current NavPac-Trainer modules:

| File | Purpose | Lines |
|------|---------|-------|
| `app.py` | Streamlit UI (3 tabs: Route, Navigation, Sextant, Fix Calculator) | 733 |
| `navigation.py` | Skyfield ephemeris, sextant simulation, DR movement, distance, body catalog | 182 |
| `angulos.py` | DMS parse/format, NavPac-specific formatting | 173 |
| `lop.py` | LOP fix solving (least-squares multi-LOP) | 67 |
| `tipos.py` | Position dataclass, LOP dataclass | 13 |

### Desired end state:

| File | Purpose | Approx lines | Change |
|------|---------|-------------|--------|
| `app.py` | Same UI, imports from celnav-core, English body names | ~710 | Update imports + body naming |
| `navigation.py` | DR movement only (`mover_barco`), waypoints (`CADIZ`, `TENERIFE`) | ~30 | Strip everything else |
| `angulos.py` | NavPac-specific HP-41C formatters only | ~60 | Remove DMS parsers + replaceable formatters |
| `lop.py` | **Deleted** — replaced by `celnav_core.core.reduction.solve_fix_from_intercepts()` | 0 | Removed entire file |
| `tipos.py` | Re-export `Position` from celnav-core + thin wrapper | ~10 | Re-export |

### Body name mapping (key decision):

Current code uses **Spanish** names internally ("Sol", "Luna", "Marte", etc.). celnav-core uses **English** ("Sun", "Moon", "Mars", etc.). The migration **switches the UI to English**, eliminating the need for a translation layer.

---

## Workflow

- [x] Mark phases in PLAN.md as they are completed (checkboxes `[x]`)
- [x] Keep commits clean and individual per phase

---

## Phase 0: Plan Confirmation

- [x] Review this PLAN.md
- [x] Confirm Phase 1 test scope
- [x] Confirm Phase 2 celnav-core additions
- [x] Confirm Phase 3 migration approach (direct refactor, not wrappers)

---

## Phase 1: Test `navigation.py` + `lop.py` (lock current behavior)

**Rationale:** These two modules will be most affected by the migration. Writing tests first ensures we know exactly what behavior to preserve.

### Phase 1.0 — Move source code to `src/` layout

- [x] Create `src/navpac/` package with `__init__.py`
- [x] Move `angulos.py`, `navigation.py`, `lop.py`, `tipos.py` into `src/navpac/`
- [x] Move `app.py` into `src/navpac/webapp/app.py` with updated `navpac.*` imports
- [x] Create `src/navpac/webapp/main.py` with Streamlit launcher entry point (later collapsed into `app.py`)
- [x] Add `[project.scripts]` entry point `webapp = "navpac.webapp.app:main"`
- [x] Add `[build-system]` and `[tool.setuptools.packages.find]` to `pyproject.toml`
- [x] Remove root-level `.py` files (now in `src/`)
- [x] `uv run webapp` starts successfully

### Phase 1.1 — Setup test infrastructure

- [x] Create `tests/` directory at repo root
- [x] Create `tests/__init__.py` (empty)
- [x] Create `tests/conftest.py` with shared fixtures
- [x] Add test configuration to `pyproject.toml`

### Phase 1.2 — `tests/test_navigation.py` (only surviving functions)

- [x] `test_mover_barco` — 8 tests all pass
- [x] `test constants` — CADIZ, TENERIFE, CUERPOS_CELESTES, NAVPAC_STAR_INDEX

**Rationale:** Only functions that survive the migration (not replaced by celnav-core) get tests. Functions like `correccion_dip_minutos`, `semidiametro_minutos`, `distancia_nmi`, `lectura_sextante`, `cuerpos_visibles` will be replaced — skip those.

#### A. Surviving functions

**`test_mover_barco`:**

| Test | Input | Expected | Notes |
|------|-------|----------|-------|
| `test_zero_distance` | Same point twice | `0.0` | |
| `test_equator_degree` | `(0,0)` to `(0,1)` at equator | `60.0` | 1° longitude at equator = 60 nmi |
| `test_meridian_degree` | `(0,0)` to `(1,0)` | `60.0` | 1° latitude = 60 nmi |
| `test_45_parallel` | `(45,0)` to `(45,1)` | `60*cos(45°) ≈ 42.43` | |
| `test_known_pair` | Madrid–Barcelona coords | Pre-computed value | |
| `test_symmetric` | A→B equals B→A | Same result | |
| `test_antipodal` | `(0,0)` to `(0,180)` | Half Earth circumference ≈ 10800 nmi | Not exact (Earth not perfect sphere) |
| `test_negative_coords` | Mix of N/S and E/W | Correct sign handling | |

#### B. Skyfield-dependent functions (mocking required)

**Mocking strategy** for `lectura_sextante` and `cuerpos_visibles`:

These functions call `observacion_aparente(nombre, lat, lon, dt_utc)` which builds a Skyfield observer chain. We mock it at the `observacion_aparente` level:

```python
@pytest.fixture
def mock_apparent(mocker):
    """Mock observacion_aparente to return controlled apparent object."""
    mock_apparent_obj = MagicMock()
    # Mock .altaz() to return controlled values
    mock_apparent_obj.altaz.return_value = (alt_degrees, az_degrees, distance)
    # Mock .distance().km
    mock_distance = MagicMock()
    mock_distance.km = 149600000.0
    mock_apparent_obj.distance.return_value = mock_distance
    
    mocker.patch("navigation.observacion_aparente", return_value=mock_apparent_obj)
    return mock_apparent_obj
```

For different test cases, the fixture creates different mock return values.

### Phase 1.3 — `tests/test_lop.py` — **skipped** (lop.py deleted in Phase 3.4)

### Phase 1.4 — Run tests and verify

- [ ] `uv run pytest tests/ -v` — all pass
- [ ] `uv run pytest --cov --cov-report=term-missing` — confirm coverage metrics
- [ ] `uv run ruff check tests/` — no lint issues

---

## Phase 2: celnav-core additions (non-breaking)

**Location:** `C:\Projects\celnav-core`

**Principle:** All additions are additive — no existing function signatures change, no existing tests break.

### Phase 2.1 — Extend `SextantReading` model

**File:** `src/celnav_core/models.py`

Add these fields to `SextantReading`:

```python
class SextantReading(BaseModel):
    body_name: str
    hs: float
    ho: float
    utc: datetime
    real_altitude: float
    azimuth: float             # NEW — apparent azimuth in degrees
    correction_total: float
    dip_arcmin: float          # NEW — dip correction in arcminutes (always negative)
    refraction_arcmin: float   # NEW — refraction in arcminutes (always positive)
    semidiameter_arcmin: float # NEW — semidiameter in arcminutes (>0 for Sun/Moon, 0 otherwise)
```

All new fields have no default — they are required.

**Impact:** Existing consumers that construct `SextantReading(positional_args...)` will break if they omit these fields. Use keyword-argument construction (which is the style in `compute_ho()`). Alternatively, give them defaults of `0.0` to be truly non-breaking (but this silently loses data). **Decision: keyword-only after the 5th positional param, or add with defaults?** The existing `compute_ho()` calls it with keyword args, so it's safe. Any external code constructing `SextantReading(lat, lon, ...)` positionally would break, but that's unlikely in practice.

### Phase 2.2 — Update `compute_ho()`

**File:** `src/celnav_core/core/sight.py`

Update `compute_ho()` to:

1. Capture azimuth from `body_alt_az()` (currently discarded with `_`)
2. Compute individual corrections:
   - `dip_arcmin = dip * 60.0` (convert from degrees to arcmin, keep sign)
   - `refraction_arcmin = (apparent_alt - geometric_alt) * 60.0` (positive)
   - `semidiameter_arcmin = sd * 60.0` (convert from degrees to arcmin)
3. Populate all new `SextantReading` fields

**Important:** Current `compute_ho()` always uses **lower limb** (subtracts sd from hs). The NavPac-Trainer also supports **upper limb** (adds sd). We need to consider: add an optional `limb` parameter to `compute_ho()`? If yes, `limb: str = "Lower"` with values "Lower", "Upper", "Center".

**Decision: Add `limb` parameter to `compute_ho()` with backward-compatible default of `"Lower"`.**

Updated signature:
```python
def compute_ho(
    body_name: str,
    dt: datetime,
    real_pos: Position,
    he_ft: float,
    limb: str = "Lower",
) -> SextantReading:
```

Logic change for limb:
```python
limb_sign = {"Lower": -1, "Upper": 1, "Center": 0}.get(limb, -1)
hs = apparent_alt - dip + limb_sign * sd
```

**Note:** The `semidiameter_arcmin` field always stores the absolute value (positive), regardless of limb. The limb only affects `hs`.

### Phase 2.3 — Add `haversine_distance()`

**File:** `src/celnav_core/core/reduction.py` (or new `src/celnav_core/utils/geo.py`)

```python
def haversine_distance(p1: Position, p2: Position) -> float:
    """Great-circle distance between two positions in nautical miles."""
```

Extract the haversine computation from `compute_fix_error()` into a standalone function, then have `compute_fix_error()` call it.

Implementation:
```python
_EARTH_RADIUS_NMI = 3440.065

def haversine_distance(p1: Position, p2: Position) -> float:
    dlat = math.radians(p1.lat - p2.lat)
    dlon = math.radians(p1.lon - p2.lon)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(p2.lat))
        * math.cos(math.radians(p1.lat))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return c * _EARTH_RADIUS_NMI
```

Update `compute_fix_error()` to use `haversine_distance()`:
```python
def compute_fix_error(fix: Fix, real_pos: Position) -> Fix:
    error_nmi = haversine_distance(fix, real_pos)
    return Fix(lat=fix.lat, lon=fix.lon, error_nmi=error_nmi, iterations=fix.iterations)
```

**Note:** `compute_fix_error()` currently takes `fix: Fix` and uses `fix.lat, fix.lon` and `real_pos.lat, real_pos.lon`. The `haversine_distance()` takes `Position` objects. Since `Fix` has `lat, lon` fields just like `Position`, the function works with both (duck typing). But for clean typing, we could make `haversine_distance` accept anything with `.lat, .lon`.

**Tests for `test_reduction.py`:**
- `test_haversine_zero` — same point → 0
- `test_haversine_equator_degree` — (0,0) to (0,1) → ~60
- `test_haversine_meridian_degree` — (0,0) to (1,0) → ~60
- `test_haversine_45_parallel` — (45,0) to (45,1) → ~42.43
- `test_haversine_symmetric` — A→B = B→A
- `test_haversine_known_values` — verify against pre-computed cases

### Phase 2.4 — Add `solve_fix_from_intercepts()`

**File:** `src/celnav_core/core/reduction.py`

A lower-level fix solver that takes raw (intercept, azimuth) pairs without needing SightReduction objects:

```python
def solve_fix_from_intercepts(
    intercepts: list[tuple[float, float]],
    dr: Position,
) -> Fix:
    """Solve fix from raw intercept (nmi) and azimuth (deg) pairs.

    Args:
        intercepts: List of (intercept_nmi, azimuth_deg) pairs.
                    Positive intercept = toward body (in azimuth direction).
        dr: Dead reckoning position.

    Returns:
        Fix with computed lat/lon. iterations=0 if < 2 intercepts provided.
    """
    if len(intercepts) < 2:
        return Fix(lat=dr.lat, lon=dr.lon, iterations=0)

    mat = []
    vec = []
    for a, zn in intercepts:
        az_r = math.radians(zn)
        mat.append([math.cos(az_r), math.sin(az_r)])
        vec.append(a)

    mat_arr = np.array(mat, dtype=float)
    vec_arr = np.array(vec, dtype=float)
    x, _, _, _ = np.linalg.lstsq(mat_arr, vec_arr, rcond=None)

    dlat_deg = float(x[0]) / 60.0
    dlon_deg = float(x[1]) / (60.0 * math.cos(math.radians(dr.lat)))

    return Fix(lat=dr.lat + dlat_deg, lon=dr.lon + dlon_deg, iterations=1)
```

**Note:** This is a convenience wrapper. The core math is identical to `solve_fix_least_squares()` but avoids requiring SightReduction objects. This is useful for the NavPac-Trainer fix calculator where the user enters intercept/azimuth manually.

**Tests for `test_reduction.py`:**
- `test_two_perpendicular` — `[(10, 0), (10, 90)]` with DR at equator → lat shift = 10/60, lon shift = 10/60
- `test_single_intercept` — returns DR with iterations=0
- `test_empty` — returns DR with iterations=0
- `test_three_intercepts` — overdetermined system
- `test_anti_parallel` — `[(10, 0), (-10, 180)]` → East cancels, North averages

### Phase 2.5 — Add `format_navpac_dmmss()`

**File:** `src/celnav_core/utils/angles.py`

Formats a decimal degree value into the HP-41C NavPac `DD.MMSS` string format (e.g., `36.5275°` → `"36.3139"`).

```python
def format_navpac_dmmss(deg: float) -> str:
    """Format decimal degrees to NavPac DD.MMSS string.

    Example:
        >>> format_navpac_dmmss(36.5275)
        '36.3139'
    """
    sign = "-" if deg < 0 else ""
    packed = deg_to_ddmmss(abs(deg))
    d = int(packed // 10000)
    mmss = packed - d * 10000
    return f"{sign}{d}.{mmss:04.0f}"
```

**Tests for `test_angles.py`:**
- `test_positive` — `36.5275` → `"36.3139"` (31 min 39 sec)
- `test_negative` — `-36.5275` → `"-36.3139"`
- `test_zero` — `0` → `"0.0000"`
- `test_exact_degree` — `45.0` → `"45.0000"`
- `test_exact_minute` — `45.5` → `"45.3000"`
- `test_rounding` — `45.5001` rounded behavior

### Phase 2.6 — Add `parse_dms_string()`

**File:** `src/celnav_core/utils/angles.py`

Parse a human-readable DMS string to decimal degrees.

```python
def parse_dms_string(s: str) -> float:
    """Parse a DMS string to decimal degrees.

    Supports formats:
        - "40º26'46\"N" (or any Unicode variants of °, ', ")
        - "40 26 46 N" (whitespace separated)
        - "40°26'46\"" (no hemisphere, sign implied)
        - "40:26:46" (colon separated)
        - "-40º26'46\"" (negative sign)
        - "3º42'W" (degrees and minutes only)

    Returns:
        Decimal degrees. Negative for S/W hemisphere.
    """
```

Implementation approach: normalize separators, extract hemisphere sign, parse components.

**Tests for `test_angles.py`:**
- `test_full_dms_north` — `"40º26'46\"N"` → `40.4461...`
- `test_full_dms_south` — `"40º26'46\"S"` → `-40.4461...`
- `test_full_dms_west` — `"3º42'W"` → `-3.7`
- `test_full_dms_east` — `"3º42'E"` → `3.7`
- `test_whitespace` — `"40 26 46 N"`
- `test_colon` — `"40:26:46"`
- `test_negative_sign` — `"-40 26 46"`
- `test_no_hemisphere` — `"40º26'46\""`
- `test_edge_0` — `"0º0'0\""` → `0.0`
- `test_edge_90n` — `"90º0'0\"N"` → `90.0`
- `test_invalid` — `""` raises `ValueError`, `"abc"` raises `ValueError`

### Phase 2.7 — Update `__init__.py` exports

**File:** `src/celnav_core/__init__.py`

Add to `__all__`:
- `haversine_distance`
- `solve_fix_from_intercepts`
- `format_navpac_dmmss`
- `parse_dms_string`

### Phase 2.8 — Run celnav-core tests

- [ ] `cd C:\Projects\celnav-core && uv run pytest -v` — all existing tests pass
- [ ] `cd C:\Projects\celnav-core && uv run pytest --cov --cov-fail-under=90` — coverage maintained
- [ ] `cd C:\Projects\celnav-core && uv run ruff check --fix . && uv run ruff format`

---

## Phase 3: Migrate NavPac-Trainer

### Phase 3.1 — Add celnav-core dependency

**File:** `pyproject.toml`

```toml
dependencies = [
    ...existing...,
    "celnav-core",
]

[tool.uv.sources]
celnav-core = { path = "../celnav-core" }
```

The `[tool.uv.sources]` section points to the local development copy. Before final commit, replace with the git URL:

```toml
# Final version:
"celnav-core @ git+https://github.com/adumont/celnav-core.git"
```

Then:
- [ ] `uv lock` to update lock file
- [ ] `uv sync` to install in venv

### Phase 3.2 — Refactor `tipos.py`

**Before (13 lines):**
```python
from dataclasses import dataclass

@dataclass
class Position:
    lat: float
    lon: float

@dataclass
class LOP:
    a: float
    zn: float
```

**After (~5 lines):**
```python
from celnav_core.models import Position  # noqa: F401
```
(LOP is no longer needed — replaced by `solve_fix_from_intercepts()`)

### Phase 3.3 — Refactor `navigation.py`

**Before (182 lines):** Contains `CUERPOS_CELESTES`, `NAVPAC_STAR_INDEX`, `RADIOS_CUERPOS_KM`, `cargar_skyfield()`, `observacion_aparente()`, `altura_cuerpo()`, `correccion_dip_minutos()`, `semidiametro_minutos()`, `lectura_sextante()`, `cuerpos_visibles()`, `mover_barco()`, `distancia_nmi()`.

**After (~30 lines):**

```python
import math
from celnav_core import EARTH_RADIUS_NMI

CADIZ = (36.5333, -6.2833)
TENERIFE = (28.4667, -16.2500)

BODY_NAME_EN = {
    "Sun", "Moon", "Venus", "Mars", "Jupiter", "Saturn",
    "Polaris", "Vega", "Sirius", "Arcturus", "Canopus",
    "Rigel", "Procyon", "Betelgeuse", "Altair", "Aldebaran",
    "Deneb", "Fomalhaut", "Regulus", "Antares",
}

def mover_barco(lat, lon, rumbo, distancia):
    """Great-circle DR: move ship from (lat,lon) on course rumbo for distancia nmi."""
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
```

**Removed** items all come from celnav-core directly. The `mover_barco()` function stays because it's app-specific voyage simulation, not celestial navigation.

### Phase 3.4 — Refactor `lop.py`

**Deleted entirely** (67 lines). Replaced by `celnav_core.core.reduction.solve_fix_from_intercepts()`.

### Phase 3.5 — Refactor `angulos.py`

**Before (173 lines):** Contains `parse_dms()`, `parse_lat_lon()`, `dms_texto_a_decimal()`, `formatear_angulo_dms()`, `formatear_lat_lon_dms()`, `formatear_position()`, `formatear_navpac_dmmss()`, `formatear_grados_mm()`, `formatear_grados_minutos_decimal()`.

**After (~60 lines):** Keep only NavPac-specific formatters that have no celnav-core equivalent.

```python
def formatear_angulo_dms(valor: float, es_latitud: bool = True) -> str:
    """Formats decimal degrees to 'DDºmm:ss H' string.
    
    Example: 36.5275 -> '36º31:39 N'
    
    Note: Stays in NavPac-Trainer because celnav-core's format_angle()
    produces 'DD°mm'ss"' (different separators). This format matches the
    HP-41C NavPac display convention.
    """
    ...

def formatear_lat_lon_dms(lat: float, lon: float) -> tuple[str, str]:
    ...

def formatear_position(pos) -> tuple[str, str]:
    ...

def formatear_grados_mm(valor: float) -> str:
    """Formats to 'DDºmm' (degrees and rounded minutes).
    
    Example: 36.5275 -> '36º31'
    
    Used for compact alt/az display in body selector dropdown.
    """
    ...

def formatear_grados_minutos_decimal(valor: float, decimales_minutos: int = 1) -> str:
    """Formats to 'DDºmm.m' (degrees + decimal minutes).
    
    Example: 36.5275 -> '36º31.6'
    """
    ...
```

**Removed:**
- `parse_dms()` → use `celnav_core.utils.angles.parse_dms_string()`
- `parse_lat_lon()` → caller can inline or use celnav-core
- `dms_texto_a_decimal()` → use `celnav_core.utils.angles.parse_dms_string()`
- `formatear_navpac_dmmss()` → use `celnav_core.utils.angles.format_navpac_dmmss()`

### Phase 3.6 — Refactor `app.py`

This is the most involved change. Steps:

1. **Update imports from navigation:**
   - `from navigation import mover_barco, CADIZ, TENERIFE` (keep)
   - Remove: `lectura_sextante, cuerpos_visibles, distancia_nmi, RADIOS_CUERPOS_KM, CUERPOS_CELESTES, NAVPAC_STAR_INDEX`
   - Remove: `from skyfield.api import Star` (no longer needed)

2. **Add imports from celnav-core:**
   ```python
   from celnav_core.models import Position
   from celnav_core.core.sight import compute_ho, dip_correction, semidiameter_deg
   from celnav_core.core.almanac import body_alt_az, visible_bodies, body_alt_az_multiple
   from celnav_core.config import NAVPAC_STAR_INDEX, RADIOS_CUERPOS_KM
   from celnav_core.utils.angles import (
       format_navpac_dmmss, parse_dms_string, body_label, format_position, format_angle,
   )
   from celnav_core.core.reduction import solve_fix_from_intercepts, haversine_distance
   ```

3. **Update update_dr_position:**
   - Replace `dms_texto_a_decimal()` with `parse_dms_string()`
   - Replace `distancia_nmi()` with `haversine_distance()` + Position objects
   - Replace `formatear_angulo_dms()` with `format_angle()` (but note: `format_angle()` produces different format string! If the log format must stay `"DDºmm:ss H"` then keep `formatear_angulo_dms` from the local `angulos.py`)

4. **Update registrar_fix:**
   - Same pattern: use `formatear_lat_lon_dms` from local `angulos.py` or `format_position` from celnav-core (depends on format preference)
   - Replace `distancia_nmi()` with `haversine_distance()`

5. **Update tab_nav (Navigation tab):**
   - `mover_barco` stays (DR simulation)
   - Replace `distancia_nmi()` with `haversine_distance()`
   - Replace `formatear_angulo_dms()` with `format_position()` or local formatter

6. **Update tab_sextant (Sextant tab):**
   - Replace `cuerpos_visibles(_lat_obs, _lon_obs, _dt_utc)` with:
     ```python
     _pos_obs = Position(lat=_lat_obs, lon=_lon_obs)
     _visible_names = visible_bodies(_dt_utc, _pos_obs, min_alt=5.0)
     _visibles = body_alt_az_multiple(_visible_names, _dt_utc, _pos_obs)
     ```
   - Replace `CUERPOS_CELESTES[n] isinstance Star` check with:
     ```python
     _hay_estrellas = any(n not in ("Sun", "Moon") for n in _visibles)
     # Or: _hay_estrellas = any(len(n) > 4 for n in _visibles) — not robust
     # Better: query celnav-core if body is a star
     ```
   - Replace `lectura_sextante(...)` call with `compute_ho(body_name, dt_utc, real_pos, he_ft, limb)`
   - Extract fields from `SextantReading` instead of dict
   - Replace body name checks: `"Sol"` → `"Sun"`, `"Luna"` → `"Moon"`
   - Replace `formatear_navpac_dmmss` with celnav-core's version
   - Replace `formatear_grados_minutos_decimal` with local version (stays in angulos.py)
   - Replace `NAVPAC_STAR_INDEX[_obs['cuerpo']]` — now uses English keys, same dict
   
   **Body display logic (app.py lines 568-580):**
   Before:
   ```python
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
   ```
   After:
   ```python
   body_name = reading.body_name
   if body_name == "Sun":
       cuerpo_navpac = "SUN"
   elif body_name == "Moon":
       cuerpo_navpac = "MOON"
   else:
       cuerpo_navpac = body_name.upper()
   if body_name in ("Sun", "Moon"):
       from celnav_core.core.sight import _LIMB_SIGNS  # or inline the limb check
       cuerpo_navpac += "L" if limb == "Lower" else "U" if limb == "Upper" else ""
   ```
   Or use: `body_label(body_name)` from celnav-core which gives "Sun L", "Moon L", "Sirius (18)" etc.

7. **Update tab_fix (Fix Calculator tab):**
   - Replace `from lop import compute_fix_multi` with `from celnav_core.core.reduction import solve_fix_from_intercepts`
   - Replace `from tipos import LOP, Position` with `from celnav_core.models import Position`
   - Replace LOP construction + compute_fix_multi with:
     ```python
     intercepts = []
     for a, zn in [(a1, zn1), (a2, zn2), (a3, zn3)]:
         if not a.strip() or not zn.strip():
             continue
         try:
             a_val = float(a[:-1].strip())  # strip 'A' or 'T' suffix
             zn_val = float(zn)
             intercepts.append((a_val, zn_val))
         except ValueError:
             ...
     
     dr = Position(lat=dr_lat_decimal, lon=dr_lon_decimal)
     fix = solve_fix_from_intercepts(intercepts, dr)
     ```
   - Access fix with `fix.lat`, `fix.lon` instead of Position attributes

### Phase 3.7 — Verify Phase 1 tests still pass

- [ ] `uv run pytest tests/ -v` — all Phase 1 tests pass unchanged
- [ ] `uv run python -c "import app; print('imports OK')"` — no import errors
- [ ] `uv run streamlit run app.py` — launches without error (manual check)

---

## Phase 4: Quality

- [ ] `uv run ruff check --fix .` — no lint issues
- [ ] `uv run ruff format` — consistent formatting
- [ ] `uv run pytest --cov --cov-report=term-missing` — coverage check (aim for 80%+)
- [ ] Update `pyproject.toml` to swap `{ path = "../celnav-core" }` for `{ git = "https://github.com/adumont/celnav-core.git" }`
- [ ] `uv lock` with final dependency
- [ ] Update `AGENTS.md` if needed
- [ ] Commit: standard "feat: migrate to celnav-core" message

---

## Appendix: Key API Differences

| NavPac-Trainer (old) | celnav-core (new) | Notes |
|---------------------|-------------------|-------|
| `navigation.altura_cuerpo(name, lat, lon, dt)` → `(alt, az)` | `celnav_core.core.almanac.body_alt_az(name, dt, Position(lat, lon))` | Position object vs raw coords |
| `navigation.lectura_sextante(...)` → `dict` | `celnav_core.core.sight.compute_ho(...)` → `SextantReading` | Typed model vs dict |
| `navigation.cuerpos_visibles(lat, lon, dt)` → `{name: (alt, az)}` | `visible_bodies(dt, Position(lat,lon))` → `[names]` + `body_alt_az_multiple(...)` | Two-step vs one-step |
| `navigation.distancia_nmi(lat1, lon1, lat2, lon2)` → `float` | `haversine_distance(Position(lat1,lon1), Position(lat2,lon2))` | Position objects |
| `navigation.correccion_dip_minutos(m)` → `float` | `celnav_core.core.sight.dip_correction(ft)` → `float` (degrees, negative) | Unit + sign convention |
| `navigation.semidiametro_minutos(name, dist_km)` → `float` | `celnav_core.core.sight.semidiameter_deg(name)` → `float` (degrees) | Uses mean vs actual distance |
| `lop.solve_fix_least_squares(lops)` → `(x, y)` | `solve_fix_from_intercepts([(a, zn)], Position)` → `Fix` | Different return type |
| `lop.compute_fix_multi(dr, lops)` → `Position` | `solve_fix_from_intercepts(...)` → `Fix` | Fix has .lat/.lon |
| `angulos.parse_dms(str)` → `float` | `celnav_core.utils.angles.parse_dms_string(str)` | Unified parser |
| `angulos.formatear_navpac_dmmss(deg)` → `str` | `celnav_core.utils.angles.format_navpac_dmmss(deg)` → `str` | Same output |
| `angulos.formatear_angulo_dms(deg)` → `"DDºmm:ss H"` | `celnav_core.utils.angles.format_angle(deg)` → `"DD°mm'ss\""` | Different format — keep local |
| `tipos.Position` dataclass | `celnav_core.models.Position` Pydantic model | Re-export |
| `tipos.LOP` dataclass | — (use raw intercept tuples) | Removed |

## Appendix: celnav-core changes summary

All changes to `C:\Projects\celnav-core`:

| File | Change | Type |
|------|--------|------|
| `src/celnav_core/models.py` | Add `azimuth`, `dip_arcmin`, `refraction_arcmin`, `semidiameter_arcmin` to `SextantReading` | Non-breaking (additive) |
| `src/celnav_core/core/sight.py` | Update `compute_ho()`: capture azimuth, compute individual corrections, add `limb` parameter | Non-breaking (additive, default "Lower") |
| `src/celnav_core/core/reduction.py` | Add `haversine_distance()` | Additive |
| `src/celnav_core/core/reduction.py` | Add `solve_fix_from_intercepts()` | Additive |
| `src/celnav_core/utils/angles.py` | Add `format_navpac_dmmss()` | Additive |
| `src/celnav_core/utils/angles.py` | Add `parse_dms_string()` | Additive |
| `src/celnav_core/__init__.py` | Add new functions to `__all__` | Additive |
