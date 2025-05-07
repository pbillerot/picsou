"""
    ROUTINES INDÉPENDANTES
"""
import numpy as np

class Cpu:
    """
        Classe CPU COMPUTE PROCESSING UNIT
    """

    def __init__(self):
        """ Initialisation """

    def compute_rsi(self, data, n=14):
        deltas = np.diff(data)
        seed = deltas[:n+1]
        up = seed[seed>=0].sum()/n
        down = -seed[seed<0].sum()/n
        if down == 0:
            down = 1
        rs = up/down
        rsi = np.zeros_like(data)
        rsi[:n] = 100. - 100./(1.+rs)

        for i in range(n, len(data)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta

            up = (up*(n-1) + upval)/n
            down = (down*(n-1) + downval)/n
            if down == 0:
                down = 1
            rs = up/down
            rsi[i] = 100. - 100./(1.+rs)
        return rsi[len(rsi)-1]

    def ema(self, data, window):
        """ Calculates Exponential Moving Average """
        if len(data) < 2 * window:
            window = len(data)//2
            if window < 2 : return None
            # raise ValueError("data is too short")
        c = 2.0 / (window + 1)
        current_ema = self.sma(data[-window*2:-window], window)
        for value in data[-window:]:
            current_ema = (c * value) + ((1 - c) * current_ema)
        return current_ema

    def sma(self, data, window):
        """ Calculates Simple Moving Average """
        if len(data) < window:
            return sum(data) / float(len(data))
        return sum(data[-window:]) / float(window)

    def calcRSI(self, data, P=14):
        # Calculate gains and losses
        # https://raposa.trade/blog/2-ways-to-trade-the-stochastic-rsi-in-python/
        data['diff_close'] = data['close'] - data['close'].shift(1)
        data['gain'] = np.where(data['diff_close']>0,
            data['diff_close'], 0)
        data['loss'] = np.where(data['diff_close']<0,
            np.abs(data['diff_close']), 0)

        # Get initial values
        data[['init_avg_gain', 'init_avg_loss']] = data[
            ['gain', 'loss']].rolling(P).mean()
        # Calculate smoothed avg gains and losses for all t > P
        avg_gain = np.zeros(len(data))
        avg_loss = np.zeros(len(data))

        for i, _row in enumerate(data.iterrows()):
            row = _row[1]
            if i < P - 1:
                last_row = row.copy()
                continue
            elif i == P-1:
                avg_gain[i] += row['init_avg_gain']
                avg_loss[i] += row['init_avg_loss']
            else:
                avg_gain[i] += ((P - 1) * avg_gain[i-1] + row['gain']) / P
                avg_loss[i] += ((P - 1) * avg_loss[i-1] + row['loss']) / P

            last_row = row.copy()

        data['avg_gain'] = avg_gain
        data['avg_loss'] = avg_loss
        # Calculate RS and RSI
        data['RS'] = data['avg_gain'] / data['avg_loss']
        data['RSI'] = 100 - 100 / (1 + data['RS'])
        return data

    def calcStochOscillator(self, data, N=14):
        data['low_N'] = data['RSI'].rolling(N).min()
        data['high_N'] = data['RSI'].rolling(N).max()
        data['StochRSI'] = 100 * (data['RSI'] - data['low_N']) / (data['high_N'] - data['low_N'])
        return data

    def calcStochRSI(self, data, P=14, N=14):
        data = self.calcRSI(data, P)
        data = self.calcStochOscillator(data, N)
        return data

    def calcReturns(self, df):
        # Helper function to avoid repeating too much code
        df['returns'] = df['Close'] / df['Close'].shift(1)
        df['log_returns'] = np.log(df['returns'])
        df['strat_returns'] = df['position'].shift(1) * df['returns']
        df['strat_log_returns'] = df['position'].shift(1) * df['log_returns']
        df['cum_returns'] = np.exp(df['log_returns'].cumsum()) - 1
        df['strat_cum_returns'] = np.exp(df['strat_log_returns'].cumsum()) / - 1
        df['peak'] = df['cum_returns'].cummax()
        df['strat_peak'] = df['strat_cum_returns'].cummax()
        return df
