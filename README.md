# NavPac Simulator — Cadiz to Canary Islands

A web-based celestial navigation trainer built with Streamlit. It simulates a passage from Cádiz to Tenerife, generating realistic sextant sights and Dead Reckoning data that you can directly feed into the **HP-41C NavPac** navigation pac to practice the full star-sight-to-fix workflow without going to sea.

---

## What the App Does

The simulator runs four interconnected modules, each accessible via a tab:

### 1. Route
Overview of the voyage: departure position (Cádiz), destination (Tenerife), UTC clock, and a mission logbook. The displayed date and time are the values you should use when querying the HP-41 Nautical Almanac.

### 2. Navigation
Advance the ship along a chosen course and speed for a given duration. The app maintains two parallel tracks:

- **DR (Dead Reckoning)** — the clean, navigation-error-free track you compute manually.
- **Real position** — a hidden track that accumulates course/speed errors and ocean current drift, scaled by the selected sea-state difficulty (Calm / Moderate / Storm).

After each leg, compare the DR position produced by NavPac's `DR` function with the one the app shows.

### 3. Sextant
Simulates a celestial observation from the current DR position. The app uses the **Skyfield** library (DE421 ephemeris) to compute a true altitude, then applies:

- Standard atmospheric refraction
- Dip correction (from height of eye in feet)
- Upper / Lower limb correction for Sun and Moon

The result is an **Hs** value formatted exactly as NavPac expects (`DMMSS`), together with the body identifier (star number for stars, `SUNL`/`SUNU`/`MOONL`/`MOONU` for Sun and Moon). Copy these values straight into NavPac's `SIGHT` program.

Supported bodies: Sun, Moon, Venus, Mars, Jupiter, Saturn, and 15 navigational stars (Polaris, Sirius, Vega, Arcturus, Canopus, Rigel, and more), each mapped to its NavPac star index number.

### 4. Fix Calculator
Enter the altitude intercepts (**a**, in tenths of a nautical mile, suffix `A` for Away or `T` for Toward) and azimuths (**ZN**) that NavPac's `SIGHT` program outputs, and the app calculates a geometric fix from up to three Lines of Position. You can then push the resulting fix back as the new DR position for the next leg.

---

## How to Use It with the HP-41C NavPac

1. **Start the app**
   ```
   streamlit run app.py
   ```

2. **Set sea state** in the sidebar to choose how much hidden error accumulates.

3. **Route tab** — note the departure time; set the same date/time on your HP-41.

4. **Navigation tab** — choose a course and speed, then press *Navigate*.
   - Run `DR` on the HP-41 with the same inputs to get your estimated position.
   - Enter NavPac's DR result into the simulator to keep both in sync.

5. **Sextant tab** — press *Take Sight* to get a simulated Hs reading.
   - The app shows exactly what to type into NavPac's `SIGHT`: date, time, height of eye, Hs (in DMMSS), and the body code.
   - Run `SIGHT` on the HP-41; record the intercept (**a**) and azimuth (**ZN**) it returns.

6. **Fix Calculator tab** — paste the intercept(s) and azimuth(s) from NavPac.
   - The app computes the intersection of the Lines of Position and displays your Fix.
   - Press *Update DR Position with FIX* to use that fix as the starting point for the next leg.

7. **Positioning section (inside Sextant tab)** — enter your fix coordinates and press *Reveal Real Position* to see how far your celestial navigation placed you from where the ship actually is.

Repeat steps 4–7 for each leg of the passage to Tenerife.

---

## Running the App

**Prerequisites:** Python 3.11+

```bash
pip install -r requirements.txt
streamlit run app.py
```

The first run downloads the DE421 ephemeris (~17 MB) if not already present locally.

---

## Project Structure

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI and session state management |
| `navigation.py` | Skyfield ephemeris wrapper, sextant simulation, ship movement |
| `angulos.py` | Angle formatting and parsing (DMS, NavPac DMMSS, decimal) |
| `lop.py` | Line-of-Position geometry and multi-LOP fix computation |
| `tipos.py` | Shared data classes (`LOP`, `Position`) |
