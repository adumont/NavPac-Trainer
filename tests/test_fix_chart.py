import pytest
import matplotlib
import numpy as np

from celnav_core.core.reduction import solve_fix_from_intercepts
from celnav_core.models import Fix, Position

from navpac.webapp.fix_chart import _nmi_offsets, plot_fix_chart


class TestNmiOffsets:
    def test_zero_offset(self):
        dr = Position(lat=30.0, lon=-60.0)
        dy, dx = _nmi_offsets(dr.lat, dr.lon, dr)
        assert dy == 0.0
        assert dx == 0.0

    def test_north_offset(self):
        dr = Position(lat=30.0, lon=-60.0)
        dy, dx = _nmi_offsets(31.0, -60.0, dr)
        assert dy == pytest.approx(60.0)
        assert dx == 0.0

    def test_east_offset(self):
        dr = Position(lat=30.0, lon=-60.0)
        dy, dx = _nmi_offsets(30.0, -59.0, dr)
        assert dy == 0.0
        expected_dx = 60.0 * np.cos(np.radians(30))
        assert dx == pytest.approx(expected_dx)


class TestPlotFixChart:
    def test_returns_figure(self):
        dr = Position(lat=30.0, lon=-60.0)
        intercepts = [(10.0, 45.0), (-5.0, 120.0)]
        fix = solve_fix_from_intercepts(intercepts, dr)
        fig = plot_fix_chart(dr, intercepts, fix)
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_returns_figure_two_intercepts(self):
        dr = Position(lat=0.0, lon=0.0)
        intercepts = [(15.0, 0.0), (15.0, 90.0)]
        fix = solve_fix_from_intercepts(intercepts, dr)
        fig = plot_fix_chart(dr, intercepts, fix)
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_single_intercept_still_produces_figure(self):
        dr = Position(lat=45.0, lon=-10.0)
        intercepts = [(5.0, 180.0)]
        fix = Fix(lat=dr.lat, lon=dr.lon, iterations=0)
        fig = plot_fix_chart(dr, intercepts, fix)
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_axes_labels(self):
        dr = Position(lat=30.0, lon=-60.0)
        intercepts = [(10.0, 45.0), (-5.0, 120.0)]
        fix = solve_fix_from_intercepts(intercepts, dr)
        fig = plot_fix_chart(dr, intercepts, fix)
        ax = fig.axes[0]
        assert "West" in ax.get_xlabel()
        assert "South" in ax.get_ylabel()

    def test_legend_present(self):
        dr = Position(lat=30.0, lon=-60.0)
        intercepts = [(10.0, 45.0), (-5.0, 120.0)]
        fix = solve_fix_from_intercepts(intercepts, dr)
        fig = plot_fix_chart(dr, intercepts, fix)
        ax = fig.axes[0]
        assert ax.get_legend() is not None

    def test_title(self):
        dr = Position(lat=30.0, lon=-60.0)
        intercepts = [(10.0, 45.0), (-5.0, 120.0)]
        fix = solve_fix_from_intercepts(intercepts, dr)
        fig = plot_fix_chart(dr, intercepts, fix)
        ax = fig.axes[0]
        assert "Fix LOP Chart" in ax.get_title()

    def test_fix_marked_on_chart(self):
        dr = Position(lat=30.0, lon=-60.0)
        intercepts = [(20.0, 0.0), (20.0, 90.0)]
        fix = solve_fix_from_intercepts(intercepts, dr)
        fig = plot_fix_chart(dr, intercepts, fix)
        ax = fig.axes[0]
        texts = [t.get_text() for t in ax.texts]
        assert "Fix" in texts
        assert "DR" in texts
