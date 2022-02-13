from chow import chow
import pandas as pd
from decimal import Decimal as D
from datetime import datetime
import os
from matplotlib import pyplot as plt
plt.rcParams.update({"text.usetex": True})
def date_from_string(string):
    return datetime.strptime(string,'%Y-%m-%d')

bkpt = date_from_string('2021-10-01')
datafolder = "../../Documents/Investments/Data"
files = [f for f in os.listdir(datafolder) if f.endswith(".csv")]

stocks = []
stocks_df={}
for filename in files:
    name = filename.split(".csv")[0]
    stocks.append(name)
    dtypes = {"Volume":int,"Open":float,"High":float,"Low":float,"Close":float,"Adj Close":float}
    cvts={"Date":date_from_string} #"Open":D,"High":D,"Low":D,"Close":D,"Adj Close":D}
    dfr = pd.read_csv(datafolder+"/"+filename, dtype = dtypes,converters=cvts)
    firstday = min(dfr['Date'])
    dfr['day'] = [(row['Date']-firstday).days for i,row in dfr.iterrows()]
    stocks_df[name]={'df':dfr,"bkpt":(bkpt-firstday).days}

for stock, val in stocks_df.items():
    dfs = val.get('df')
    Ccl = chow(dfs, breakpoint = val.get("bkpt"),
           timecol = 'day',
           ycol = 'Close')
    stocks_df[stock]['chowClass']=Ccl
    treeclass = Ccl.analyse(breakpoints = [val.get("bkpt")])
    stocks_df[stock]['tc']=treeclass

stocks_df_tc = pd.DataFrame([[k,v['tc']] for k,v in stocks_df.items()], columns = ['stock','tc'])


for treeclass in set(stocks_df_tc['tc']):
    stocks_tc = stocks_df_tc.loc[stocks_df_tc['tc']==treeclass,]
    tot = len(stocks_tc)
    ncols = max(1,round(tot/4+0.5))
    f, axes = plt.subplots(ncols,min(4,tot), figsize=(6,4))
    try:
        axes[0][0]
    except TypeError:
        try:
            axes[0]
        except TypeError:
            axes = [[axes]]
        else:
            axes = [axes]
    f.suptitle(f"Class {treeclass}", fontsize=14)
    f.tight_layout()
    iaxis_row = 0
    iaxis_col = 0
    for i,row in stocks_tc.iterrows():
        stock = row['stock']
        val = stocks_df.get(stock)
        df = val['df']
        tc = val['tc']
        chowC = val['chowClass']
        params = chowC.params()
        df.plot(x='day',y='Close',
                ax=axes[iaxis_row][iaxis_col],
                c = chowC.color,
                label = f"{stock}: {tc}")
        bkpt = chowC.breakpoint
        end = max(df['day'])
        if bkpt is not None:
            axes[iaxis_row][iaxis_col].plot((0,bkpt),(params[0][1],params[0][1]+bkpt*params[0][0]), color='#35978f')
            axes[iaxis_row][iaxis_col].plot((bkpt,end),(params[1][1]+bkpt*params[1][0],params[1][1]+end*params[1][0]), color='#bf812d')
        else:
            axes[iaxis_row][iaxis_col].plot((0,end),(params[0][1],params[0][1]+end*params[0][0]), color='#35978f')
        axes[iaxis_row][iaxis_col].set_title(f"{stock}")
        axes[iaxis_row][iaxis_col].get_legend().remove()
        axes[iaxis_row][iaxis_col].grid()
        iaxis_col+=1
        if iaxis_col>3:
            iaxis_col=0
            iaxis_row+=1
    plt.savefig(f'{treeclass}.pdf')

plt.show()



import numpy as np # data handling
import pandas as pd # data hanglind
import seaborn # data visualisation
from matplotlib import pyplot as plt # visualisation
from datetime import datetime as dt # time
import logging # for logging
logging.basicConfig(filename='miazluc_project1.py.log', encoding='utf-8', level=logging.DEBUG)
logger = logging.getLogger(__name__)
plt.rcParams.update({"text.usetex": True})
import tensorflow as tf # handling tensors
from tensorflow import keras # using neural networks with tf

class nnmodel():
    """A neural net model with methods for splitting and scaling data, 
    creating, compiling and fitting a neural net on the data,
    predicting data from the fitted model and plotting validation & testing error +
    plotting prediction"""
    def __init__(self, dfr, output=['y'], prop=0.1, activation= tf.nn.tanh,
                 nlayers = 3, layerwidth = 50,
                 epochs = 5000, loss = 'mean_squared_error', verbose = False):
        """
        initialise class
        :param dfr: dataframe with data
        :param output: colum(s) with output data 
                       (the remaining of the dataset is taken to be the input)
        :param prop: proportion of training set to sample from the df
        :param activation: activation function
        :param epochs: number of epochs for fitting
        :param loss: loss function
        """
        self.name = activation.__name__
        logger.info(f"Initialisation of model {self.name}")
        self.epochs = epochs
        self.nlayers = nlayers
        self.layerwidth = layerwidth
        self.loss = loss
        self.verbose = verbose
        self.df = dfr
        self.Y = dfr[output]
        keys = list(set(dfr.keys()).difference(set(output+['set'])))
        self.X = dfr[keys]
        self.prop_train = prop
        self.Xmin = 0
        self.Xrange = 1
        self.Ymin = 0
        self.Yrange = 1
        self.divide()
        self.create_model(activation)
        self.prediction=None
        self.scaled = False
    def divide(self):
        """Divide the input (X) and output (Y) sets into training and testing sets
        respecting self.prop_train as the proportion of training size to testing size"""
        self.Xtrain = self.X.sample(frac=self.prop_train, axis = 0)# sample on index
        self.Xtest = self.X.drop(self.Xtrain.index)
        self.Ytrain = self.Y.loc[self.Xtrain.index,]
        self.Ytest = self.Y.loc[self.Xtest.index,]
        self.df['set'] = ['Train' if i in self.Xtrain.index else 'Test' for i, row in self.df.iterrows()]
    def set_prop(self,prop):
        """Set accessor for self.prop_train"""
        self.prop_train = prop
        self.divide()
    def scale(self):
        """
        Scales the training and testing sets according to the train set
        Does nothing if already called once
        """
        if not self.scaled:
            logger.info(f"Scaling for model {self.name}")
            self.scaled = True
            self.Xmin = self.Xtrain.min()
            self.Xrange = self.Xtrain.max()-self.Xmin
            self.Ymin =self.Ytrain.min()
            self.Yrange = self.Ytrain.max()-self.Ymin
            self.Xtrain = (self.Xtrain-self.Xmin)/self.Xrange
            self.Xtest = (self.Xtest-self.Xmin)/self.Xrange
            self.Ytrain = (self.Ytrain-self.Ymin)/self.Yrange
            self.Ytest = (self.Ytest-self.Ymin)/self.Yrange
    def unscale(self):
        """Unscale prediction"""
        if self.scaled == True:
            logger.info(f"Unscaling for model {self.name}")
            self.range = (self.range*self.Xrange).add(self.Xmin)
            self.prediction = self.prediction * self.Yrange + self.Ymin
    def create_model(self, activation):
        """Create the keras Sequential NN model"""
        self.model = keras.Sequential()
        self.model.add(keras.layers.Dense(self.layerwidth,
                                          input_dim=self.X.shape[1],
                                          activation=activation))
        for i in range(0,self.nlayers-1):
            self.model.add(keras.layers.Dense(self.layerwidth, activation=activation))
        self.model.add(keras.layers.Dense(1, activation=activation))
    def compile(self):
        """
        Compile keras model
        :param loss: loss function passed to keras model
        """
        logger.info(f"Compiling model {self.name}")
        self.model.compile(loss=self.loss,
                           optimizer='adam')
    def fit(self):
        """
        Fit keras model
        :param epochs: integer with the number of epochs for the keras model
        :param verbose: passed to keras model
        """
        logger.info(f"Started fitting {self.name}, {dt.now():%Y-%m-%d %H:%M}")
        # Fitting model
        self.history = self.model.fit(self.Xtrain, self.Ytrain,
                    epochs=self.epochs,
                    verbose=self.verbose,
                    validation_data=(self.Xtest, self.Ytest),
                    batch_size=10)
        # Computing losses
        self.loss_train= self.model.evaluate(self.Xtrain, self.Ytrain, verbose=False)
        self.loss_test = self.model.evaluate(self.Xtest, self.Ytest, verbose=False)
    def plot_model_function(self, figsize=(6,2.5), range_n=300):
        """
        plot the model function
        :param figsize: tuple with parameters for figure sie passed to pyplot.subplots
        :param unscale: boolean, determine if the axes are send to self.unscale
        :param range_n: integer, number of points in the x range
        """
        logger.info(f"Plotting model function for model {self.name}")
        self.range = pd.DataFrame(np.linspace(self.X.min(), self.X.max(), 
                                              len(self.X.columns) *range_n),
                                  columns = self.X.columns)
        self.prediction = self.model.predict(self.range)
        self.prediction = pd.DataFrame(self.prediction, columns = self.Y.columns)
        self.unscale()
        with plt.style.context('fast'):
            f,axes = plt.subplots(1,2,figsize=figsize)
            palette = ['#35978f','#bf812d']
            seaborn.scatterplot(data=self.df, x="x", y="y", hue = 'set', 
                                s=5, ax = axes[0], palette = palette)
            axes[0].set_xlabel('$x$')
            axes[0].set_ylabel('$y$')
            axes[0].set_title('\\texttt{data.txt}')
            axes[0].grid()
            axes[1].scatter(x = self.range, y = self.prediction, color ='#c7eae5', s=3)
            axes[1].scatter(x=self.df.loc[self.df['set']=='Train','x'],
                            y=self.df.loc[self.df['set']=='Train','y'], color = '#bf812d', s=4)
            axes[1].set_xlabel('$x$')
            axes[1].set_ylabel('$y$')
            keyx = self.X.keys()[0]
            keyy = self.Y.keys()[0]
            axes[1].set_xlim(left = self.X[keyx].min(), right = self.X[keyx].max())
            axes[1].set_ylim(bottom = self.Y[keyy].min(), top = self.Y[keyy].max())
            axes[1].set_title('model prediction')
            axes[1].grid()
            plt.savefig(f'TASK4_{self.name}.pdf')
    def plot_history(self, figsize= (6,2.5),**kwargs):
        """
        Plot testing loss & accuracy and validation loss & accuracy
        :param history: a `<keras.History>` object
        :param file: a `<str>` with the saving filename for the image.
        :param figsize: a tuple with width and height of the output image in inches
        :param loss: a `<str>` with the name of the loss function
        """
        logger.info(f"Plotting history for model {self.name}")
        loss = self.history.history['loss']#training accuracy
        val_loss = self.history.history['val_'+"loss"]#validation accuracy
        x = range(1, len(val_loss) + 1)
        with plt.style.context('fast'):
            f,axis = plt.subplots(1,1,figsize=figsize)
            f.tight_layout()
            # Mean Absolute Error
            axis.plot(x, loss, '#c7eae5', label='Training')
            axis.plot(x, val_loss, '#bf812d', label='Validation')
            title = self.loss.replace('_',' ').capitalize()
            axis.set_title(f'{title}')
            axis.legend()
            axis.grid()
            plt.savefig(f"TASK3_{self.name}.pdf", **kwargs)

def df_stack(dfpile):
    for stock, pile in dfpile.items():
        dfp = pile['df']
        # scaling of days (end becomes 0 and shifts all in negatives
        #                   this aligns all time trends irrespective of their length)
        maxdays = dfp['day'].max()
        dfp['x']=dfp['day']-maxdays-1000
        # scaling stocks close relative to last close
        close = dfp.iloc[-1]['Close']
        dfp['y'] = dfp['Close']/close
        dfp['stock'] = stock
        dfp['s'] = stocks.index(stock)
        yield dfp
    yield None

#join df with an added column stock
stockgen = df_stack(stocks_df)
dfall = stockgen.__next__()
nextdf = stockgen.__next__()
while(nextdf is not None):
    dfall = dfall.append(nextdf)
    nextdf = stockgen.__next__()

dfall['id'] = range(0,len(dfall))
dfall.index = dfall['id']
import copy
df_sub = copy.copy(dfall[['s','x','y']])

# scale 'x':
df_sub['x']= (df_sub['x']-df_sub['x'].min())/(df_sub['x'].max()-df_sub['x'].min())
df_sub['s']= (df_sub['s']+1)/len(stocks)
df_sub['y'] = (df_sub['y']-df_sub['y'].min())/(df_sub['y'].max()-df_sub['y'].min())

model =  nnmodel(df_sub, output = ["y"],
                     prop=0.2, activation=tf.nn.elu,
                     epochs = 1000, loss = 'mean_squared_error',
                     nlayers = 6, layerwidth=20)
model.compile()
model.verbose=True
model.fit()
model.plot_history()

model.prediction= model.model.predict(df_sub[['s','x']])
f,ax = plt.subplots()
ax.scatter(x=df_sub['y'],y=model.prediction, s=1)
ax.grid()
plt.show()

df_pred = pd.DataFrame([[(i+1)/len(stocks),d,stocks[i]] for i in range(0,len(stocks)) for d in [1,1.1,1.2,1.5]],
                        columns = ['s','x','stock'])
model.prediction = model.model.predict(df_pred[['s','x']])
df_pred['y'] = model.prediction

dfp = df_pred.pivot(columns='x',values='y', index='stock')
dfp['stock']=dfp.index
dfp['ret1.1']=[(((row[1.1])/row[1])-1)*100 for i,row in dfp.iterrows()]
dfp['ret1.2']=[(((row[1.2])/row[1])-1)*100 for i,row in dfp.iterrows()]
dfp['ret1.5']=[(((row[1.5])/row[1])-1)*100 for i,row in dfp.iterrows()]