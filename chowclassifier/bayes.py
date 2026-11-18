"""Bayesian Chow classification, with support for censored data (optional, needs PyMC).

Install with ``pip install chowclassifier[bayes]`` (PyMC), ``chowclassifier[nutpie]`` (faster
sampler) or ``chowclassifier[jax]`` (NumPyro/JAX sampler, optionally on GPU).

The frequentist :class:`~chowclassifier.chow.Chow` tests a breakpoint with an F-test and calls a
trend significant when its confidence interval excludes zero. :class:`BayesChow` fits instead

* a single line, ``y = a + b x``, or
* a line with one breakpoint ``tau``: slope ``b`` before and ``b + delta`` after, continuous at
  ``tau`` (segmented regression, default) or with a jump ``gamma`` in level as in the Chow test
  (``continuous=False``),

with the breakpoint a discrete parameter over the candidate values (as searched by ``Chow``),
marginalised in the model. The posterior gives the probability of a break, the probability of each
breakpoint and the slopes, and each posterior draw is classified with the same 14 classes as
``Chow`` (N, I, D, NN, NI, ND, IN, ID, iI, Ii, DN, DI, dD, Dd). A slope is "N" when it lies inside
a region of practical equivalence ``[-rope, rope]`` rather than when a test fails to reject zero,
so that the absence of a trend can be supported by the data, and the class probabilities do not
become overconfident just because a series has many points.

Censored data. Values below a detection or quantification limit (non-detects) are common in
environmental monitoring. Give a boolean column ``censcol`` (True when the value is a limit, i.e.
the true value is below it): these rows enter the likelihood through the normal cumulative
distribution function (Tobit model) instead of being dropped, replaced by half the limit or
treated as measured values.

Example::

    from chowclassifier.bayes import BayesChow
    bc = BayesChow(df, timecol="year", ycol="conc", censcol="below_lod", log_y=True, rope=0.01)
    bc.run()
    bc.treeclass, bc.class_probabilities, bc.p_break, bc.breakpoint
    bc.plot()
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd

from .utilities import TREND_COLORS

CLASSES = ["N", "I", "D", "NN", "NI", "ND", "IN", "ID", "iI", "Ii", "DN", "DI", "dD", "Dd"]


def _require_pymc():
    try:
        import pymc  # noqa: F401
    except ImportError as e:  # pragma: no cover - depends on the environment
        raise ImportError("BayesChow needs PyMC: install it with `pip install chowclassifier[bayes]`") from e
    return pymc


def classify_draws(b_before: np.ndarray, b_after: np.ndarray, has_break: np.ndarray, rope: float) -> np.ndarray:
    """Chow classes of posterior draws.

    :param b_before: slope before the break (or the single slope when there is no break), per draw
    :param b_after: slope after the break, per draw (ignored where ``has_break`` is False)
    :param has_break: boolean, per draw
    :param rope: half-width of the no-trend region, in slope units
    :return: array of class labels (see ``CLASSES``)
    """
    def sgn(b):
        return np.where(b > rope, 1, np.where(b < -rope, 2, 0))
    s1, s2 = sgn(b_before), sgn(b_after)
    single = np.array(["N", "I", "D"], dtype=object)[s1]
    lab = np.array([["NN", "NI", "ND"], ["IN", "Ii", "ID"], ["DN", "DI", "Dd"]], dtype=object)
    br = lab[s1, s2]
    br = np.where((s1 == 1) & (s2 == 1), np.where(b_after > b_before, "iI", "Ii"), br)
    br = np.where((s1 == 2) & (s2 == 2), np.where(b_after < b_before, "dD", "Dd"), br)
    return np.where(has_break, br, single)


class BayesChow:
    """Bayesian Chow classification of one time series, optionally with censored values.

    :param df: data with a time column and a value column (and optionally a censoring column)
    :param name: name of the series
    :param initial_breakpoint: centre of the breakpoint search (default: middle of the unique times)
    :param timecol: time column (numeric, e.g. decimal year)
    :param ycol: value column; for a censored row, the limit
    :param censcol: boolean column, True when the value is a limit (left-censored); None if no censoring
    :param margin: as in ``Chow``: number of candidate breakpoints on each side of the initial one;
                   None to try every time that leaves ``min_points`` unique times on each side
    :param min_points: minimum number of unique times before and after a candidate breakpoint
    :param log_y: model log(y); the slopes and ``rope`` are then relative changes per time unit
                  (reported as exp(slope) - 1)
    :param rope: half-width of the no-trend region (slope units; relative change if ``log_y``)
    :param p_break: prior probability of a breakpoint, spread evenly over the candidates
    :param break_threshold: posterior probability of a break above which the series is classified
                            with a break (as the Bonferroni-corrected F-test of ``Chow``); the class
                            is then the most probable one among the draws of the retained model.
                            The probabilities of all classes over all draws are in
                            ``class_probabilities_all``
    :param continuous: line continuous at the breakpoint (default) or with a jump (Chow test)
    :param slope_sd: prior SD of the slopes, in units of SD(y) per SD(time)
    :param draws, tune, chains: sampler settings
    :param sampler: "pymc" (default), "nutpie", "numpyro" or "blackjax" (passed to pm.sample as nuts_sampler)
    :param random_seed: seed of the sampler
    """

    def __init__(self, df: pd.DataFrame, name: str = "", initial_breakpoint: Optional[float] = None,
                 timecol: str = "year", ycol: str = "value", censcol: Optional[str] = None,
                 margin: Optional[int] = 2, min_points: int = 3, log_y: bool = False, rope: float = 0.0,
                 p_break: float = 0.5, break_threshold: float = 0.95, continuous: bool = True,
                 slope_sd: float = 1.0,
                 draws: int = 1000, tune: int = 1000, chains: int = 4, sampler: str = "pymc",
                 random_seed: int = 42):
        cols = [timecol, ycol] + ([censcol] if censcol else [])
        d = df.loc[:, cols].dropna(subset=[timecol, ycol]).copy()
        d.columns = ["X", "y"] + (["cens"] if censcol else [])
        if not censcol:
            d["cens"] = False
        d["X"] = pd.to_numeric(d["X"])
        d["y"] = pd.to_numeric(d["y"])
        d["cens"] = d["cens"].astype(bool)
        if log_y:
            if (d["y"] <= 0).any():
                raise ValueError(f"{name}: log_y needs positive values (and limits)")
            d["y"] = np.log(d["y"])
        self.df = d.sort_values("X").reset_index(drop=True)
        self.name = name
        self.initial_breakpoint = initial_breakpoint
        self.margin, self.min_points = margin, min_points
        self.log_y, self.continuous, self.p_break_prior = log_y, continuous, p_break
        self.break_threshold = break_threshold
        self.rope = np.log1p(rope) if log_y else rope
        self.slope_sd = slope_sd
        self.draws, self.tune, self.chains, self.sampler, self.random_seed = draws, tune, chains, sampler, random_seed
        self.breakpoints = None
        self.p_break = None   # posterior probability of a break (after run)
        self.idata = None
        self.p_comp = None
        self.class_draws = None
        self.class_probabilities = None
        self.treeclass = None
        self.p_break = None
        self.breakpoint = None
        self.tt = -1
        self.color = "#000000"

    # ------------------------------------------------------------------
    def candidate_breakpoints(self) -> np.ndarray:
        """Candidate breakpoints: unique times leaving ``min_points`` unique times on each side,
        within ``margin`` positions of the initial breakpoint (all of them if margin is None)."""
        X = np.sort(self.df["X"].unique())
        k = self.min_points
        cand = X[k:len(X) - k + 1]
        if len(cand) == 0:
            return cand
        if self.margin is not None:
            ib = self.initial_breakpoint if self.initial_breakpoint is not None else X[len(X) // 2]
            i = int(np.argmin(np.abs(cand - ib)))
            cand = cand[max(0, i - self.margin): i + self.margin + 1]
        return cand

    def _build(self):
        pm = _require_pymc()
        import pytensor.tensor as pt
        d = self.df
        cand = self.candidate_breakpoints()
        self.breakpoints = cand
        xs = d["X"].std() or 1.0
        ys = d["y"].std() or 1.0
        xc, yc = d["X"].mean(), d["y"].mean()
        x = ((d["X"] - xc) / xs).to_numpy()
        y = ((d["y"] - yc) / ys).to_numpy()
        bk = (cand - xc) / xs
        cen = d["cens"].to_numpy()
        self._scale = (xc, xs, yc, ys)
        K = len(bk)
        # The components share their parameters: slope b before the break and b + delta after it (and
        # a jump gamma in level if not continuous); the no-break line is the same with delta = gamma = 0.
        # With separate parameters per component, the posterior has one mode per component and the
        # sampler cannot move between them (the break probability then depends on where a chain starts).
        with pm.Model() as model:
            a = pm.Normal("a", 0, 2.5)
            b = pm.Normal("b", 0, self.slope_sd)
            sigma = pm.HalfNormal("sigma", 1.0)
            dist0 = pm.Normal.dist(a + b * x, sigma)
            ll0 = pt.where(cen, pm.logcdf(dist0, y), pm.logp(dist0, y)).sum()
            if K:
                delta = pm.Normal("delta", 0, self.slope_sd)
                X = x[:, None]
                after = (X >= bk[None, :]).astype(float)
                mu = a + b * X + delta * after * (X - bk)
                if not self.continuous:
                    gamma = pm.Normal("gamma", 0, 1.0)
                    mu = mu + gamma * after
                distk = pm.Normal.dist(mu, sigma)
                Y, C = y[:, None], cen[:, None]
                llk = pt.where(C, pm.logcdf(distk, Y), pm.logp(distk, Y)).sum(axis=0)
                lp = pt.concatenate([pt.atleast_1d(np.log1p(-self.p_break_prior) + ll0),
                                     np.log(self.p_break_prior) - np.log(K) + llk])
            else:
                lp = pt.atleast_1d(ll0)
            pm.Deterministic("lp", lp)
            pm.Potential("mixture", pm.math.logsumexp(lp))
        return model

    def run(self, **sample_kwargs):
        """Sample the posterior and classify. Extra keyword arguments go to ``pymc.sample``."""
        pm = _require_pymc()
        model = self._build()
        kw = dict(draws=self.draws, tune=self.tune, chains=self.chains, random_seed=self.random_seed,
                  progressbar=False, target_accept=0.9)
        if self.sampler != "pymc":
            kw["nuts_sampler"] = self.sampler
        kw.update(sample_kwargs)
        with model:
            self.idata = pm.sample(**kw)
        self.classify()
        return self

    def _draws(self, var):
        a = np.asarray(self.idata.posterior[var].values)
        return a.reshape(a.shape[0] * a.shape[1], *a.shape[2:])

    def classify(self):
        """Classes of the posterior draws, class probabilities and the modal class."""
        xc, xs, yc, ys = self._scale
        lp = self._draws("lp")
        lp = lp - lp.max(axis=1, keepdims=True)
        p = np.exp(lp)
        p /= p.sum(axis=1, keepdims=True)
        self.p_comp = p.mean(axis=0)  # Rao-Blackwellised posterior probability of each component
        rng = np.random.default_rng(self.random_seed)
        comp = (p.cumsum(axis=1) > rng.random((len(p), 1))).argmax(axis=1)
        has = comp > 0
        f = ys / xs  # slope back to data units per time unit
        b0 = self._draws("b") * f
        b1 = b0
        b2 = (self._draws("b") + self._draws("delta")) * f if len(self.breakpoints) else b0
        self._slopes = dict(b0=b0, b1=b1, b2=b2, has=has, comp=comp)
        before = np.where(has, b1, b0)
        after = np.where(has, b2, b0)
        self.class_draws = classify_draws(before, after, has, self.rope)
        self.class_probabilities_all = (pd.Series(self.class_draws).value_counts(normalize=True)
                                        .reindex(CLASSES).fillna(0.0))
        self.p_break = float(1 - self.p_comp[0])
        self.has_break = bool(len(self.breakpoints)) and self.p_break >= self.break_threshold
        # classify within the retained model (break or no break), as Chow does after its F-test
        keep = has if self.has_break else ~has
        if keep.sum() < 100:  # too few draws of the retained component: use them all
            keep = np.ones_like(has)
        self._keep = keep
        self.class_probabilities = (pd.Series(self.class_draws[keep]).value_counts(normalize=True)
                                    .reindex(CLASSES).fillna(0.0))
        self.treeclass = self.class_probabilities.idxmax()
        self.breakpoint = float(self.breakpoints[np.argmax(self.p_comp[1:])]) if self.has_break else None
        last = self.treeclass[-1]
        self.tt = {"N": 0, "I": 1, "D": 2}[last.upper()]
        self.color = TREND_COLORS[self.tt]
        return self.params()

    def _summ(self, b):
        q = np.quantile(b, [0.025, 0.5, 0.975]) if len(b) else np.full(3, np.nan)
        if self.log_y:
            q = np.expm1(q)
        return dict(slope=q[1], slope_ci_lower=q[0], slope_ci_upper=q[2],
                    p_increase=float((b > self.rope).mean()) if len(b) else np.nan,
                    p_decrease=float((b < -self.rope).mean()) if len(b) else np.nan)

    def params(self) -> dict:
        """Results: class, class probabilities, break probability and year, slopes (median and 95 %
        credible interval; relative change per time unit if ``log_y``) without and with the break."""
        s = self._slopes
        has = s["has"]
        out = dict(name=self.name, treeclass=self.treeclass, p_class=float(self.class_probabilities.max()),
                   p_break=self.p_break, breakpoint=self.breakpoint, n=len(self.df),
                   n_censored=int(self.df["cens"].sum()))
        out.update({f"model0_{k}": v for k, v in self._summ(s["b0"][~has]).items()})
        out.update({f"model1_{k}": v for k, v in self._summ(s["b1"][has]).items()})
        out.update({f"model2_{k}": v for k, v in self._summ(s["b2"][has]).items()})
        out.update({f"p_{c}": float(v) for c, v in self.class_probabilities.items()})
        out["rhat_max"] = self.rhat_max()
        return out

    def rhat_max(self) -> float:
        """Largest split R-hat of the slope and scale parameters (simple rank-free version)."""
        vals = []
        for v in ["a", "b", "delta", "gamma", "sigma"]:
            if v not in self.idata.posterior:
                continue
            a = np.asarray(self.idata.posterior[v].values)  # chain, draw
            c, n = a.shape[0], a.shape[1] // 2
            if c * 2 < 2 or n < 2:
                continue
            s = np.concatenate([a[:, :n], a[:, n:2 * n]], axis=0)
            w = s.var(axis=1, ddof=1).mean()
            b = n * s.mean(axis=1).var(ddof=1)
            vals.append(np.sqrt(((n - 1) / n * w + b / n) / w) if w > 0 else np.nan)
        return float(np.nanmax(vals)) if vals else np.nan

    def summary(self) -> str:
        p = self.params()
        txt = (f"{self.name}: class {p['treeclass']} (P = {p['p_class']:.2f}), P(break) = {p['p_break']:.2f}"
               + (f" at {p['breakpoint']}" if p['breakpoint'] is not None else ""))
        return txt

    def plot(self, ax=None, filename: Optional[str] = None, n_lines: int = 0, band: bool = True,
             xlabel: str = "", ylabel: str = "", title: Optional[str] = None):
        """Data (open markers: censored values at their limit) and the posterior median fit with its
        95 % band, mixing the no-break and break components in proportion to their probability."""
        import matplotlib.pyplot as plt
        main = ax is None
        if main:
            fig, ax = plt.subplots(figsize=(10, 5))
        d = self.df
        tr = np.exp if self.log_y else (lambda v: v)
        ax.scatter(d.loc[~d.cens, "X"], tr(d.loc[~d.cens, "y"]), s=10, color="#444", alpha=0.5, label="measured")
        if d.cens.any():
            ax.scatter(d.loc[d.cens, "X"], tr(d.loc[d.cens, "y"]), s=12, facecolor="none", edgecolor="#999",
                       marker="v", alpha=0.6, label="below limit")
        grid = np.linspace(d.X.min(), d.X.max(), 200)
        xc, xs, yc, ys = self._scale
        g = (grid - xc) / xs
        a, b = self._draws("a"), self._draws("b")
        fits = a[:, None] + b[:, None] * g
        if len(self.breakpoints):
            comp = self._slopes["comp"]
            bk = ((self.breakpoints - xc) / xs)[np.maximum(comp - 1, 0)][:, None]
            after = g[None, :] >= bk
            fb = fits + self._draws("delta")[:, None] * after * (g - bk)
            if not self.continuous:
                fb = fb + self._draws("gamma")[:, None] * after
            fits = np.where((comp > 0)[:, None], fb, fits)
        fits = yc + ys * fits
        q = np.quantile(fits, [0.025, 0.5, 0.975], axis=0)
        ax.plot(grid, tr(q[1]), color=self.color, lw=2, label=f"{self.treeclass} (P = {self.class_probabilities.max():.2f})")
        if band:
            ax.fill_between(grid, tr(q[0]), tr(q[2]), color=self.color, alpha=0.2, lw=0)
        if self.breakpoint is not None:
            ax.axvline(self.breakpoint, color="#999", ls="--", lw=1)
        if self.log_y:
            ax.set_yscale("log")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(self.name if title is None else title)
        ax.legend()
        if main:
            if filename:
                fig.savefig(filename, bbox_inches="tight")
                plt.close(fig)
            else:
                plt.show()
        return ax


def run_many(df: pd.DataFrame, namecol: str = "name", progress: bool = True, **kwargs) -> pd.DataFrame:
    """Run :class:`BayesChow` on every group of ``df`` (column ``namecol``); returns one row per series.
    Keyword arguments are passed to :class:`BayesChow`."""
    rows = []
    groups = df.groupby(namecol)
    it = groups
    if progress:
        from tqdm import tqdm
        it = tqdm(groups, total=groups.ngroups)
    for name, g in it:
        try:
            rows.append(BayesChow(g, name=str(name), **kwargs).run().params())
        except (ValueError, RuntimeError) as e:
            rows.append(dict(name=str(name), error=str(e)))
    return pd.DataFrame(rows)
