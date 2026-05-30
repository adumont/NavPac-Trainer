import math

import pytest

from navpac.navigation import (
    CADIZ,
    TENERIFE,
    CUERPOS_CELESTES,
    NAVPAC_STAR_INDEX,
    mover_barco,
)


class TestConstants:
    def test_cadiz_coords(self):
        assert CADIZ == (36.5333, -6.2833)

    def test_tenerife_coords(self):
        assert TENERIFE == (28.4667, -16.2500)


class TestCuerposCelestes:
    def test_sun_present(self):
        assert "Sol" in CUERPOS_CELESTES

    def test_moon_present(self):
        assert "Luna" in CUERPOS_CELESTES

    def test_polaris_present(self):
        assert "Polaris" in CUERPOS_CELESTES

    def test_expected_count(self):
        assert len(CUERPOS_CELESTES) == 20


class TestNavpacStarIndex:
    def test_polaris_index(self):
        assert NAVPAC_STAR_INDEX["Polaris"] == 0

    def test_sirius_index(self):
        assert NAVPAC_STAR_INDEX["Sirius"] == 18

    def test_expected_count(self):
        assert len(NAVPAC_STAR_INDEX) == 14


class TestMoverBarco:
    def test_no_movement(self):
        lat, lon = mover_barco(0, 0, 0, 0)
        assert lat == pytest.approx(0)
        assert lon == pytest.approx(0)

    def test_north_travel(self):
        lat, lon = mover_barco(0, 0, 0, 60)
        assert lat == pytest.approx(1.0, abs=1e-2)
        assert lon == pytest.approx(0, abs=1e-2)

    def test_east_travel_at_equator(self):
        lat, lon = mover_barco(0, 0, 90, 60)
        assert lat == pytest.approx(0, abs=1e-4)
        assert lon == pytest.approx(1.0, abs=1e-3)

    def test_east_travel_at_mid_lat(self):
        lat, lon = mover_barco(40, 0, 90, 60)
        assert lat == pytest.approx(40, abs=1e-2)
        expected_dlon = 1.0 / math.cos(math.radians(40))
        assert lon == pytest.approx(expected_dlon, abs=1e-2)

    def test_south_travel(self):
        lat, lon = mover_barco(10, 0, 180, 60)
        assert lat == pytest.approx(9.0, abs=1e-2)
        assert lon == pytest.approx(0, abs=1e-2)

    def test_west_travel_at_equator(self):
        lat, lon = mover_barco(0, 0, 270, 60)
        assert lat == pytest.approx(0, abs=1e-4)
        assert lon == pytest.approx(-1.0, abs=1e-3)

    def test_rhumb_045(self):
        dist = 60 * math.sqrt(2)
        lat, lon = mover_barco(0, 0, 45, dist)
        assert lat == pytest.approx(1.0, abs=1e-2)
        assert lon == pytest.approx(1.0, abs=1e-2)

    def test_known_vector(self):
        lat, lon = mover_barco(36, -6, 229, 24)
        assert lat == pytest.approx(35.73, abs=1e-1)
        assert lon == pytest.approx(-6.44, abs=1e-1)
