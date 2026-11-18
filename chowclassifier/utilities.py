"""Utility functions and constants for the chowclassifier package."""

from typing import Union
from datetime import datetime
import pandas as pd
from matplotlib import colormaps

TREND_COLORS = ["#4d4c49", "#d85e5e", "#3a668c", "#000000"]  # constant, increasing, decreasing
CI_COLORS = ["#fef5da", "#ff988c", "#b4c5f4", "#474747"]
SCATTERPARAMS = {"marker": 'o', "linewidths":0.5, "alpha":1,"s":50,"label":'_nolegend_'}
FILLPARAMS = {"linestyle":"None", "alpha":0.3,"label":'_nolegend_'}
FITPARAMS = {"label":'_nolegend_'}

def parse_cmap(cmap):
    """
    Parse and normalize colormap to dictionary format.
    
    Converts string colormap names, lists, or dictionaries to a standardized
    dictionary format with integer keys.
    
    :param cmap: Colormap as string name, list of colors, or dictionary
    :return: Dictionary mapping integers to color values
    """
    if isinstance(cmap,str):
        cmap = dict(enumerate(colormaps[cmap].colors))
    elif isinstance(cmap,list):
        cmap = dict(enumerate(cmap))
    elif isinstance(cmap, dict):
        if not all(isinstance(item, int) for item in cmap.keys()):
            cmap.update({i:v for i,(k,v) in enumerate(cmap.items())})
    else:
        cmap = dict(enumerate(colormaps['Set1'].colors))
    return cmap

def conf_int_to_trend(ci:Union[pd.DataFrame,list], param:str='X'):
    """
    Convert confidence interval to trend classification.
    
    Returns trend code 0, 1, or 2 from the confidence interval:

    - if ci crosses 0, then returns 0 (non-significant)
    - if ci is completely below 0, then returns 2 (decreasing)
    - else returns 1 (increasing)
    
    :param ci: Confidence interval to process, either a tuple (length 2), 
               a DataFrame, or result from conf_int given by statsmodels
    :param param: Column name to use if a DataFrame was given as ci
    :return: Integer trend code (0, 1, or 2)
    """
    if isinstance(ci, (list, tuple)) and len(ci)==2:
        l,u = ci
    else:
        l,u=ci.loc[param,:]
    if u<0:
        return 2 # significantly decreasing (at tested level)
    if l>0:
        return 1 # significantly increasing (at tested level)
    return 0 # non significant (at tested level)

def infer_date_format(s_date:str):
    """
    Infer date format from a sample date string.

    :param s_date: Sample date string to infer format from
    :return: Date format string if successfully inferred, None otherwise
    """
    date_patterns = ["%d-%m-%Y","%d-%m-%Y %H:%M:%S",
                     "%Y-%m-%d","%Y-%m-%d %H:%M:%S",
                     "%y-%m-%d","%y-%m-%d %H:%M:%S",
                     "%d %b %y","%d %b %y %H:%M:%S",
                     "%d %b %Y","%d %b %Y %H:%M:%S",
                     ]

    for pattern in date_patterns:
        try:
            datetime.strptime(s_date, pattern).date()
        except ValueError:
            pass
        else:
            return pattern
    return None

def guess_timelapse_type(series:Union[list,pd.DataFrame,pd.Series], date_format:str = "%Y-%m-%d"):
    """
    Guess the time lapse unit in a time series and re-index it.

    Finds the coarsest unit in which every date is a whole number of units
    after the first one: years (same day of the year), days, hours, minutes
    or seconds.

    :param series: Time series data (list, DataFrame, or Series)
    :param date_format: Format string for parsing datetime values
    :return: Tuple of (list of integer offsets from the first date, datetype string)
    """
    try:
        series = pd.to_datetime(series, format = date_format)
    except (ValueError, TypeError):
        pass
    dates = pd.Series(pd.to_datetime(series))
    start = dates.min()
    # Years are checked on the calendar, not with days % 365, which failed
    # as soon as the span included more than one leap year.
    if (dates.dt.month == start.month).all() and (dates.dt.day == start.day).all() \
            and (dates.dt.time == start.time()).all():
        return [int(d.year - start.year) for d in dates], 'year'
    seconds = (dates - start).dt.total_seconds()
    # Largest unit first. (The previous nesting could never return 'hour' or
    # 'minute', and used Timedelta.hours/.minutes, which do not exist.)
    for unit, length in (('day', 86400), ('hour', 3600), ('minute', 60)):
        if (seconds % length == 0).all():
            return [int(x // length) for x in seconds], unit
    return [int(x) for x in seconds], 'second'
