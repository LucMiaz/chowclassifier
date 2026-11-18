# ChowClassifier

## Description
There are many application where it is useful to analyse rapidly a large number of time-series for overall trends and possible breakpoint at which the trend changes. For example, spotting increasing trends in potential contaminants concentration from the outputs of non-target screening from high resolution mass spectrometry.

ChowClassifier aims to solve this. It is a script that performs a series of Chow tests on a time-indexed dataset to determine if a breakpoint in the time trends is probable. Two classes `Chow` and `ChewData` enable to perform the tests (and, optionally, `BayesChow` a Bayesian classification that handles censored data, see below), generate plots and export the results in `csv` and `excel`. Dataset with groups can be ran simultaneously with `ChewData` indicating with `namecol` the name of the grouping column. Calling `run` on a `ChewData` instance will create an instance of `Chow` for each group and classify them into the following categories.

| Breakpoint ? | Category | Description |
|--------------|----------|-------------|
| No           |N         | non-significant overall trend |
| No           |   I      | significant increasing overall trend |
| No           | D        | significant decreasing overall trend |
| Yes         | NN        | non-significant trend on set1 and non-significant trend on set2 |
| Yes         | NI        | non-significant trend on set1 and significant increasing trend on set2 |
| Yes         | ND        | non-significant trend on set1 ans significant decreasing trend on set2 |
| Yes         | IN        | significant increasing trend on set1 and non-significant trend on set2 |
| Yes         | ID        | significant increasing trend on set1 and significant decreasing trend on set2 |
| Yes         | iI        | significant increasing trend on both set1 and set2 with greater increase in set2 |
| Yes         | Ii        | significant increasing trend on both set1 and set2 with greater increase in set1 |
| Yes         | DN        | significant decreasing trend on set1 and non-significant trend on set2 |
| Yes         | DI        | significant decreasing trend on set1 and significant increasing trend on set2 |
| Yes         | dD        | significant decreasing trend on both set1 and set2 with greater decrease in set2 |
| Yes         | Dd        | significant decreasing trend on both set1 and set2 with greater decrease in set1 |

where set1 and set2 indicate respectively the data before the breakpoint and after. The decision process for this classification is shown in the following schema:


![Image unavailable, see schema on readthedocs.](docs/img/Categorisation_TT.png)


## Chow test
Chow test was first derived by Gregory Chow[^1] in 1960 and later by Franklin Fisher[^2]. We test the significance of the breakpoint at the Bonferroni-corrected level $\alpha/m$ ($m$ breakpoints tested) with the statistic $Z=\frac{S_c-(S_1+S_2)}{S_1+S_2}\cdot\frac{N_1+N_2-2\cdot k}{k}$, where $k=2$ is the number of parameters of each regression (intercept and slope). It follows an F-distribution with $k$ and $N_1+N_2-2k$ degrees of freedom, where $S_C$ is the sum of squared residuals of the regression on the full time series, $S_1$, $S_2$ are the sums of squared residuals of the regression on the first, and respectively, the second half of the time series and $N_1$, $N_2$ are the number of observation for each half. See also [^3].

## Installation
```
pip install chowclassifier
```

## Citation

If you use this package in your research, please cite:

Influence of Season on Biodegradation Rates in Rivers
Run Tian, Malte Posselt, Luc T. Miaz, Kathrin Fenner, and Michael S. McLachlan
Environmental Science & Technology 2024 58 (16), 7144-7153
DOI: [10.1021/acs.est.3c10541](https://doi.org/10.1021/acs.est.3c10541)

[Download citation](https://pubs.acs.org/action/downloadCitation?doi=10.1021%2Facs.est.3c10541&include=cit&format=ris&direct=true&downloadFileName=acs.est.3c10541)

## Use
The script can be run on any file with `python -m chowclassifier -f path/to/file/filename.csv -X xcol -y ycol -n grouping_name` (`chowclassifier --help` lists all options) or it can be imported:

```python
from chowclassifier import ChewData

C = ChewData(filename="example/data/stocks.csv",
             timecol="Date",      # name of the time column (x-axis)
             ycol="Close",        # name of the value column (y-axis)
             namecol="name",      # one time series per value of this column
             groupcol="g",        # optional: sub-groups plotted by plot_by_group
             alpha=0.01)          # significance level; a Bonferroni correction
                                  # is applied when several breakpoints are tested

# If the time column holds dates, it is converted automatically when the
# format can be inferred; otherwise call C.parse_timecol(date_format="%Y-%m-%d").

C.run(initial_breakpoint=None)   # None: midpoint of the time column
C.save_to_file("results.xlsx")   # or .csv

C.plot(filename="example/fig/stocks.png",   # all series in one figure
       xlabel="time", ylabel="value",
       figsize=(16, 8), sharey=True)
C.plot_individually(savingpath="example/fig", fmt="png",   # one file per series
                    xlabel="time", ylabel="value")
C.plot_by_group(savingpath="example/fig", fmt="png",       # one file per series, by group
                xlabel="time", ylabel="value",
                plot_overall=True,          # overall trend across groups
                plot_individual_fill=True)  # confidence interval of each group
```

## Bayesian classification and censored data (optional)

`chowclassifier.bayes.BayesChow` classifies a series into the same 14 categories with a Bayesian
model instead of F-tests. It is an optional feature: the Chow test does not need it, and its
dependencies (PyMC, and optionally nutpie or JAX) are only installed on request:

```
pip install chowclassifier[bayes]     # PyMC
pip install chowclassifier[nutpie]    # PyMC + nutpie sampler (faster)
pip install chowclassifier[jax]       # PyMC + NumPyro/JAX sampler (CPU or GPU)
```

**Censored data.** Environmental and analytical series often contain values below a detection or
quantification limit. `BayesChow` takes a boolean column (`censcol`) that marks these rows (the
value is then the limit, and the true value lies below it). They enter the likelihood through the
normal cumulative distribution function (Tobit model), instead of being dropped, set to half the
limit, or treated as measured values, which biases slopes when limits change over time.

**Model.** The series is fitted either with a single line or with one breakpoint, with the
breakpoint a discrete parameter over the candidate times (the same search as `Chow`, controlled
by `margin`), marginalised in the model. Both lines share their parameters (slope `b` before the
break and `b + delta` after it; continuous at the break by default, or with a jump in level as in
the Chow test with `continuous=False`), so that the sampler can move between "break" and
"no break". The output gives

* `p_break`: posterior probability of a breakpoint, and `breakpoint`, the most probable one
  (a break is retained when `p_break >= break_threshold`, default 0.95);
* `treeclass`: the most probable category, and `class_probabilities` for all 14;
* the slopes before and after the break with 95 % credible intervals.

A trend is "N" when its slope lies within a region of practical equivalence `[-rope, rope]`, so
the absence of a trend can be supported by the data, and the probabilities do not grow
overconfident just because a series has many points (as happens when a fitted trend is
bootstrapped into pseudo-observations and tested). With `log_y=True` the model is fitted to
log(y) and `rope` is a relative change per time unit (e.g. 0.01 = 1 % per year).

```python
from chowclassifier.bayes import BayesChow
bc = BayesChow(df, timecol="year", ycol="conc", censcol="below_limit",
               log_y=True, rope=0.01, margin=None, sampler="nutpie")
bc.run()
print(bc.summary())                 # e.g. "PFOS, Seine: class dD (P = 0.93), P(break) = 0.99 at 2016"
bc.class_probabilities              # probability of each category
bc.plot(ylabel="ng/L")              # open triangles: values below the limit
```

`ChewData` runs it on every group with `method="bayes"`:

```python
C = ChewData(df=df, namecol="site", timecol="year", ycol="conc", method="bayes",
             censcol="below_limit", bayes_kwargs=dict(log_y=True, rope=0.01, sampler="nutpie"))
C.run()
C.results_df()
```

Each series is sampled separately (tens of seconds for a few hundred points, minutes for
tens of thousands of censored points).

## References

[^1]: Chow, Gregory C. ‘Test of Equality Between Sets of Coefficients in Two Linear Regressions’. Econometrica 28, no. 3 (1960): 591–605. [jstor.org/stable/1910133](https://www.jstor.org/stable/1910133).

[^2]: Fisher, Franklin M. ‘Tests of Equality Between Sets of Coefficients in Two Linear Regressions: An Expository Note’. Econometrica2 38, no. 2 (1970): 361–66. [jstor.org/stable/1913018](https://www.jstor.org/stable/1913018).

[^3]: *Chow test* entry on Wikipedia: https://en.wikipedia.org/wiki/Chow_test

## Version changes

2.0.0 Added the optional Bayesian classification `BayesChow` (`pip install chowclassifier[bayes]`), with support for censored data (values below a limit), and `ChewData(method='bayes')`.

1.1.1 Fixed empty unused plots, added breakpoint-margin constraints, added test example, added CI.
1.0.10 Minor addition, with show_legend option
1.0.9 Correction of bugs, added jupyter notebook example.
1.0.8 Correction of bugs.
1.0.7 Split main classes and utilities in multiple files, added option to ChewData.plot to have grouped trends, corrected input parsing, corrected inconsistancy with intial_breakpoint/margin
 Added option to change linestyle by trend individually
1.0.5 Added option to plot confidence interval fill for individual group trends
1.0.4 Added support for plotting individual trends by group
1.0.3 Bug correction
1.0.2 Added support to parse full csv/excel automatically
1.0.1 First implementation of algorithm
