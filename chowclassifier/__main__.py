"""Command-line interface for the chowclassifier package."""
# __main__.py
import argparse
import warnings
from chowclassifier.chewdata import ChewData


def main(argv=None):
    """
    run analysis on given data

    :params -f, --filename: filename
    :params -s, --sep: separator for parsing the filename (if type csv)
    :params -X, --timecol: timecol
    :params -y, --ycol: ycol
    :params -n, --namecol: name of column for groupby
    :params -b, --breakpoint: initial breakpoint (if None, midpoint will be taken)
    :params -k, --breakpoints: candidates for breakpoints (list)
    :params -m, --margin: margin around initial breakpoint
    :params -o, --output: filename for the excel or csv file output
    :params -p, --path: path where the figures will be saved
    :params -a, --alpha: significance level in (0,1)
    :params --no-figures: Do not export figures
    :params --no-table: Do not export results table
    :params --nrows: Numbers of rows in the grouped figure (leave ncols blank)
    :params --ncols: Number of columns in the groupe figure (leave nrows blank)
    :params --fig-title: title of the figure
    :params --xlabel: label of the x axis
    :params --ylabel: label of the y axis
    :params -g, --groupcol: column with sub-groups
    :params --sharey / --no-sharey: share y axis across subplots
    :params --figsize: size of figures
    """
    parser = argparse.ArgumentParser(
        prog="chowclassifier",
        description="Classify the time trends of each series in a table with Chow tests.")
    parser.add_argument('-f','--filename', type=str, help="CSV, TSV or Excel file")
    parser.add_argument('-X','--timecol', type=str, default = 'date')
    parser.add_argument('-y','--ycol', type=str, default = 'value')
    parser.add_argument('-n','--namecol', type=str, default = 'name')
    parser.add_argument('-g','--groupcol', type=str, default = 'g',
                        help="column with sub-groups (plotted by group)")
    parser.add_argument('-b','--breakpoint', type=float, default = None)
    # was type=list, which split the argument into characters
    parser.add_argument('-k','--breakpoints', type=float, nargs='+', default = None,
                        help="not supported yet: ignored with a warning")
    parser.add_argument('-m','--margin', type=int, default = 5)
    parser.add_argument('-o','--output', type=str, default = 'output.xlsx')
    parser.add_argument('-p','--path', type=str, default = 'figs')
    parser.add_argument('-s','--sep', type=str, default = ',')
    parser.add_argument('-a','--alpha', type=float, default = 0.01)
    # Flags instead of type=bool: bool("False") is True, so
    # "--no-figures False" used to disable the figures.
    parser.add_argument('--no-figures', action='store_true', help="do not export figures")
    parser.add_argument('--no-table', action='store_true', help="do not export the results table")
    parser.add_argument('--nrows', type=int, default = None)
    parser.add_argument('--ncols', type=int, default = 3)
    parser.add_argument('--fig-title', type=str, default = '')
    parser.add_argument('--fig-format', type=str, default = 'pdf')
    parser.add_argument('--xlabel', type=str, default = 'X')
    parser.add_argument('--ylabel', type=str, default = 'y')
    parser.add_argument('--sharey', action=argparse.BooleanOptionalAction, default = True,
                        help="share the y axis across subplots (--no-sharey to disable)")
    parser.add_argument('--figsize', type=float, nargs=2, default = (16, 8),
                        metavar=('WIDTH', 'HEIGHT'))
    args = parser.parse_args(argv)
    if args.filename is None:
        print("No data given. Please pass filename as argument --filename 'data.csv'")
        return
    if args.breakpoints is not None:
        warnings.warn("--breakpoints is not supported yet and is ignored; "
                      "use --breakpoint and --margin.", stacklevel=1)
    chew = ChewData(filename = args.filename,
                namecol = args.namecol,
                groupcol = args.groupcol,
                ycol = args.ycol,
                timecol = args.timecol,
                sep = args.sep,
                margin = args.margin,
                alpha = args.alpha,
                initial_breakpoint = args.breakpoint)
    chew.run()
    if not args.no_table:
        chew.save_to_file(filename = args.output, sep = args.sep)
    if not args.no_figures:
        chew.plot(f'output.{args.fig_format}',
               nrows = args.nrows,
               ncols = args.ncols,
               sharey = args.sharey,
               figsize = tuple(args.figsize),
               title = args.fig_title,
               xlabel = args.xlabel,
               ylabel = args.ylabel,
               )
        # fmt, not format: --fig-format was ignored for these figures
        chew.plot_individually(savingpath = args.path, fmt = args.fig_format,
                               xlabel = args.xlabel, ylabel = args.ylabel)


if __name__ == "__main__":

    main()
