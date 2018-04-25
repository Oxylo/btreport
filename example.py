# -*- coding: utf-8; py-indent-offset:4 -*-
import os
import sys
import pandas as pd
import backtrader as bt
from report import Cerebro


class CrossOver(bt.Strategy):
    """A simple moving average crossover strategy,
    at SMA 50/200 a.k.a. the "Golden Cross Strategy"
    """
    params = (('fast', 50),
              ('slow', 200),
              ('order_pct', 0.95),
              ('market', 'BTC/USD')
              )

    def __init__(self):
        sma = bt.indicators.SimpleMovingAverage
        cross = bt.indicators.CrossOver
        self.fastma = sma(self.data.close,
                          period=self.p.fast,
                          plotname='FastMA')
        sma = bt.indicators.SimpleMovingAverage
        self.slowma = sma(self.data.close,
                          period=self.p.slow,
                          plotname='SlowMA')
        self.crossover = cross(self.fastma, self.slowma)

    def start(self):
        self.size = None

    def log(self, txt, dt=None):
        """ Logging function for this strategy
        """
        dt = dt or self.datas[0].datetime.date(0)
        time = self.datas[0].datetime.time()
        print('%s - %s, %s' % (dt.isoformat(), time, txt))

    def next(self):
        if self.position.size == 0:
            if self.crossover > 0:
                amount_to_invest = (self.p.order_pct *
                                    self.broker.cash)
                self.size = amount_to_invest / self.data.close
                msg = "*** MKT: {} BUY: {}"
                self.log(msg.format(self.p.market, self.size))
                self.buy(size=self.size)

        if self.position.size > 0:
            # we have an open position or made it to the end of backtest
            last_candle = (self.data.close.buflen() == len(self.data.close) + 1)
            if (self.crossover < 0) or last_candle:
                msg = "*** MKT: {} SELL: {}"
                self.log(msg.format(self.p.market, self.size))
                self.close()


if __name__ == "__main__":
    try:
        OUTPUTDIR = sys.argv[1]
    except IndexError as e:
        print(e, "\nPlease include outfile directory")
        sys.exit(1)

    # read data
    TESTDATA = 'btc_usd.csv'
    basedir = os.path.abspath(os.path.dirname(__file__))
    datadir = os.path.join(basedir, 'sampledata')
    infile = os.path.join(datadir, TESTDATA)
    ohlc = pd.read_csv(infile, index_col='dt', parse_dates=True)

    # initialize Cerebro engine, extende with report method
    cerebro = Cerebro()
    cerebro.broker.setcash(100)

    # add data
    feed = bt.feeds.PandasData(dataname=ohlc)
    cerebro.adddata(feed)

    # add Golden Cross strategy
    params = (('fast', 50),
              ('slow', 200),
              ('order_pct', 0.95),
              ('market', 'BTC/USD')
              )
    cerebro.addstrategy(strategy=CrossOver, **dict(params))

    # run backtest with both plotting and reporting
    cerebro.run()
    cerebro.plot(volume=False)
    cerebro.report(OUTPUTDIR,
                   infilename='btc_usd.csv',
                   user='Trading John',
                   memo='a.k.a. Golden Cross',)
