# Changelog

All notable changes to chowclassifier are listed here, newest first. Versions
follow [semantic versioning](https://semver.org/); dates are those of the
version bump in `pyproject.toml`.

## 1.1.4 (2026-11-12)

### Fixed
- `Chow.plot()` with default arguments raised `AttributeError`; plot options passed to one call (e.g. `fitparams`) no longer stick to every later plot; `show_legend=False` works when there is no legend.
- `Chow.summary()` prints the regression tables (it printed only the headings).
- `Chow.plot_by_group()`: each group gets its own colour (all groups had the first group's colour), and the sub-analyses use the uncorrected alpha (it was Bonferroni-corrected twice).
- `ChewData` passes `groupcol` to `Chow`, so grouping columns not named `g` are used.
- `ChewData.plot(grouped=True)` works (it raised `AttributeError`); `plot()` forwards options such as `linestyles` to the subplots and shows `title` as the figure title.
- `plot_individually()` and `plot_by_group()` accept `format=` as an alias of `fmt=`; `format=` was silently ignored and figures came out as PDF.
- Dates: yearly data spanning several leap years was indexed in days, hourly and minute data in seconds; now indexed in years, hours and minutes. The format is inferred from the first non-missing date.
- `conf_int_to_trend()` accepts tuples, as documented.
- Command line: `--no-figures` and `--no-table` are flags (`--no-figures False` used to disable the figures), `--sharey`/`--no-sharey`, `--figsize WIDTH HEIGHT`; `--fig-format` also applies to the individual figures; `--xlabel`, `--ylabel` and `--fig-title` are used; new `-g/--groupcol`; `--breakpoints` (never used) warns that it is ignored.

### Changed
- Requires Python ≥ 3.9 (the code already needed 3.8; 3.6 was declared).
- `__pycache__`, `*.egg-info` and the built docs are no longer tracked.
- `test_examples` fails when the example script fails (its exit status was ignored).

### Documentation
- Version shown in the docs and `chowclassifier.__version__` read from the package metadata (they said 1.1.1 and 1.0.9).
- API reference covers `chewdata` and `utilities`; usage examples fixed (`fmt=` instead of `format=`, `plot_by_group` call); Chow test described with k = 2 and F(k, N₁+N₂−2k), as implemented; licence stated as CC BY-NC 4.0, as in `LICENSE`.
- Added this changelog.

## 1.1.3 (2026-04-09)
- Fixed a non-deterministic choice of the initial breakpoint: the midpoint was taken from an unsorted set of times.

## 1.1.2 (2026-04-09)
- The last candidate breakpoint of the search window is now tested (off-by-one in the window).
- Clear `ValueError` when no breakpoint can be tested, or when the breakpoint cannot be determined.
- Figures are closed after saving (memory use with many series).

## 1.1.1b (2026-04-07) and 1.1.1a (2026-04-03)
- `ChewData.plot_individually` passes all plot parameters (labels, scatter, fill and fit parameters) to `Chow.plot`.

## 1.1.1 (2026-03-19)
- Fixed empty unused subplots; breakpoint search constrained by the margin; test example; GitLab CI (pylint, pytest on several Python versions).
- Fixed the statsmodels import.

## 1.1.0 (2026-01-18)
- Packaging with `pyproject.toml`, conda recipe and build instructions; project URLs.
- Sphinx documentation on Read the Docs.

## 1.0.10 (2023-05-29)
- `show_legend` option for the plots.

## 1.0.9 and 1.0.8 (2023-04-20)
- Bug fixes; Jupyter notebook example.

## 1.0.7 (2023-04-17)
- Main classes and utilities split into several modules.
- `ChewData.plot` can show grouped trends; input parsing fixed; consistent use of `initial_breakpoint` and `margin`.
- Option to set the line style of each trend category.

## 1.0.6 (2023-03-29)
- Line style and confidence-interval fill control for the plots.

## 1.0.5 and 1.0.4 (2023-03-10)
- Trends plotted by group, with an optional confidence-interval fill for each group; figure titles fixed.

## 1.0.3 and 1.0.2 (2023-02-16)
- Whole CSV and Excel files parsed automatically.
- Fixed a missing font and an `IndexError` with `initial_breakpoint`.

## 1.0.1 and 1.0.0 (2023-01-17)
- First packaged implementation: `Chow` and `ChewData` classes, plots, CSV and Excel export, tests and CI.

## 0.x (2022)
- Chow classifier script for stock time series.
