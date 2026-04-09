"""Implementation of a Chow Classifier"""

import os
from typing import Union
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
from .utilities import infer_date_format, guess_timelapse_type
from .chow import Chow


class ChewData():
    """
    Handle a full data frame with grouping of time series.
    
    :param df: Dataset as a pandas DataFrame (optional if filename provided)
    :param filename: Path to dataframe file (used if df not given)
    :param namecol: Name of the column with group names (used in groupby)
    :param initial_breakpoint: Initial breakpoint value
    :param sep: Separator character in CSV files
    :param timecol: Name of the time column in dataset
    :param ycol: Name of the variable column in dataset
    :param groupcol: Name of the grouping column in dataset
    :param margin: Range of indexes around breakpoint/midpoint, 
                   see Chow.get_breakpoint_indices
    :param alpha: Significance level at which to test the trends
                  (Bonferroni correction will be applied later)
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
        Initialize a ChewData object for analyzing multiple time series.
        
        Either df or filename must be provided. The class will automatically
        detect wide vs long format and convert if necessary.
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
        self.chows = []
        self.failed = []
        self.results = None
        if self.df is None:
            self.get_df(filename, sep)
        if self.namecol not in self.df.columns and\
            len([k for k in self.df.columns if k not in ['id',ycol,timecol,'',np.nan]])>0:
            #inferred that df is in wide format
            try:
                self.melt()
            except ValueError as e:
                raise ValueError(
                    "Could not melt the dataframe. Is it really in wide format?"
                    " Check given namecol"
                ) from e
        if pd.api.types.is_numeric_dtype(self.df[self.timecol]) is False:
            date_format = infer_date_format(self.df.loc[self.df[self.timecol]!=np.nan,self.timecol][0])
            print(f'Inferred format {date_format} for column {self.timecol}')
            if date_format is not None:
                self.parse_timecol(date_format)
    def melt(self):
        """
        Pivot the dataframe from wide to long format.
        
        Converts a wide-format dataframe (with time series in columns) to
        long format (with a variable column for series names).
        """
        if self.groupcol in self.df.columns:
            self.df = self.df.melt(id_vars=[self.timecol,self.groupcol], value_name=self.ycol).dropna()
        else:
            self.df = self.df.melt(id_vars=[self.timecol], value_name=self.ycol).dropna()
        self.namecol = 'variable'
    def get_df(self, filename, sep):
        """
        Load dataframe from file.
        
        Supports Excel (.xlsx, .xls), CSV (.csv), and TSV (.tsv) formats.
        
        :param filename: Path to the file
        :param sep: Separator character for CSV files
        :raises ValueError: If file extension is not recognized
        """
        ext = filename.split('.')[-1]
        if ext in ('xlsx', 'xls'):
            self.df = pd.read_excel(filename, engine='openpyxl')
        elif ext == 'csv':
            self.df = pd.read_csv(filename,sep = sep)
        elif ext == 'tsv':
            self.df = pd.read_csv(filename, sep='\t')
        else:
            raise ValueError(f"Filename {filename} does not have a recognised extension")
    def parse_timecol(self, date_format:str = '%Y-%m-%d'):
        """
        Transform time column from dates to numeric values.
        
        The time column must be numeric for analysis. If you have dates instead,
        use this method to transform that column. Note: you need to adjust the
        breakpoint accordingly!

        :param date_format: Date format string (default '%Y-%m-%d')
        """
        series,self.datetype = guess_timelapse_type(self.df[self.timecol], date_format = date_format)
        self.df[self.datetype] = series
        self.timecol = self.datetype
        print(f'Indexed the time column {self.timecol} as {self.datetype}s')
    def run_single(self,
                   sub_df:pd.DataFrame,
                   name:str,
                   initial_breakpoint:Union[float,int])->(dict,Chow):
        """
        Run the Chow classification on a single dataframe.
        
        :param sub_df: DataFrame containing the time series data
        :param name: Name identifier for the series
        :param initial_breakpoint: Initial break point for Chow test 
                                   (if None, will take midpoint of timecol)
        :return: Tuple of (dictionary of parameters from the analysis,
                 Chow object from the analysis)
        """
        chow = Chow(df = sub_df,
                name = name,
                initial_breakpoint = initial_breakpoint,
                timecol = self.timecol,
                ycol = self.ycol,
                alpha = self.alpha,
                margin = self.margin)
        try:
            chow.run()
        except ValueError:
            return None, None
        params = chow.params() # get the regressions parameters
        params['name'] = name
        return params, chow
    def run(self, initial_breakpoint = None):
        """
        Run the Chow classification for each group in the dataset.
        
        :param initial_breakpoint: Initial break point for Chow test
                                  (if None, will take midpoint of timecol)
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
        with tqdm(total = len(self.df.groupby(self.namecol))) as pbar:
            for name, sub_df in self.df.groupby(self.namecol):
                if sub_df.shape[0] > 1:
                    params, chow = self.run_single(
                        sub_df, name=name, initial_breakpoint=initial_breakpoint
                    )
                    if chow is None:
                        self.failed.append(name)
                    else:
                        results.append(params)
                        self.chows.append(chow)
                else:
                    self.failed.append(name)
                pbar.update(1)
        self.results = pd.DataFrame(results) # put the results in a dataframe
    def plot(self, filename:Union[str,None]=None,
             grouped:bool = False,
             divide:int = 1,
             nrows:Union[None,int] = None,
             ncols:Union[None,int] = None,
             cmap:Union[None,str] = None,
             scatterparams:dict = None,
             fillparams:dict = None,
             fitparams:dict = None,
             **params):
        """
        Plot all trends in one image.
        
        :param filename: Name of the output file with extension
                         (e.g., 'name.pdf')
        :param grouped: Whether to plot overall trends or grouped trends
        :param divide: Divide the plots into n files
        :param nrows: Number of rows in subplot grid
        :param ncols: Number of columns in subplot grid
        :param cmap: (grouped) Name of one of matplotlib cmaps
        :param scatterparams: Dictionary of parameters for the scatter 
                              part of the plot
        :param fillparams: Dictionary of parameters for the error fill 
                           area of the plot
        :param fitparams: Dictionary of parameters for the fitted line
        :param params: Named parameters passed to matplotlib 
                       (e.g., xlabel, ylabel, sharey, figsize, pad,
                       plot_overall, plot_individual_fill, title)
        """
        scatterparams = scatterparams or {}
        fillparams = fillparams or {}
        fitparams = fitparams or {}
        def get_n(m, _nplots=len(self.chows)):
            n = _nplots / m
            if n - int(n) == 0.:
                return int(n)
            return int(n) + 1
        if filename is not None:
            f = filename.split(".")
            filename = ".".join(f[0:-1])
            ext = f[-1]
        nplots = get_n(divide)
        print("Plotting trends")
        with tqdm(total = divide) as pbar:
            for i in range(0, divide):
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
                for chow_obj, ax in zip(self.chows[i*nplots:(i+1)*nplots]+[None for _ in range(ncols*nrows - len(self.chows[i*nplots:(i+1)*nplots]))], axes.reshape(-1)):
                    if chow_obj is None:
                        ax.axis('off')
                        continue
                    if grouped is True and self.groupcol in chow_obj.df.colnames:
                        plt.clf()
                        chow_obj.plot_by_group(ax = ax,
                                              xlabel=params.get('xlabel',self.timecol),
                                              ylabel=params.get('ylabel',self.ycol),
                                              cmap = cmap,
                                              title=chow_obj.name,
                                              scatterparams = scatterparams,
                                              fillparams = fillparams,
                                              fitparams = fitparams,
                                              **params)
                    else:
                        chow_obj.plot(ax=ax,
                            xlabel=params.get('xlabel','X'),
                            ylabel=params.get('ylabel','y'),
                            title=chow_obj.name,
                            scatterparams = scatterparams,
                            fillparams = fillparams,
                            fitparams = fitparams)
                if filename is not None:
                    plt.savefig(f'{filename}_{i:02d}.{ext}')
                pbar.update(1)
        if filename is None:
            plt.show()
            plt.close()
    def plot_individually(self, savingpath:str = 'figs', fmt:str = 'pdf', **params):
        """
        Plot all trends in individual files.
        
        :param savingpath: Path where the plots will be saved
        :param fmt: Format of the image (e.g., 'pdf', 'png')
        :param params: Named parameters passed to matplotlib
                       (e.g., xlabel, ylabel, prefix, scatterparams,
                       fillparams, fitparams)
        """
        # check if saving path exists:
        if not os.path.isdir(savingpath):
            os.makedirs(savingpath)
        print("Plotting trends individually")
        with tqdm(total = len(self.chows)) as pbar:
            params['xlabel'] = params.get('xlabel', self.timecol)
            params['ylabel'] = params.get('ylabel', self.ycol)
            params['scatterparams'] = params.get('scatterparams', {})
            params['fillparams'] = params.get('fillparams', {})
            params['fitparams'] = params.get('fitparams', {})
            for chow_obj in self.chows:
                plt.clf()
                chow_obj.plot(
                    filename=f'{"/".join([savingpath, chow_obj.name])}.{fmt}',
                    title=params.get('prefix', '') + chow_obj.name,
                    **params)
                pbar.update(1)
                plt.close()
    def plot_by_group(self,
                      savingpath:Union[None,str] = 'figs',
                      fmt:str = 'pdf',
                      cmap:str = 'Set1',
                      **params):
        """
        Plot all trends in individual files, grouped by category.
        
        :param savingpath: Path where the plots will be saved
                           (None to show instead of save)
        :param fmt: Format of the image (e.g., 'pdf', 'png')
        :param cmap: Name of one of matplotlib cmaps
        :param params: Named parameters passed to matplotlib and plot_by_group.
                      Includes: show_legend, plot_overall, plot_individual_fill,
                      xlabel, ylabel, title, overall_label
        """
        if not os.path.isdir(savingpath):
            os.makedirs(savingpath)
        print("Plotting trends by group")
        with tqdm(total = len(self.chows)) as pbar:
            for chow_obj in self.chows:
                plt.clf()
                params['title'] = params.get('title', chow_obj.name)
                params['xlabel'] = params.get('xlabel', self.timecol)
                params['ylabel'] = params.get('ylabel', self.ycol)
                if savingpath is not None:
                    filename = f"{savingpath}/{chow_obj.name}_bygroups.{fmt}"
                else:
                    filename = None
                chow_obj.plot_by_group(
                    filename=filename, groupcol=self.groupcol, cmap=cmap, **params
                )
                pbar.update(1)
        if savingpath is None:
            plt.show()
            plt.close()

    def results_df(self):
        """
        Create dataframe with analysis results.
        
        :return: DataFrame with multi-level columns containing results
                 for all analyzed series
        """
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
        Export results to Excel file.
        
        Creates multiple sheets: 'results' (analysis results), 
        'data' (input data),
        and 'failed' (list of failed analyses).

        :param filename: Output filename with .xlsx or .xls extension
        :param kwargs: Additional keyword arguments passed to pd.ExcelWriter
        """
        df = self.results_df()
        with pd.ExcelWriter(filename, **kwargs) as writer:
            df.to_excel(writer, sheet_name = 'results')
            self.df.to_excel(writer, sheet_name = 'data')
            pd.DataFrame([[x] for x in self.failed],columns=['Name']).to_excel(writer, sheet_name='failed')
    def to_csv(self, filename:str, **kwargs):
        """
        Export results to CSV file.

        :param filename: Output filename with .csv extension
        :param kwargs: Additional keyword arguments passed to pd.DataFrame.to_csv
        """

        df = self.results_df()
        df.to_csv(filename, **kwargs)
    def save_to_file(self, filename:str, **kwargs):
        """
        Export results to Excel or CSV file based on extension.
        
        Automatically detects file format from extension and 
        calls the appropriate export method.

        :param filename: Output filename with extension (.xlsx, .xls, or .csv)
        :param kwargs: Additional keyword arguments passed to export methods
        :raises ValueError: If filename extension is not supported
        """

        ext = filename.split('.')[-1]
        if ext in ['xlsx','xls']:
            self.to_excel(filename, engine='openpyxl')
        elif ext == 'csv':
            self.to_csv(filename,**kwargs)
        else:
            raise ValueError(f'filename {filename} does not have a supported extension. Should be .csv, .xlsx or .xls.')
