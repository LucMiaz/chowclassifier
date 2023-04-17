import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Union
from datetime import datetime

TREND_COLORS = ['#7570b3','#d95f02','#1b9e77']# constant, increasing,decreasing 
CI_COLORS = ['#aeabd3','#fd7d1c','#25daa4']
SCATTERPARAMS = {"marker": 'x', "linewidths":0.5, "alpha":1,"s":50,"label":'_nolegend_'}
FILLPARAMS = {"linestyle":"None", "alpha":0.3,"label":'_nolegend_'}
FITPARAMS = {"label":'_nolegend_'}

def conf_int_to_trend(ci:Union[pd.DataFrame,list], param:str='X'):
    """return trend  0, 1, 2 from the confidence interval:

    - if ci crosses 0, then returns 0
    - if ci is completely below 0, then returns 2
    - else returns 1
    
    :params ci: confidence interval to process, either a tuple (length 2), a dataframe or result from conf_int given by statsmodles
    :params param: name column to use if a dataframe was given as ci
    """
    if isinstance(ci, list) and len(ci)==2:
        l,u = ci
    else:
        l,u=ci.loc[param,:]
    if u<0:
        return 2 # significantly decreasing (at tested level)
    elif l>0:
        return 1 # significantly increasing (at tested level)
    else:
        return 0 # non significant (at tested level)

def infer_date_format(s_date:str):
    """
    Infer date format from a sample

    :params s_date: sample date to infer date format from.
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
        except:
            pass
        else:
            return pattern

def guess_timelapse_type(series:Union[list,pd.DataFrame,pd.Series], date_format:str = "%Y-%m-%d"):
    """Guess the time lapse in a series and index it

    :params series: data
    :params date_format: format of the datetime
    :return: indexed series and datetype"""
    try:
        series = pd.to_datetime(series, format = date_format)
    except:
        pass
    start = min(series)
    series = series-start # reindex timecol from lowest one
    if all([i.seconds==0 for i in series]):
        #check if indexed by minutes
        if all([i.seconds%60 == 0 for i in series]):
            #check if indexed by hour
            if all([i.seconds%3600 == 0 for i in series]):
                #check if indexed by year
                if all([i.days%365==0 or i.days%366==0 for i in series]):
                    #index by year
                    series = [int(i.days/365) for i in series]
                    datetype = 'year'
                else:#index by day
                    series = [i.days for i in series]
                    datetype = 'day'
            else:#index by hour
                series = [i.days * 24 + i.hours for i in series]
                datetype = 'hour'
        else:#index by minute
            series = [i.days * 60 * 24 + i.minutes for i in series]
            datetype = 'minute'
    else:# index on the seconds:
        series = [i.days * 3600 * 24 + i.seconds for i in series]
        datetype = 'second'
    return series,datetype