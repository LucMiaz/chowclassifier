from chowclassifier import ChewData
# define the path to data
filepath = "example/data"
# define the name of the file containing the data (with extension)
filename = "stocks.csv"
# define the path where figures will be saved
savingpath_figures = 'example/fig'
# what name has the X/time column?
timecol = 'Date'
# what name has the y/value column?
ycol = 'Close'
# what level of confidence? Note, when
# testing multiple breakpoint, a Bonferroni correction will be applied
alpha = 0.01
# initial breakpoint ?
initial_breakpoint = None

C = ChewData(filename = f"{'/'.join([x for x in [filepath,filename] if x not in [None,'']])}",
            timecol = timecol,# name of time column (used as x-axis)
            ycol = ycol,# name for value column (used as y-axis) Leave blank if multiple
            alpha = alpha# level of confidence to use
            )

########## use the code line below if your X/time column is not a number, e.g. a date
########## comment it otherwise
# C.parse_timecol(date_format = '%Y-%m-%d') # 

C.run(initial_breakpoint = initial_breakpoint)
C.plot(xlabel = 'time',# label for x axis
       ylabel='value',# label for y axis
       title = "Chow Classification",# title of the main plot
       filename = f"{'/'.join([x for x in [savingpath_figures,filename] if x not in [None,'']])}.png",# filename for the figure
       figsize=(16,8),# figure size
       sharey=True, # whether the individual plots are forced to share y axis
       linestyles = ['dotted','solid','solid'],# linestyle of each trend category (neutral, increasing, decreasing)
       )
C.plot_individually(savingpath = savingpath_figures,# Saving path for the figures
                    format = 'png',# figure format
                    xlabel = 'time',# label for x axis
                    ylabel='value',# label for y axis
                    )

C.plot_by_group('g',
                savingpath = savingpath_figures,# Saving path for the figures
                format = 'png',# figure format
                xlabel = 'time',# label for x axis
                ylabel='value',# label for y axis
                plot_overall = True,# Whether to plot an overall trend across groups (including confidence inverval fill)
                plot_individual_fill = True# Whether to plot individual confidence inverval fills
                )