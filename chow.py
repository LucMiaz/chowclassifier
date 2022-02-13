"""Implementation of a Chow Classifier"""
from decimal import Decimal
import numpy as np
import pandas as pd
from scipy.stats import f
import matplotlib.pyplot as plt
import statsmodels.api as sm

def confintToTrend(ci,param='X'):
    """return trend  0, 1, 2 from the confidence interval:
    if ci crosses 0, then returns 0
    if ci is completely below 0, then returns 2
    else returns 1
    either ci is a tuple of length 2
    else ci is a conf_int from statsmodels"""
    if isinstance(ci, list) and len(ci)==2:
        l,u = ci
    else:
        l,u=ci.loc[param,:]
    if u<0:
        return 2
    elif l>0:
        return 1
    else:
        return 0

# a random noise generator
class noise_gen:
    def __init__(self, mu = 0, sigma = 1, seed = None):
        import random as rd
        import numpy as np
        if seed and isinstance(seed, int):
            np.random.seed(seed)
            self.seed = seed
        elif seed:
            print("Seed %s not of type integer, setting seed as 1990" % str(seed))
            seed = 1990
            rd.seed(1990)
        self.seed = seed
        self.mu = mu
        self.sigma = sigma
        self.n = 0
    def __next__(self, k = None):
        if k and isinstance(k, int):
            k = k
        else:
            k = 1
        self.n+=k
        return np.random.normal(self.mu, self.sigma, k)
    def __iter__(self):
        return self

import string

def labels(alphabet=string.ascii_uppercase):
    assert len(alphabet) == len(set(alphabet))  # make sure every letter is unique
    s = [alphabet[0]]
    while 1:
        yield ''.join(s)
        l = len(s)
        for i in range(l-1, -1, -1):
            if s[i] != alphabet[-1]:
                s[i] = alphabet[alphabet.index(s[i])+1]
                s[i+1:] = [alphabet[0]] * (l-i-1)
                break
        else:
            s = [alphabet[0]] * (l+1)


class count():
    def __init__(self):
        self.n = -1
    def __next__(self):
        self.n += 1
        return self.n
    def __iter__(self):
        return self

class syntdf():
    def __init__(self, columns = ['id','year','area'], numeric_cols=['area','year']):
        self.columns = columns
        self.counter = count()
        self.df = pd.DataFrame(columns=self.columns)
        for numcol in numeric_cols:
            self.df[numcol] = pd.to_numeric(self.df[numcol])
    def add(self, *args,**kwargs):
        for i, v in enumerate(args):
            kwargs[self.columns[i]]=v
        i = next(self.counter)
        for k in set(kwargs.keys()).intersection(self.columns):
            self.df.at[i, k] = kwargs[k]


class chow(object):
    def __init__(self, df,
                breakpoint = 2010,
                timecol = 'year',
                ycol = 'area',
                margin = 5):
        self.df = df.loc[:,[timecol,ycol]]
        self.df.columns = ('X','y')
        self.df['X'] = pd.to_numeric(self.df['X'], downcast='integer')
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
    def run(self, breakpoints=None):
        if breakpoints:
            if not isinstance(breakpoints, list):
                breakpoints=[breakpoints]
            midpoint = np.median(breakpoints)
        else:
            breakpoints = sorted([*set(self.df['X'])])
            midpoint = np.median(breakpoints)
            breakpoints = range(breakpoints[self.margin-1],breakpoints[-self.margin])
        results = {}
        for bk in breakpoints:
            results[bk]=self.run_bk(breakpoint=bk)
            self.results=pd.DataFrame(results)
            self.results = self.results.transpose()
            self.results['delay'] = np.abs(midpoint - self.results.index)
            self.results = self.results.sort_values('delay')
            #find best breakpoint
            self.breakpoint = self.results.score.idxmin()
        self.run_bk(breakpoint = self.breakpoint)
    def run_bk(self, breakpoint=None):
        if not breakpoint:
            breakpoint = self.breakpoint
            print("changed breakpoint to %s" % str(self.breakpoint))
        if self.normalise:
            self.df['y']=(self.df['y']-self.df['y'].mean())/self.df['y'].std()
        X=self.df.loc[:,'X']
        y=self.df.loc[:,'y']
        X1=self.df.loc[self.df['X']<self.breakpoint,'X']
        X2=self.df.loc[self.df['X']>=self.breakpoint,'X']
        y1=self.df.loc[self.df['X']<self.breakpoint,'y']
        y2=self.df.loc[self.df['X']>=self.breakpoint,'y']
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
            self.score=f.sf(self.F, 3, X.shape[0]-2*3)
            self.successful=True
        else:
            print("Data missing for at least on period for {}".format(self.df))
            self.score = 1
            self.F=0
            self.ss_res_0=0
            self.ss_res_1=0
            self.ss_res_2=0
            self.successful=False
        return {"score" : self.score,
                "F" : self.F,
                "ss_res_0" : self.ss_res_0,
                "ss_res_1" : self.ss_res_1,
                "ss_res_2" : self.ss_res_2,}
    def classify(self,alpha=0.01):
        """classify in TreeClass"""
        if self.score < alpha:
            tt1= confintToTrend(self.model1.conf_int(alpha))
            tt2= confintToTrend(self.model2.conf_int(alpha))
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
            b1,a1=self.model1.params
            b2,a2=self.model2.params
        else:
            #N0, N1 or N2
            tt= confintToTrend(self.model0.conf_int(alpha))
            tc = ['N0','N1','N2'][tt]
            b1,a1=self.model0.params
            b2,a2=self.model0.params
            self.breakpoint=None
        self.treeclass = tc
        self.set_color()
        return [[a1,b1],[a2,b2]]
    def set_color(self):
        colors = {'Ii':'#8c510a','iI':'#bf812d','IN':'#dfc27d','NI':'#f6e8c3',
        'Dd':'#c7eae5','dD':'#80cdc1','DN':'#35978f','ND':'#01665e',
        'NN':'#555555','NI':'#006837','ND':'#d73027','N0':'#AAAAAA','N1':'#1a9850','N2':'#a50026',
        'ID':'#9970ab','DI':'#762a83'}
        self.color = colors[self.treeclass]
    def params(self, alpha=0.01):
        if self.score < alpha:
            b1,a1=self.model1.params
            b2,a2=self.model2.params
        else:
            b1,a1=self.model0.params
            b2,a2=self.model0.params
        return [[a1,b1],[a2,b2]]
    def analyse(self, breakpoints=None):
        if np.any(self.df):
            self.run(breakpoints)
            self.classify()
            return self.treeclass
        else:
            self.successful=False
            return None

def KL(df,w=5):
    """computes the kullback-leibler divergence for a given dataframe
    (should have column 'year','x','y')
    will first normalise x,y to x_n,y_n then compute the pmf based
    on windows of size w (assumed to be odd) and normal distribution"""
    from scipy.stats import norm
    minyear=df.loc[:,'year'].min()+int(w/2)
    maxyear=df.loc[:,'year'].max()-int(w/2)
    meanX = np.mean(df.loc[:,'x'])
    sdX = np.std(pfosobs.loc[:,'x'])
    meanY = np.mean(df.loc[:,'y'])
    sdY = np.std(pfosobs.loc[:,'y'])
    df['x_n']=[(cc-meanX)/sdX for cc in df.loc[:,'x']]#normalise cc
    df['y_n']=[(cc-meanY)/sdY for cc in df.loc[:,'y']]
    p=pd.DataFrame(columns=['year','mX','sX'])
    q=pd.DataFrame(columns=['year','mY','sY'])
    for i in range(minyear,maxyear+1):
        msX=df.loc[(df['year']>=i-2) & (df['year']<=i+2),'x_n'].agg([np.mean,np.std])
        msY=df.loc[(df['year']>=i-2) & (df['year']<=i+2),'y_n'].agg([np.mean,np.std])
        p.loc[int(i-minyear),:]=[i,float(msX[0]),float(msX[1])]
        q.loc[int(i-minyear),:]=[i,float(msY[0]),float(msY[1])]
    df=pd.merge(df,p,on='year',how='right')
    df=pd.merge(df,q,on='year',how='right')
    kl=0
    for i in range(minyear, maxyear+1):
        kl=df.loc[df['year']==i,'x_n']