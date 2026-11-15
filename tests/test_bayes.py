"""Tests of the optional Bayesian classification (skipped when PyMC is not installed)."""
import numpy as np
import pandas as pd
import pytest

pytest.importorskip("pymc")
from chowclassifier.bayes import BayesChow, classify_draws  # noqa: E402


def test_classify_draws():
    r = 0.01
    b = np.array([0.0, 0.05, -0.05, 0.0, 0.05, 0.02, 0.05, -0.05, -0.02])
    a = np.array([0.0, 0.0, 0.0, 0.05, -0.05, 0.05, 0.02, -0.02, -0.05])
    h = np.array([False, False, False, True, True, True, True, True, True])
    assert list(classify_draws(b, a, h, r)) == ["N", "I", "D", "NI", "ID", "iI", "Ii", "Dd", "dD"]


def _series(slope_before, slope_after, bkp, seed=1, limit=2.0):
    rng = np.random.default_rng(seed)
    x = np.repeat(np.arange(2005, 2025), 15).astype(float)
    mu = np.log(5) + slope_before * (x - 2005) + (slope_after - slope_before) * np.clip(x - bkp, 0, None)
    y = np.exp(mu + rng.normal(0, 0.5, len(x)))
    cens = y < limit
    return pd.DataFrame(dict(year=x, conc=np.where(cens, limit, y), nd=cens))


@pytest.mark.parametrize("before,after,bkp,expected", [(-0.05, -0.05, 2015, "D"), (0.06, -0.10, 2015, "ID")])
def test_bayes_censored(before, after, bkp, expected):
    df = _series(before, after, bkp)
    assert df["nd"].any()
    bc = BayesChow(df, timecol="year", ycol="conc", censcol="nd", log_y=True, rope=0.01,
                   margin=None, chains=2, draws=400, tune=400, random_seed=3).run()
    assert bc.treeclass == expected
    if len(expected) == 2:
        assert bc.p_break > 0.95 and abs(bc.breakpoint - bkp) <= 2


def test_chewdata_bayes():
    from chowclassifier import ChewData
    a, b = _series(-0.05, -0.05, 2015, seed=4), _series(0.0, 0.0, 2015, seed=5)
    df = pd.concat([a.assign(name="dec"), b.assign(name="flat")], ignore_index=True)
    C = ChewData(df=df, namecol="name", timecol="year", ycol="conc", method="bayes", censcol="nd",
                 bayes_kwargs=dict(log_y=True, rope=0.01, chains=2, draws=300, tune=300))
    C.run(initial_breakpoint=2015)
    r = C.results_df().set_index("name")
    assert r.loc["dec", "treeclass"] == "D" and r.loc["flat", "treeclass"] == "N"
