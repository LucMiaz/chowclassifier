"""Implementation of a Chow Classifier"""

import numpy as np
import pandas as pd
from scipy.stats import f as Fdist
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
from typing import Union
from datetime import datetime
import os

### Set plot style
from matplotlib import rc
sns.set_style('white')
plt.rcParams.update({'font.family':'serif',
                     'font.serif':'EB Garamond',
                     'font.size':14,
                     "xtick.bottom" : True,
                     "ytick.left" : True})

TREND_COLORS = ['#7570b3','#d95f02','#1b9e77']# constant, increasing,decreasing 
CI_COLORS = ['#aeabd3','#fd7d1c','#25daa4']
SCATTERPARAMS = {"marker": 'x', "linewidths":0.5, "alpha":1,"s":1}
FILLPARAMS = {"linestyle":'dashed', "alpha":0.1}
FITPARAMS = {"label":"OLS"}

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

class Chow(object):
    """
    Class handling the chow analysis
    Call `run()` to run the analysis (find breakpoint and classify)
    Call afterwards `params()` to get the regressions (y=k * x + b) parameters as
    [[model1_k, model1_b, model1_Rsquared],[model2_k, model2_b, model2_Rsquared]]
    (if the breakpoint is not significant, model1 = model2)

    :params df: data on which to perform the Chow categorisation
    :params name: name of the dataset (optional)
    :params breakpoint: breakpoint (if None, midpoint of X series will be used)
    :params timecol: name of time column (X)
    :params ycol: name of the variable column (Y)
    :params margin: range of indexes around breakpoint (or midpoint) where the best breakpoint
                    will be searched. E.g. if X = [0,1,1.5,2,3,4,5], breakpoint = 2 and margin = 1,
                    the set of breakpoints [1.5,2,3] will be tested.
                    (set = 0 if you want to look only at the given breakpoint or the midpoint)
    """
    def __init__(self, df,
                name:str = "",
                breakpoint:float = None,
                timecol:str = 'year',
                ycol:str = 'value',
                margin:int = 5):
        """
        
        """
        self.df = df.loc[:,[timecol,ycol]]
        self.name = name
        self.df.columns = ('X','y')
        self.df['X'] = pd.to_numeric(self.df['X'])
        self.df['y'] = pd.to_numeric(self.df['y'])
        self.breakpoint = breakpoint
        self.normalise=False
        self.F=None
        self.alpha=None
        self.model0=None
        self.model1=None
        self.model2=None
        self.margin=margin
        self.successful=None
        self.color = "#000000"
    def get_breakpoint_indices(self):
        """sets the breakpoints"""
        breakpoint_indices = range(0,len(self.df['X']))
        self.breakpoints = sorted(set(self.df['X']))
        if self.breakpoint is None:
            self.breakpoint = self.breakpoints[int(len(self.breakpoints)/2)]
        if self.breakpoint not in self.df['X']:
            self.breakpoint = self.breakpoint + min([abs(x-self.breakpoint) for x in self.df['X']])
        breakpoint_index = self.breakpoints.index(self.breakpoint)
        breakpoint_indices = range(max(4, breakpoint_index - self.margin),min(len(self.breakpoints)-4, breakpoint_index+self.margin))
        return breakpoint_indices
    def find_best_bkp(self, breakpoint_indices=None,**kwargs):
        """
           finds best breakpoint and run Chow test and find OLS params for either whole set,
           and the two subset broken at best breakpoint
        """
        if breakpoint_indices:
            if not isinstance(breakpoint_indices, list):
                breakpoint_indices=[breakpoint_indices]
            midpoint_index = int(np.median(breakpoint_indices))
        else:
            breakpoint_indices = self.get_breakpoint_indices()
            midpoint_index = breakpoint_indices[int(len(breakpoint_indices)/2)]
        results = {}
        for bk in breakpoint_indices:
            results[bk]=self.run_chow(breakpoint=self.breakpoints[bk])
        self.results=pd.DataFrame(results)
        self.results = self.results.transpose()
        self.results['delay'] = np.abs(midpoint_index - self.results.index)
        self.results = self.results.sort_values('score')
        #find best breakpoint
        self.breakpoint = self.breakpoints[self.results.score.idxmin()]
        self.run_chow(breakpoint = self.breakpoint, normalise = kwargs.get('normalise',False))
    def run_chow(self, breakpoint, normalise = False):
        """Run chow test at breakpoint"""
        if self.normalise:
            self.df['y']=(self.df['y']-self.df['y'].mean())/self.df['y'].std()
        X=self.df.loc[:,'X']
        y=self.df.loc[:,'y']
        X1=self.df.loc[self.df['X']<breakpoint,'X']
        X2=self.df.loc[self.df['X']>=breakpoint,'X']
        y1=self.df.loc[self.df['X']<breakpoint,'y']
        y2=self.df.loc[self.df['X']>=breakpoint,'y']
        if np.any(X1) and np.any(X2):
            X1=sm.add_constant(X1)
            X2=sm.add_constant(X2)
            X=sm.add_constant(X)
            self.model0=sm.OLS(y,X).fit()
            self.model1=sm.OLS(y1,X1).fit()
            self.model2=sm.OLS(y2,X2).fit()
            self.ss_res_0=np.sum((y-self.model0.predict(X))**2)
            self.ss_res_1=np.sum((y1-self.model1.predict(X1))**2)
            self.ss_res_2=np.sum((y2-self.model2.predict(X2))**2)
            self.F=((self.ss_res_0-(self.ss_res_1+self.ss_res_2))/3) / ((self.ss_res_1+self.ss_res_2)/(X.shape[0]-2*3))
            self.score=Fdist.sf(self.F, 3, X.shape[0]-2*3)
            self.successful=True
        else:
            raise ValueError("Data missing for at least one period for {}, with breakpoint {}".format(self.name,self.breakpoint))
        return {"score" : self.score,
                "F" : self.F,
                "ss_res_0" : self.ss_res_0,
                "ss_res_1" : self.ss_res_1,
                "ss_res_2" : self.ss_res_2,}
    def classify(self,alpha=0.01,**kwargs):
        """
        classify in the dataset based on results of Chow test at significance level alpha
        Possible values are:
        No significant breakpoint and:

        1. N: non-significant overall trend
        2. I: significant increasing overall trend
        3. D: significant decreasing overall trend

        Significant breakpoint (set1 and set2 indicate points before, respectively after, breakpoint) and:

        4. NN: non-significant trend on set1 and non-significant trend on set2
        5. NI: non-significant trend on set1 and significant increasing trend on set2
        6. ND: non-significant trend on set1 ans significant decreasing trend on set2
        7. IN: significant increasing trend on set1 and non-significant trend on set2
        8. ID: significant increasing trend on set1 and significant decreasing trend on set2
        9. iI: significant increasing trend on both set1 and set2 with greater increase in set2
        10. Ii: significant increasing trend on both set1 and set2 with greater increase in set1
        11. DN: significant decreasing trend on set1 and non-significant trend on set2
        12. DI: significant decreasing trend on set1 and significant increasing trend on set2
        13. dD: significant decreasing trend on both set1 and set2 with greater decrease in set2
        14. Dd: significant decreasing trend on both set1 and set2 with greater decrease in set1 
        """
        self.alpha = alpha
        if self.score < alpha:
            tt1= conf_int_to_trend(self.model1.conf_int(alpha))
            tt2= conf_int_to_trend(self.model2.conf_int(alpha))
            # correction for insignificant trend on one period when actually
            # the trend is significantly higher or lower than the next/previous period
            # at the breakpoint year (i.e. confidence intervals are disjoints at that point)
            if (tt1==0 or tt2==0) and self.breakpoint:
                lci1, uci1 = self.model1.conf_int().loc['X',:]
                lci2, uci2 = self.model2.conf_int().loc['X',:]
                b1, a1 = self.model1.params
                b2, a2 = self.model2.params
                right_limit = b1 + self.breakpoint * a1  #right limit of first period
                left_limit = b2 + self.breakpoint * a2#left limit of second period
                if right_limit >= left_limit:
                    if b2 + lci2 * self.breakpoint > b1 + uci1 * self.breakpoint:
                        if tt1==0:
                            tt1==1 # the trend is in fact increasing
                        if tt2==0:
                            tt2==2 # the trend is in fact decreasing
                else:
                    if b2 + uci2 * self.breakpoint < b1 + lci1 * self.breakpoint:
                        if tt1==0:
                            tt1==2 # the trend is in fact decreasing
                        if tt2==0:
                            tt2==1 # the trend is in fact increasing
            if tt1==0:
                tc=['NN','NI','ND'][tt2]
            elif tt1==1:
                if tt2==1:
                    tc = ['iI','Ii'][1*(self.model1.params['X']>self.model2.params['X'])]
                else:
                    tc=['IN','','ID'][tt2]
            elif tt1==2:
                if tt2==2:
                    tc = ['dD','Dd'][1*(self.model1.params['X']<self.model2.params['X'])]
                else:
                    tc=['DN','DI'][tt2]
        else:
            #N0, N1 or N2
            tt= conf_int_to_trend(self.model0.conf_int(alpha))
            tc = ['N','I','D'][tt]
            self.breakpoint=None
        self.treeclass = tc
        self.set_color()
        return self.params(alpha)
    def set_color(self):
        colors = {'Ii':'#8c510a','iI':'#bf812d','IN':'#dfc27d','NI':'#f6e8c3',
        'Dd':'#c7eae5','dD':'#80cdc1','DN':'#35978f','ND':'#01665e',
        'NN':'#555555','NI':'#006837','ND':'#d73027','N':'#AAAAAA','I':'#1a9850','D':'#a50026',
        'ID':'#9970ab','DI':'#762a83'}
        self.color = colors[self.treeclass]
    def params(self, alpha=None):
        """Returns parameters of model"""
        if alpha is None:
            alpha = self.alpha
        def get_params(model):
            d = [*[i for i in model.params],\
                model.rsquared,\
                *[i for i in model.conf_int(alpha).loc['X',:]],\
                *[i for i in model.conf_int(alpha).loc['const',:]]]
            return {k:v for v,k in zip(d,['b','a','R','a_ci_lower','a_ci_upper','b_ci_lower','b_ci_upper'])}
        if self.score < alpha:
            return {f'model0':{},
                    f'model1':get_params(self.model1),
                    f'model2':get_params(self.model2)}
        else:
            return {'model0':get_params(self.model0),
                    'model1':{},
                    'model2':{}}    
    def run(self, **kwargs):
        """Run the chow classification. parameters will be forwarded to run and classify,
        e.g. breakpoint can be passed to run, and alpha to classify"""
        if np.any(self.df):
            self.find_best_bkp(**kwargs)
            self.classify(**kwargs)
            return self.treeclass
        else:
            self.successful=False
            return None
    def summary(self, alpha = 0.01):
        """Print the summary of the model(s)"""
        if self.score < alpha:
            print(f"Summary model 1: start-{self.breakpoint}")
            self.model1.summary()
            print(f"Summary model 2: {self.breakpoint}-end")
            self.model2.summary()
        else:
            print(f"Summary model 0: whole dataset")
            self.model0.summary()
    def plot(self, color = None, filename:str = None, ax = None, figsize = (16,8),
            ylabel:str = '', xlabel:str = '', title:str = '', ylog:bool=False,
            scatterparams = None,
            fillparams = None,
            fitparams = None):
        """
        Plot the regression model(s)

        :params color: give color for the points (default defined in TREND_COLORS)
        :params filename: filename (with extension format), if None, will call plt.show() instead
        :params ax: ax on which to plot, if None will create new figure
        :params figsize: tuple with figure size
        :params ylabel: label for y-axis
        :params xlabel: label for x-axis
        :params title: title of the plot/subplot
        :params ylog: make the y-axis log-scale
        :params scatterparams: parameters for the scatter plot
        :params fillparams: parameter for the confidence intervals
        :params fitparams: parameter for the fitted line
        """
        ### update plot parameters
        if scatterparams is None:
            scatterparams = {}
        if fitparams is None:
            fitparams = {}
        if fillparams is None:
            fillparams = {}
        SCATTERPARAMS.update(scatterparams)
        FILLPARAMS.update(fillparams)
        FITPARAMS.update(fitparams)
        # record if it is plotting for parent process
        main_p = ax is None
        # create the plot:
        self.set_color()
        def add_reg_plot(sub_df, model):
            ci_l,ci_u = zip(*model.get_prediction().conf_int())
            tt = conf_int_to_trend(model.conf_int(self.alpha))
            FILLPARAMS['color'] = fillparams.get('color',CI_COLORS[tt])
            FITPARAMS['color'] = fitparams.get('color',TREND_COLORS[tt])
            ax.fill_between(sub_df['X'], y1=ci_l, y2 = ci_u, **FILLPARAMS)
            ax.plot(sub_df['X'], model.fittedvalues, marker = None,**FITPARAMS)
        if ax is None:
            f, (ax) = plt.subplots(nrows=1, ncols=1, figsize=figsize)
        if self.score < self.alpha:
            df1 = self.df.loc[self.df['X']<self.breakpoint,]
            df2 = self.df.loc[self.df['X']>=self.breakpoint,]
            add_reg_plot(df1,self.model1)
            add_reg_plot(df2,self.model2)
        else:
            add_reg_plot(self.df,self.model0)
        SCATTERPARAMS['color'] = scatterparams.get('color',self.color)
        ax.scatter(self.df['X'],self.df['y'],
                    **SCATTERPARAMS)
        # Tweak the visual presentation
        ax.xaxis.grid(True)
        ax.yaxis.grid(True)
        ax.minorticks_on()
        ax.set(ylabel=ylabel,
            xlabel=xlabel,
            title=title)
        if ylog is True:
            ax.set_yscale('log')
        #sns.despine(trim=True, left=True)
        #f.suptitle("")
        if filename is not None and main_p is True:
            plt.savefig(f'{filename}')
        elif main_p is True:
            plt.show()

class ChewData():
    """
    Handle a full data frame with grouping of time series
    
    :params df: dataset (as a pandas DataFrame) or
    :params filename: path to dataframe (used if df not given)
    :params namecol: name of the column with group names (used in groupby)
    :params initial_breakpoint: initial breakpoint
    :params sep: separator in csv
    :params timecol: name of the time column in dataset
    :params ycol: name of the variable column in dataset
    :params margin: range of indexes around breakpoint/midpoint, see Chow.get_breakpoints
    :params alpha: significance level at which to test the trends
    """
    def __init__(self, 
                df:pd.DataFrame = None, 
                filename:str = None,
                namecol:str = 'name',
                initial_breakpoint:float = None,
                sep=',',
                timecol:str = 'year',
                ycol:str = 'area',
                margin:int = 5,
                alpha:float = 0.01):
        """
        
        """
        # get dataframe
        
        self.df = df
        self.namecol = namecol
        self.timecol = timecol
        self.ycol = ycol
        self.margin = margin
        self.alpha = alpha
        self.initial_breakpoint = initial_breakpoint
        if self.df is None:
            self.get_df(filename, sep)
        if self.namecol not in self.df.columns and\
            len([k for k in self.df.columns if k not in ['id',ycol,timecol,'',np.nan]])>0:
            #inferred that df is in wide format
            try:
                self.melt()
            except ValueError as e:
                raise ValueError("Could not melt the dataframe. Is it really in wide format? Check given namecol")
        if pd.api.types.is_numeric_dtype(self.df[self.timecol]) is False:
            date_format = infer_date_format(self.df[self.timecol][0])
            print(f'Inferred format {date_format} for column {self.timecol}')
            self.parse_timecol(date_format)
    def melt(self):
        """pivot the dataframe from wide to long"""
        self.df = self.df.melt(id_vars=[self.timecol], value_name=self.ycol).dropna()
        self.namecol = 'variable'
    def get_df(self, filename, sep):
        """get dataframe from file"""
        ext = filename.split('.')[-1]
        if ext == 'xlsx' or ext == 'xls':
            self.df = pd.read_excel(filename)
        elif ext == 'csv':
            self.df = pd.read_csv(filename,sep = sep)
        elif ext == 'tsv':
            self.df = pd.read_csv(filename, sep='\t')
        else:
            raise ValueError(f"Filename {filename} does not have a recognised extension")
    def parse_timecol(self, date_format:str = '%Y-%m-%d'):
        """
        Timecol must be numeric, if you have dates instead, use this method to transform
        that column. (you need to adjust the breakpoint accordingly!)

        :params format: give the date format (default yyyy-mm-dd)
        """
        series,self.datetype = guess_timelapse_type(self.df[self.timecol], date_format = date_format)
        self.df[self.datetype] = series
        self.timecol = self.datetype
        print(f'Indexed the time column {self.timecol} as {self.datetype}s')
    def run(self, breakpoint = None):
        """
        Run the classification for each group
        
        :params breakpoint: initial break point for Chow test (if None, will take midpoint of timecol)
        """
        results = []
        self.chows = []
        if breakpoint is None:
            breakpoint = self.initial_breakpoint
        for name, sub_df in self.df.groupby(self.namecol):
            C = Chow(df = sub_df,
                     name = name,
                     breakpoint = breakpoint,
                     timecol = self.timecol,
                     ycol = self.ycol,
                     margin = self.margin)
            C.run(alpha = self.alpha) # do the classification at significance level alpha
            params = C.params(alpha = self.alpha) # get the regressions parameters
            params['name'] =  name
            results.append(params)
            self.chows.append(C)
        self.results = pd.DataFrame(results) # put the results in a dataframe
    def plot(self,filename:str, title:str = '',
             nrows:Union[None,int] = None, ncols:Union[None,int] = None, **params):
        """
        Plot all trends in one image
        
        :params filename: name of the output with extension (e.g name.pdf)
        :params title: title printed on the output
        :params ncols: number of columns
        :params nrows: number of rows
        :params params: named parameters passed to matplotlib, eg xlabel, ylabel, sharey, figsize
        """
        def get_n(m):
            n = len(self.chows)/m
            if n-int(n) == 0.:
                return int(n)
            return int(n)+1
        if nrows is None and ncols is None:
            ncols = 4
            nrows = get_n(ncols)
        elif nrows is not None:
            ncols = get_n(nrows)
        else:
            nrows = get_n(ncols)
        f, axes = plt.subplots(nrows=nrows,
                               ncols=ncols,
                               sharey=params.get("sharey",True),
                               figsize=params.get('figsize',(16,8)))
        f.tight_layout(pad=2.0) # increase padding between sub figures
        for C,ax in zip(self.chows,axes.reshape(-1)):
            C.plot(ax=ax,
                   xlabel=params.get('xlabel','X'),
                   ylabel=params.get('ylabel','y'),
                   title=C.name)
        plt.savefig(f'{filename}')
    def plot_individually(self, savingpath:str = 'figs', format:str = 'pdf', **params):
        """
        Plot all trends in individual files
        
        :params savingpath: path where the plots will be saved
        :params format: format of the image
        :params params: named parameters passed to matplotlib, eg. xlabel, ylabel, sharey, figsize
        """
        # check if saving path exists:
        if not os.path.isdir(savingpath):
            os.makedirs(savingpath)
        for C in self.chows:
            C.plot(filename = f'{"/".join([savingpath,C.name])}.{format}', **params)
    def results_df(self):
        """Create dataframe with results"""
        d = {'name': [],
             'breakpoint': [],
             'model0': {},
             'model1': {},
             'model2': {}
             }
        for c in self.chows:
            params = c.params()
            d['name'].append(c.name)
            d['breakpoint'].append(c.breakpoint)
            for k,v in params.items():
                for k1,v1 in v.items():
                    d[k].setdefault(k1,[]).append(v1)
        data, cols = [],[]
        for k, v in d.items():
            if not isinstance(v, dict):
                cols.append((k, ''))
                data.append(v)
            else:
                for k2, v2 in v.items():
                    cols.append((k, k2))
                    data.append(v2)
        df = pd.DataFrame(list(zip(*data)), columns=pd.MultiIndex.from_tuples(cols))
        return df
    def to_excel(self, filename:str, **kwargs):
        """
        Export results to excel

        :params filename: filename
        """
        df = self.results_df()
        with pd.ExcelWriter(filename) as writer:
            df.to_excel(writer, sheet_name = 'results')
            self.df.to_excel(writer, sheet_name = 'data')
    def to_csv(self, filename:str, **kwargs):
        """
        Export results to csv

        :params filename: filename
        """

        df = self.results_df()
        df.to_csv(filename, **kwargs)
    def save_to_file(self, filename:str, **kwargs):
        """
        Export results to excel or csv

        :params filename: filename
        :params kwargs: other parameters passed to pd.DataFrame.to_csv
        """

        ext = filename.split('.')[-1]
        if ext in ['xlsx','xls']:
            self.to_excel(filename)
        elif ext == 'csv':
            self.to_csv(filename,**kwargs)
        else:
            raise ValueError(f'filename {filename} does not have a supported extension. Should be .csv, .xlsx or .xls.')


