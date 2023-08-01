"""Implementation of a Chow Classifier"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Union
import os
from tqdm import tqdm
from .utilities import infer_date_format, guess_timelapse_type
from .chow import Chow


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
    :params groupcol: name of the grouping column in dataset
    :params margin: range of indexes around breakpoint/midpoint, see Chow.get_breakpoints
    :params alpha: significance level at which to test the trends (Bonferroni correction will be applied later)
    """
    def __init__(self, 
                df:pd.DataFrame = None, 
                filename:str = None,
                groupcol:Union[None,str] = 'g',
                namecol:str = 'name',
                initial_breakpoint:float = None,
                sep=',',
                timecol:str = 'year',
                ycol:str = 'value',
                margin:int = 2,
                alpha:float = 0.01):
        """
        
        """
        # get dataframe
        
        self.df = df
        self.namecol = namecol
        self.timecol = timecol
        self.groupcol = groupcol
        if ycol is None:
            self.ycol = 'value'
        else:
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
            date_format = infer_date_format(self.df.loc[self.df[self.timecol]!=np.nan,self.timecol][0])
            print(f'Inferred format {date_format} for column {self.timecol}')
            if date_format is not None:
                self.parse_timecol(date_format)
    def melt(self):
        """pivot the dataframe from wide to long"""
        if self.groupcol in self.df.columns:
            self.df = self.df.melt(id_vars=[self.timecol,self.groupcol], value_name=self.ycol).dropna()
        else:
            self.df = self.df.melt(id_vars=[self.timecol], value_name=self.ycol).dropna()
        self.namecol = 'variable'
    def get_df(self, filename, sep):
        """get dataframe from file"""
        ext = filename.split('.')[-1]
        if ext == 'xlsx' or ext == 'xls':
            self.df = pd.read_excel(filename, engine='openpyxl')
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
    def run_C(self, sub_df:pd.DataFrame, name:str, initial_breakpoint:Union[float,int])->(dict,Chow):
        """
        Run the classification on a dataframe
        
        :params sub_df: dataframe
        :params name: name of the series
        :params initial_breakpoint: initial break point for Chow test (if None, will take midpoint of timecol)
        :returns: dictionary of parameters from the analysis, Chow object from the analysis
        """
        C = Chow(df = sub_df,
                name = name,
                initial_breakpoint = initial_breakpoint,
                timecol = self.timecol,
                ycol = self.ycol,
                alpha = self.alpha,
                margin = self.margin)
        try:
            C.run()
        except ValueError:
            return None,None
        else:
            params = C.params() # get the regressions parameters
            params['name'] =  name
            return params, C
    def run(self, initial_breakpoint = None):
        """
        Run the classification for each group
        
        :params initial_breakpoint: initial break point for Chow test (if None, will take midpoint of timecol)
        """
        results = []
        self.chows = []
        self.failed = []
        if initial_breakpoint is None and self.initial_breakpoint is None:
            x = list(set(self.df[self.timecol]))
            self.initial_breakpoint = x[int(len(x)/2)]
            initial_breakpoint = self.initial_breakpoint
            print(f"Set {initial_breakpoint = }")
        elif initial_breakpoint is None:
            initial_breakpoint = self.initial_breakpoint
        print("Running analysis")
        with tqdm(total = len(self.df.groupby(self.namecol))) as bar:
            for name, sub_df in self.df.groupby(self.namecol):
                if sub_df.shape[0] > 1:
                    params,C = self.run_C(sub_df, name = name, initial_breakpoint=initial_breakpoint)
                    if C is None:
                        self.failed.append(name)
                    else:
                        results.append(params)
                        self.chows.append(C)
                else:
                    self.failed.append(name)
                bar.update(1)
        self.results = pd.DataFrame(results) # put the results in a dataframe
    def plot(self,filename:Union[str,None]=None,
             grouped:bool = False,
             divide:int = 1,
             nrows:Union[None,int] = None,
             ncols:Union[None,int] = None,
             cmap:Union[None,str] = None,
             scatterparams:dict = {},
             fillparams:dict = {},
             fitparams:dict = {},
             **params):
        """
        Plot all trends in one image
        
        :params filename: name of the output with extension (e.g name.pdf)
        :params grouped: whether to plot overall trends or grouped trends
        :params cmap: (grouped) Name of one of matplotlib cmaps
        :params plot_overall: (grouped) Plot overall trend and confidence interval
        :params plot_individual_fill: (grouped) Plot confidence interval for each individual group in addition to the overall one (if applicable)
        :params title: title printed on the output
        :params divide: divide the plots into n files
        :params ncols: number of columns
        :params nrows: number of rows
        :params scatterparams: dictionnary of parameters for the scatter part of the plot, passed to chew plot
        :params fillparams: dictionnary of parameters for the error fill area of the plot, passed to chew plot
        :params fitparams: dictionnary of parameters for the fitted line, passed to chew plot
        :params params: named parameters passed to matplotlib, eg xlabel, ylabel, sharey, figsize, pad
        """
        def get_n(m,_nplots = len(self.chows)):
                n = _nplots/m
                if n-int(n) == 0.:
                    return int(n)
                return int(n)+1
        if filename is not None:
            f = filename.split(".")
            filename = ".".join(f[0:-1])
            ext = f[-1]
        nplots = get_n(divide)
        print("Plotting trends")
        with tqdm(total = divide) as bar:
            for i in range(0,divide):
                if nrows is None and ncols is None:
                    ncols = 4
                    nrows = get_n(ncols,nplots)
                elif nrows is not None:
                    ncols = get_n(nrows,nplots)
                else:
                    nrows = get_n(ncols,nplots)
                f, axes = plt.subplots(nrows=nrows,
                                    ncols=ncols,
                                    sharey=params.get("sharey",True),
                                    figsize=params.get('figsize',(16,8)))
                f.tight_layout(pad=params.get('pad',3.0)) # increase padding between sub figures
                for chowObj, ax in zip(self.chows[i*nplots:(i+1)*nplots], axes.reshape(-1)):
                    if grouped is True and self.groupcol in chowObj.df.colnames:
                        plt.clf()
                        chowObj.plot_by_group(ax = ax,
                                              xlabel=params.get('xlabel',self.timecol),
                                              ylabel=params.get('ylabel',self.ycol),
                                              cmap = cmap, 
                                              title=chowObj.name,
                                              scatterparams = scatterparams,
                                              fillparams = fillparams,
                                              fitparams = fitparams
                                              **params)
                    else:
                        chowObj.plot(ax=ax,
                            xlabel=params.get('xlabel','X'),
                            ylabel=params.get('ylabel','y'),
                            title=chowObj.name,
                            scatterparams = scatterparams,
                            fillparams = fillparams,
                            fitparams = fitparams)
                if filename is not None:
                    plt.savefig(f'{filename}_{i:02d}.{ext}')
                bar.update(1)
        if filename is None:
            plt.show()
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
        print("Plotting trends individually")
        with tqdm(total = len(self.chows)) as bar:
            for chowObj in self.chows:
                plt.clf()
                chowObj.plot(filename = f'{"/".join([savingpath, chowObj.name])}.{format}',
                             xlabel=params.get('xlabel', self.timecol),
                             ylabel=params.get('ylabel', self.ycol),
                             title=params.get('prefix','')+chowObj.name,
                             scatterparams = params.get('scatterparams',{}),
                             fillparams = params.get('fillparams',{}),
                             fitparams = params.get('fitparams',{}))
                bar.update(1)
    def plot_by_group(self,
                      savingpath:Union[None,str] = 'figs',
                      format:str = 'pdf',
                      cmap:str = 'Set1',
                      **params):
        """
        Plot all trends in individual files
        
        :params savingpath: path where the plots will be saved
        :params format: format of the image
        :params cmap: Name of one of matplotlib cmaps
        :params show_legend: include the legend
        :params plot_overall: Plot overall trend and confidence interval
        :params plot_individual_fill:  Plot confidence interval for each individual group in addition to the overall one (if applicable)
        :params params: named parameters passed to matplotlib, eg. xlabel, ylabel, sharey, figsize, overall_label
        """
        if not os.path.isdir(savingpath):
            os.makedirs(savingpath)
        print("Plotting trends by group")
        with tqdm(total = len(self.chows)) as bar:
            for chowObj in self.chows:
                plt.clf()
                params['title'] = params.get('title', chowObj.name)
                params['xlabel'] = params.get('xlabel', self.timecol)
                params['ylabel'] = params.get('ylabel', self.ycol)
                if savingpath is not None:
                    filename = f"{savingpath}/{chowObj.name}_bygroups.{format}"
                else:
                    filename = None
                chowObj.plot_by_group(filename = filename, groupcol = self.groupcol, cmap = cmap, **params)
                bar.update(1)
        if savingpath is None:
            plt.show()

    def results_df(self):
        """Create dataframe with results"""
        d = {'name': [],
             'breakpoint': [],
             'score': [],
             'model0': [],
             'model1': [],
             'model2': []
             }
        model_params = self.chows[0].params_names()
        for c in self.chows:
            params = c.params()
            d['name'].append(c.name)
            d['breakpoint'].append(c.initial_breakpoint)
            d['score'].append(c.score)
            for k,v in params.items():
                d[k].append(v)
        data, cols = [],[]
        for k, v in d.items():
            if not isinstance(v[0], dict):
                cols.append((k, ''))
                data.append(v)
            else:
                subdata = {}
                for v1 in v:
                    for p in model_params:
                        subdata.setdefault(p,[]).append(v1.get(p,np.nan))
                for k1,v1 in subdata.items():
                    cols.append((k, k1))
                    data.append(v1)
        df = pd.DataFrame(list(zip(*data)), columns=pd.MultiIndex.from_tuples(cols))
        return df
    def to_excel(self, filename:str, **kwargs):
        """
        Export results to excel

        :params filename: filename
        """
        df = self.results_df()
        with pd.ExcelWriter(filename, **kwargs) as writer:
            df.to_excel(writer, sheet_name = 'results')
            self.df.to_excel(writer, sheet_name = 'data')
            pd.DataFrame([[x] for x in self.failed],columns=['Name']).to_excel(writer, sheet_name='failed')
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
            self.to_excel(filename, engine='openpyxl')
        elif ext == 'csv':
            self.to_csv(filename,**kwargs)
        else:
            raise ValueError(f'filename {filename} does not have a supported extension. Should be .csv, .xlsx or .xls.')


