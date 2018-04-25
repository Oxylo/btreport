import backtrader as bt
import sys
import matplotlib.pyplot as plt
import os
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from utils import timestamp2str, get_now, dir_exists


class PerformanceReport:
    """ Report with performce stats for given backtest run
    """

    def __init__(self, stratbt, infilename,
                 outputdir, user, memo):
        self.stratbt = stratbt  # works for only 1 stategy
        self.infilename = infilename
        self.outputdir = outputdir
        self.user = user
        self.memo = memo
        self.check_and_assign_defaults()

    def check_and_assign_defaults(self):
        """ Check initialization parameters or assign defaults
        """
        if not self.infilename:
            self.infilename = 'Not given'
        if not dir_exists(self.outputdir):
            msg = "*** ERROR: outputdir {} does not exist."
            print(msg.format(self.outputdir))
            sys.exit(0)
        if not self.user:
            self.user = 'Happy Canary'
        if not self.memo:
            self.memo = 'No comments'

    def get_performance_stats(self):
        """ Return dict with performace stats for given strategy withing backtest
        """
        st = self.stratbt
        dt = st.data._dataname['open'].index
        trade_analysis = st.analyzers.myTradeAnalysis.get_analysis()
        rpl = trade_analysis.pnl.net.total
        total_return = rpl / self.get_startcash()
        total_number_trades = trade_analysis.total.total
        trades_closed = trade_analysis.total.closed
        bt_period = dt[-1] - dt[0]
        bt_period_days = bt_period.days
        drawdown = st.analyzers.myDrawDown.get_analysis()
        sharpe_ratio = st.analyzers.mySharpe.get_analysis()['sharperatio']
        sqn_score = st.analyzers.mySqn.get_analysis()['sqn']
        kpi = {# PnL
               'start_cash': self.get_startcash(),
               'rpl': rpl,
               'result_won_trades': trade_analysis.won.pnl.total,
               'result_lost_trades': trade_analysis.lost.pnl.total,
               'profit_factor': (-1 * trade_analysis.won.pnl.total / trade_analysis.lost.pnl.total),
               'rpl_per_trade': rpl / trades_closed,
               'total_return': 100 * total_return,
               'annual_return': (100 * (1 + total_return)**(365.25 / bt_period_days) - 100),
               'max_money_drawdown': drawdown['max']['moneydown'],
               'max_pct_drawdown': drawdown['max']['drawdown'],
               # trades
               'total_number_trades': total_number_trades,
               'trades_closed': trades_closed,
               'pct_winning': 100 * trade_analysis.won.total / trades_closed,
               'pct_losing': 100 * trade_analysis.lost.total / trades_closed,
               'avg_money_winning': trade_analysis.won.pnl.average,
               'avg_money_losing':  trade_analysis.lost.pnl.average,
               'best_winning_trade': trade_analysis.won.pnl.max,
               'worst_losing_trade': trade_analysis.lost.pnl.max,
               #  performance
               'sharpe_ratio': sharpe_ratio,
               'sqn_score': sqn_score,
               'sqn_human': self._sqn2rating(sqn_score)
               }
        return kpi

    def get_equity_curve(self):
        """ Return series containing equity curve
        """
        st = self.stratbt
        dt = st.data._dataname['open'].index
        value = st.observers.broker.lines[1].array[:len(dt)]
        curve = pd.Series(data=value, index=dt)
        return 100 * curve / curve.iloc[0]

    def _sqn2rating(self, sqn_score):
        """ Converts sqn_score score to human readable rating
        See: http://www.vantharp.com/tharp-concepts/sqn.asp
        """
        if sqn_score < 1.6:
            return "Poor"
        elif sqn_score < 1.9:
            return "Below average"
        elif sqn_score < 2.4:
            return "Average"
        elif sqn_score < 2.9:
            return "Good"
        elif sqn_score < 5.0:
            return "Excellent"
        elif sqn_score < 6.9:
            return "Superb"
        else:
            return "Holy Grail"

    def __str__(self):
        msg = ("*** PnL: ***\n"
               "Start capital         : {start_cash:4.2f}\n"
               "Total net profit      : {rpl:4.2f}\n"
               "Result winning trades : {result_won_trades:4.2f}\n"
               "Result lost trades    : {result_lost_trades:4.2f}\n"
               "Profit factor         : {profit_factor:4.2f}\n"
               "Total return          : {total_return:4.2f}%\n"
               "Annual return         : {annual_return:4.2f}%\n"
               "Max. money drawdown   : {max_money_drawdown:4.2f}\n"
               "Max. percent drawdown : {max_pct_drawdown:4.2f}%\n\n"
               "*** Trades ***\n"
               "Number of trades      : {total_number_trades:d}\n"
               "    %winning          : {pct_winning:4.2f}%\n"
               "    %losing           : {pct_losing:4.2f}%\n"
               "    avg money winning : {avg_money_winning:4.2f}\n"
               "    avg money losing  : {avg_money_losing:4.2f}\n"
               "    best winning trade: {best_winning_trade:4.2f}\n"
               "    worst losing trade: {worst_losing_trade:4.2f}\n\n"
               "*** Performance ***\n"
               "Sharpe ratio          : {sharpe_ratio:4.2f}\n"
               "SQN score             : {sqn_score:4.2f}\n"
               "SQN human             : {sqn_human:s}"
               )
        kpis = self.get_performance_stats()
        # see: https://stackoverflow.com/questions/24170519/
        # python-# typeerror-non-empty-format-string-passed-to-object-format
        kpis = {k: -999 if v is None else v for k, v in kpis.items()}
        return msg.format(**kpis)

    def plot_equity_curve(self, fname='equity_curve.png'):
        """ Plots equity curve to png file
        """
        curve = self.get_equity_curve()
        buynhold = self.get_buynhold_curve()
        xrnge = [curve.index[0], curve.index[-1]]
        dotted = pd.Series(data=[100, 100], index=xrnge)
        fig, ax = plt.subplots(1, 1)
        ax.set_ylabel('Net Asset Value (start=100)')
        ax.set_title('Equity curve')
        _ = curve.plot(kind='line', ax=ax)
        _ = buynhold.plot(kind='line', ax=ax, color='grey')
        _ = dotted.plot(kind='line', ax=ax, color='grey', linestyle=':')
        return fig

    def _get_periodicity(self):
        """ Maps length backtesting interval to appropriate periodiciy for return plot
        """
        curve = self.get_equity_curve()
        startdate = curve.index[0]
        enddate = curve.index[-1]
        time_interval = enddate - startdate
        time_interval_days = time_interval.days
        if time_interval_days > 5 * 365.25:
            periodicity = ('Yearly', 'Y')
        elif time_interval_days > 365.25:
            periodicity = ('Monthly', 'M')
        elif time_interval_days > 50:
            periodicity = ('Weekly', '168H')
        elif time_interval_days > 5:
            periodicity = ('Daily', '24H')
        elif time_interval_days > 0.5:
            periodicity = ('Hourly', 'H')
        elif time_interval_days > 0.05:
            periodicity = ('Per 15 Min', '15M')
        else: periodicity = ('Per minute', '1M')
        return periodicity

    def plot_return_curve(self, fname='return_curve.png'):
        """ Plots return curve to png file
        """
        curve = self.get_equity_curve()
        period = self._get_periodicity()
        values = curve.resample(period[1]).ohlc()['close']
        # returns = 100 * values.diff().shift(-1) / values
        returns = 100 * values.diff() / values
        returns.index = returns.index.date
        is_positive = returns > 0
        fig, ax = plt.subplots(1, 1)
        ax.set_title("{} returns".format(period[0]))
        ax.set_xlabel("date")
        ax.set_ylabel("return (%)")
        _ = returns.plot.bar(color=is_positive.map({True: 'green', False: 'red'}), ax=ax)
        return fig

    def generate_html(self):
        """ Returns parsed HTML text string for report
        """
        basedir = os.path.abspath(os.path.dirname(__file__))
        images = os.path.join(basedir, 'templates')
        eq_curve = os.path.join(images, 'equity_curve.png')
        rt_curve = os.path.join(images, 'return_curve.png')
        fig_equity = self.plot_equity_curve()
        fig_equity.savefig(eq_curve)
        fig_return = self.plot_return_curve()
        fig_return.savefig(rt_curve)
        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template("templates/template.html")
        header = self.get_header_data()
        kpis = self.get_performance_stats()
        graphics = {'url_equity_curve': 'file://' + eq_curve,
                    'url_return_curve': 'file://' + rt_curve
                    }
        all_numbers = {**header, **kpis, **graphics}
        html_out = template.render(all_numbers)
        return html_out

    def generate_pdf_report(self):
        """ Returns PDF report with backtest results
        """
        html = self.generate_html()
        outfile = os.path.join(self.outputdir, 'report.pdf')
        HTML(string=html).write_pdf(outfile)
        msg = "See {} for report with backtest results."
        print(msg.format(outfile))

    def get_strategy_name(self):
        return self.stratbt.__class__.__name__

    def get_strategy_params(self):
        return self.stratbt.cerebro.strats[0][0][-1]

    def get_start_date(self):
        """ Return first datafeed datetime
        """
        dt = self.stratbt.data._dataname['open'].index
        return timestamp2str(dt[0])

    def get_end_date(self):
        """ Return first datafeed datetime
        """
        dt = self.stratbt.data._dataname['open'].index
        return timestamp2str(dt[-1])

    def get_header_data(self):
        """ Return dict with data for report header
        """
        header = {'strategy_name': self.get_strategy_name(),
                  'params': self.get_strategy_params(),
                  'file_name': self.infilename,
                  'start_date': self.get_start_date(),
                  'end_date': self.get_end_date(),
                  'name_user': self.user,
                  'processing_date': get_now(),
                  'memo_field': self.memo
                  }
        return header

    def get_series(self, column='close'):
        """ Return data series
        """
        return self.stratbt.data._dataname[column]

    def get_buynhold_curve(self):
        """ Returns Buy & Hold equity curve starting at 100
        """
        s = self.get_series(column='open')
        return 100 * s / s[0]

    def get_startcash(self):
        return self.stratbt.broker.startingcash


class Cerebro(bt.Cerebro):
    def __init__(self, **kwds):
        super().__init__(**kwds)
        self.add_report_analyzers()

    def add_report_analyzers(self, riskfree=0.01):
            """ Adds performance stats, required for report
            """
            self.addanalyzer(bt.analyzers.SharpeRatio,
                             _name="mySharpe",
                             riskfreerate=riskfree,
                             timeframe=bt.TimeFrame.Months)
            self.addanalyzer(bt.analyzers.DrawDown,
                             _name="myDrawDown")
            self.addanalyzer(bt.analyzers.AnnualReturn,
                             _name="myReturn")
            self.addanalyzer(bt.analyzers.TradeAnalyzer,
                             _name="myTradeAnalysis")
            self.addanalyzer(bt.analyzers.SQN,
                             _name="mySqn")

    def get_strategy_backtest(self):
        return self.runstrats[0][0]

    def report(self, outputdir,
               infilename=None, user=None, memo=None):
        bt = self.get_strategy_backtest()
        rpt =PerformanceReport(bt, infilename=infilename,
                               outputdir=outputdir, user=user,
                               memo=memo)
        rpt.generate_pdf_report()
