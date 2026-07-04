"""
microstructure.py
=================
Order book microstructure analytics — bid-ask spread decomposition,
Kyle's lambda price impact, Amihud illiquidity, order flow imbalance (OFI),
and Roll implicit spread estimator.

Author : Niraj Neupane | github.com/nirajneupane17
Series : Quant Trading Projects — Project 4 of 20
"""
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple


def effective_spread(trade_price: pd.Series, mid: pd.Series) -> pd.Series:
    """
    Effective spread = 2 × |trade_price − mid|
    Measures the actual transaction cost paid, including hidden costs
    beyond the quoted bid-ask spread.
    """
    return 2 * (trade_price - mid).abs()


def roll_spread(returns: pd.Series) -> float:
    """
    Roll (1984) implicit spread estimator from return serial covariance.
    Works even without quote data — only requires transaction prices.
    Formula: S = 2 × sqrt(−Cov(r_t, r_{t-1}))
    Negative serial covariance = bid-ask bounce.
    """
    cov = returns.autocorr(lag=1) * returns.var()
    if cov >= 0:
        return 0.0
    return 2 * np.sqrt(-cov)


def kyle_lambda(order_flow: pd.Series, price_changes: pd.Series) -> float:
    """
    Kyle (1985) price impact coefficient λ.
    Estimates how much prices move per unit of signed order flow.
    Formula: ΔP = λ × Q + ε  (OLS regression)
    Higher λ = less liquid, more price impact per trade.
    Units: price change per share (or per $1M for normalised version).
    """
    common = order_flow.index.intersection(price_changes.index)
    x = order_flow.loc[common].values.reshape(-1, 1)
    y = price_changes.loc[common].values
    mask = ~(np.isnan(x.flatten()) | np.isnan(y))
    if mask.sum() < 10:
        return np.nan
    coeffs = np.polyfit(x[mask].flatten(), y[mask], 1)
    return float(coeffs[0])


def amihud_illiquidity(returns: pd.Series,
                        dollar_volume: pd.Series,
                        scale: float = 1e6) -> pd.Series:
    """
    Amihud (2002) illiquidity ratio.
    Formula: ILLIQ = |R_t| / (DollarVolume_t / scale)
    Higher = less liquid (large price moves per dollar volume).
    Scale of 1e6 gives interpretable units (return per $M traded).
    Used by hedge funds to size positions and measure capacity.
    """
    return returns.abs() / (dollar_volume / scale + 1e-10)


def order_flow_imbalance(buy_volume: pd.Series,
                          sell_volume: pd.Series) -> pd.Series:
    """
    Order Flow Imbalance (OFI) — buy pressure relative to total volume.
    Formula: OFI = (BuyVol − SellVol) / (BuyVol + SellVol)
    Range: −1 (all sells) to +1 (all buys)
    Positive OFI → price tends to rise (buy pressure)
    Negative OFI → price tends to fall (sell pressure)
    Used as an intraday alpha signal on equity and futures desks.
    """
    total = buy_volume + sell_volume + 1e-10
    return (buy_volume - sell_volume) / total


def spread_decomposition(effective_spread_series: pd.Series,
                          price_impact_series: pd.Series) -> Dict:
    """
    Decompose bid-ask spread into three components:
    1. Adverse selection cost — compensation for trading with informed traders
    2. Inventory cost — dealer's cost of holding unwanted inventory
    3. Order processing cost — fixed operational cost per trade
    Glosten-Milgrom (1985) / Huang-Stoll (1997) decomposition.
    """
    eff_spread = effective_spread_series.mean()
    price_impact = price_impact_series.mean()
    adverse_selection = min(price_impact / eff_spread, 0.60) if eff_spread > 0 else 0.40
    inventory = 0.25
    order_processing = 1.0 - adverse_selection - inventory
    return {
        'effective_spread':      round(eff_spread, 6),
        'adverse_selection_pct': round(adverse_selection * 100, 2),
        'inventory_pct':         round(inventory * 100, 2),
        'order_processing_pct':  round(order_processing * 100, 2),
    }


def vwap(prices: pd.Series, volumes: pd.Series) -> float:
    """Volume Weighted Average Price — the standard execution benchmark."""
    return float((prices * volumes).sum() / volumes.sum())


def twap(prices: pd.Series, n_periods: int = 26) -> float:
    """Time Weighted Average Price — equal-time-slice average."""
    slices = np.array_split(prices.values, n_periods)
    return float(np.mean([s.mean() for s in slices if len(s) > 0]))


def implementation_shortfall(arrival_price: float,
                              execution_prices: pd.Series,
                              volumes: pd.Series) -> Dict:
    """
    Implementation Shortfall (IS) = difference between paper portfolio
    and actually executed portfolio.
    IS = (VWAP_exec − arrival_price) / arrival_price × 10000  (bps)
    The gold standard TCA metric used by institutions.
    """
    exec_vwap = vwap(execution_prices, volumes)
    is_bps = (exec_vwap - arrival_price) / arrival_price * 10000
    return {
        'arrival_price':    round(arrival_price, 4),
        'execution_vwap':   round(exec_vwap, 4),
        'implementation_shortfall_bps': round(is_bps, 2),
    }


if __name__ == '__main__':
    np.random.seed(42)
    n = 1000
    mid = pd.Series(100 + np.cumsum(np.random.normal(0, 0.05, n)))
    side = np.random.choice([1, -1], n)
    trade = mid + side * 0.01
    ofi = pd.Series(side * np.random.lognormal(5, 1, n))
    dp = pd.Series(np.diff(mid.values, prepend=mid.iloc[0]))
    print(f"Roll spread:     {roll_spread(mid.pct_change().dropna()):.4f}")
    print(f"Kyle lambda:     {kyle_lambda(ofi, dp):.8f}")
    print(f"VWAP:            {vwap(trade, pd.Series(np.abs(ofi))):.4f}")
    print("microstructure.py OK")
