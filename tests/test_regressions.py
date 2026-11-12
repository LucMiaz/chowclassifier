"""Regression tests for bugs fixed in 1.1.4."""
import io
import contextlib
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from chowclassifier import Chow, ChewData
from chowclassifier import utilities
from chowclassifier.utilities import conf_int_to_trend, guess_timelapse_type


def _data(seed=0, groupcol="g"):
    rng = np.random.default_rng(seed)
    x = np.arange(40)
    return pd.DataFrame({"year": x, "value": x + rng.normal(0, 0.3, 40),
                         groupcol: np.where(x % 2, "a", "b"), "name": "s1"})


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kwargs)


@pytest.fixture
def chow():
    c = Chow(df=_data(), margin=5)
    c.run()
    return c


def test_plot_with_default_arguments(chow, tmp_path):
    chow.plot(filename=str(tmp_path / "x.png"))      # fillparams=None used to raise
    assert (tmp_path / "x.png").exists()


def test_plot_options_do_not_leak_into_later_plots(chow, tmp_path):
    before = dict(utilities.FITPARAMS)
    chow.plot(filename=str(tmp_path / "x.png"), fitparams={"linewidth": 7})
    assert utilities.FITPARAMS == before


def test_show_legend_false_without_legend(chow, tmp_path):
    chow.plot(filename=str(tmp_path / "x.png"), show_legend=False)


def test_summary_prints_the_tables(chow):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        chow.summary()
    assert "OLS Regression Results" in out.getvalue()


def test_groups_get_uncorrected_alpha_and_own_colours(chow):
    _, ax = plt.subplots()
    chow.plot_by_group(ax=ax)
    assert chow.gCs["a"].alpha0 == chow.alpha0
    colours = {mcolors.to_hex(c.get_facecolor()[0]) for c in ax.collections
               if c.get_offsets().shape[0] == 20}
    assert len(colours) == 2
    plt.close("all")


def test_chewdata_passes_groupcol():
    ch = ChewData(df=_data(groupcol="site"), groupcol="site", timecol="year", ycol="value")
    _quiet(ch.run)
    assert sorted(set(ch.chows[0].df["g"])) == ["a", "b"]


def test_chewdata_grouped_plot(tmp_path):
    ch = ChewData(df=_data(), timecol="year", ycol="value")
    _quiet(ch.run)
    _quiet(ch.plot, str(tmp_path / "p.png"), grouped=True, linestyles="dashed", title="T")
    assert (tmp_path / "p_00.png").exists()


def test_format_alias(tmp_path):
    ch = ChewData(df=_data(), timecol="year", ycol="value")
    _quiet(ch.run)
    _quiet(ch.plot_individually, savingpath=str(tmp_path), format="png")
    _quiet(ch.plot_by_group, savingpath=str(tmp_path), format="png")
    assert {p.name for p in tmp_path.iterdir()} == {"s1.png", "s1_bygroups.png"}


def test_date_column_with_index_without_zero():
    dates = [f"{y}-01-01" for y in range(2000, 2010)]
    df = pd.DataFrame({"date": dates, "value": np.arange(10.0), "name": "s"},
                      index=range(5, 15))
    ch = _quiet(ChewData, df=df, timecol="date", ycol="value")
    assert ch.timecol == "year"


@pytest.mark.parametrize("dates, expected", [
    (["2000-01-01", "2001-01-01", "2002-01-01", "2005-01-01"], ([0, 1, 2, 5], "year")),
    (["2020-01-01", "2020-01-03", "2020-02-01"], ([0, 2, 31], "day")),
    (["2020-01-01 00:00", "2020-01-01 01:00", "2020-01-01 05:00"], ([0, 1, 5], "hour")),
    (["2020-01-01 00:00", "2020-01-01 00:01", "2020-01-01 00:30"], ([0, 1, 30], "minute")),
    (["2020-01-01 00:00:00", "2020-01-01 00:00:07"], ([0, 7], "second")),
])
def test_guess_timelapse_type(dates, expected):
    assert guess_timelapse_type(pd.Series(pd.to_datetime(dates))) == expected


def test_conf_int_to_trend_accepts_tuples():
    assert conf_int_to_trend((0.1, 0.2)) == 1
    assert conf_int_to_trend((-2, -1)) == 2
    assert conf_int_to_trend((-1, 1)) == 0


def test_cli_flags(tmp_path):
    x = np.arange(30)
    pd.DataFrame({"year": x, "value": x * 1.0, "name": "s"}).to_csv(tmp_path / "d.csv", index=False)
    env = {"MPLBACKEND": "Agg", **{k: v for k, v in __import__("os").environ.items() if k != "MPLBACKEND"}}
    run = lambda *a: subprocess.run([sys.executable, "-m", "chowclassifier", "-f", "d.csv",
                                     "-X", "year", "-y", "value", *a], cwd=tmp_path, env=env,
                                    capture_output=True, text=True, check=True)
    run("--no-figures", "-o", "out.csv")
    assert (tmp_path / "out.csv").exists() and not (tmp_path / "figs").exists()
    run("--fig-format", "png", "--no-table", "--figsize", "8", "4", "--no-sharey")
    assert (tmp_path / "figs" / "s.png").exists()
