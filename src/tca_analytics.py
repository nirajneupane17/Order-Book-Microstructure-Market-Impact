"""
tca_analytics.py
================
Transaction Cost Analysis (TCA) — the standard framework used by
institutional investors, hedge funds, and prime brokers to evaluate
execution quality and measure slippage.

Author : Niraj Neupane | github.com/nirajneupane17
Series : Quant Trading Projects — Project 4 of 20
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional


def arrival_price_slippage(exec_price: float,
                            arrival_price: float,
                            side: int = 1) -> float:
    """
    Arrival price slippage (bps) — most common TCA metric.
    side: +1 for buy order, -1 for sell order.
    Positive = paid more than arrival price (adverse slippage).
    """
    return side * (exec_price - arrival_price) / arrival_price * 10000


def vwap_shortfall(exec_price: float, mkt_vwap: float,
                    side: int = 1) -> float:
    """
    VWAP shortfall — how much better/worse you did vs market VWAP.
    Negative shortfall = beat the benchmark (good for buys).
    """
    return side * (exec_price - mkt_vwap) / mkt_vwap * 10000


def participation_rate(exec_volume: float, mkt_volume: float) -> float:
    """
    Participation rate = fraction of market volume your trade represents.
    >5% = significant market participant, expect higher impact.
    >20% = very high, will move the market.
    """
    return exec_volume / mkt_volume if mkt_volume > 0 else 0.0


def tca_report(exec_df: pd.DataFrame) -> pd.DataFrame:
    """
    Full TCA report per stock — summarises all execution quality metrics.

    Required columns in exec_df:
    stock, mid_price, vwap, twap, spread_cost_bps, vwap_vs_twap_bps

    Returns summary DataFrame with:
    - Spread cost, VWAP slippage, total cost (all in bps)
    - Best/worst day execution
    - Execution quality rating
    """
    rows = []
    for stock in exec_df['stock'].unique():
        d = exec_df[exec_df['stock'] == stock]
        spread = d['spread_cost_bps'].mean()
        slippage = d['vwap_vs_twap_bps'].mean()
        total = spread + abs(slippage)
        quality = 'Excellent' if total < 2 else 'Good' if total < 5 else 'Fair' if total < 10 else 'Poor'
        rows.append({
            'stock':             stock,
            'spread_cost_bps':   round(spread, 3),
            'vwap_slippage_bps': round(slippage, 3),
            'total_cost_bps':    round(total, 3),
            'best_day_cost':     round(d['vwap_vs_twap_bps'].abs().min(), 3),
            'worst_day_cost':    round(d['vwap_vs_twap_bps'].abs().max(), 3),
            'execution_quality': quality,
        })
    return pd.DataFrame(rows).set_index('stock')


def intraday_volume_profile(minute_bars: pd.DataFrame,
                              stock: str) -> pd.Series:
    """
    Compute average intraday volume profile (U-shape).
    Used to build VWAP schedules — trade when everyone else trades.
    """
    d = minute_bars[minute_bars['stock'] == stock].copy()
    d['hour'] = pd.to_datetime(d['datetime']).dt.hour
    d['minute'] = pd.to_datetime(d['datetime']).dt.minute
    profile = d.groupby(['hour', 'minute'])['volume'].mean()
    return profile / profile.sum()


if __name__ == '__main__':
    exec_df = pd.read_csv('/home/claude/MKT/data/execution_analysis.csv')
    report = tca_report(exec_df)
    print("TCA Report:")
    print(report[['spread_cost_bps', 'vwap_slippage_bps',
                   'total_cost_bps', 'execution_quality']].to_string())
    print("tca_analytics.py OK")
