from chowclassifier import ChewData, Chow
# define the path to data
filepath = "data"
# define the name of the file containing the data (with extension)
filename = "stocks.csv"
# define the path where figures will be saved
savingpath_figures = 'fig'
# what name has the X/time column?
timecol = 'Date'
# what name has the y/value column?
ycol = 'Close'
# initial breakpoint ?
initial_breakpoint = None

C = ChewData(filename = f"{'/'.join([x for x in [filepath,filename] if x not in [None,'']])}",
            timecol = timecol, ycol = ycol,
            breakpoint = initial_breakpoint)

########## use the code line below if your X/time column is not a number, e.g. a date
########## comment it otherwise
C.parse_timecol(date_format = '%Y-%m-%d') # 

C.run()
C.plot(xlabel = 'time', ylabel='value',# labels given to the axes
        title = "Chow Classification",# title of the main plot
        filename = f"{'/'.join([x for x in [savingpath_figures,filename] if x not in [None,'']])}.pdf",
        figsize=(16,8),sharey=True)
C.plot_individually(savingpath = savingpath_figures, format = 'pdf',
                    xlabel = 'time', ylabel='value',# labels given to the axes
                    )