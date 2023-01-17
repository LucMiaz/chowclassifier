# ChowClassifier

## Description
There are many application where it is useful to analyse rapidly a large number of time-series for overall trends and possible breakpoint at which the trend changes. For example, spotting increasing trends in potential contaminants concentration from the outputs of non-target screening from high resolution mass spectrometry.

ChowClassifier aims to solve this. It is a script that performs a series of Chow tests on a time-indexed dataset to determine if a breakpoint in the time trends is probable. Two classes `Chow` and `ChewData` enable to perform the tests, generate plots and export the results in `csv` and `excel`. Dataset with groups can be ran simultaneously with `ChewData` indicating with `namecol` the name of the grouping column. Calling `run` on a `ChewData` instance will create an instance of `Chow` for each group and classify them into the following categories.

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


![Schema of Chow classification](img/Categorisation_TT.png)


## Chow test
Chow test was first derived by Gregory Chow[^1] in 1960 and later by Franklin Fisher[^2]. We test the significance of the breakpoint under the null hypothesis $Z=\frac{S_c-(S_1+S_2)}{S_1+S_2}\cdot\frac{N_1+N_2-2\cdot k}{k}$  where $k=3$ is the total number of parameters. This follows a F-distribution with $3$ and $N_1+N_2-6$ degrees of freedom, where $S_C$ is the sum of squared residuals of the regression on the full time series, $S_1$, $S_2$ are the sums of squared residuals of the regression on the first, and respectively, the second half of the time series and $N_1$, $N_2$ are the number of observation for each half. See also [^3].

## Installation
```
pip install chowclassifier
```

## Use
The script can be ran on any file with `python -m chowclassifier -f path/to/file/filename.csv -X xcol -y ycol -n grouping_name` or it can be imported:

```python:example/example.py

```

## References

[^1]: Chow, Gregory C. ‘Test of Equality Between Sets of Coefficients in Two Linear Regressions’. Econometrica 28, no. 3 (1960): 591–605. [jstor.org/stable/1910133](https://www.jstor.org/stable/1910133).

[^2]: Fisher, Franklin M. ‘Tests of Equality Between Sets of Coefficients in Two Linear Regressions: An Expository Note’. Econometrica2 38, no. 2 (1970): 361–66. [jstor.org/stable/1913018](https://www.jstor.org/stable/1913018).

[^3]: https://en.wikipedia.org/wiki/Chow_test