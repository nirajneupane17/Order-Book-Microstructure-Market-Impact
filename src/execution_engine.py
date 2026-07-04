"""
execution_engine.py
===================
Optimal execution and transaction cost analysis.
Implements Almgren-Chriss (2001) optimal liquidation,
VWAP/TWAP scheduling, and implementation shortfall measurement.

Author : Niraj Neupane | github.com/nirajneupane17
Series : Quant Trading Projects — Project 4 of 20
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from scipy.optimize import minimize


def almgren_chriss_trajectory(X: float, T: float, n: int,
                               sigma: float, eta: float,
                               gamma: float, risk_aversion: float = 1.0
                               ) -> np.ndarray:
    """
    Almgren-Chriss (2001) optimal execution trajectory.

    Minimises E[cost] + λ × Var[cost], where:
      - E[cost] = market impact cost (from trading fast)
      - Var[cost] = timing risk (from trading slow, price may move)
      - λ = risk_aversion parameter

    Parameters
    ----------
    X             : total shares to liquidate
    T             : total time to liquidate (days)
    n             : number of execution periods
    sigma         : daily price volatility (fraction)
    eta           : temporary impact coefficient
    gamma         : permanent impact coefficient
    risk_aversion : λ — higher = trade faster (less timing risk)

    Returns
    -------
    np.ndarray of shares to trade in each period
    """
    tau = T / n
    kappa = np.sqrt(risk_aversion * sigma**2 / eta)
    # Optimal remaining inventory at each time step
    t_vals = np.linspace(0, T, n + 1)
    x_vals = X * np.sinh(kappa * (T - t_vals)) / np.sinh(kappa * T)
    # Shares to trade each period
    trades = -np.diff(x_vals)
    return np.maximum(trades, 0)


def twap_schedule(total_shares: int, n_periods: int) -> np.ndarray:
    """TWAP: equal shares per period."""
    base = total_shares // n_periods
    remainder = total_shares % n_periods
    schedule = np.full(n_periods, base)
    schedule[:remainder] += 1
    return schedule


def vwap_schedule(total_shares: int,
                   volume_profile: np.ndarray) -> np.ndarray:
    """VWAP: allocate shares proportional to expected volume profile."""
    weights = volume_profile / volume_profile.sum()
    return (total_shares * weights).astype(int)


def market_impact_cost(shares: np.ndarray,
                        prices: np.ndarray,
                        eta: float) -> float:
    """
    Estimated market impact cost for a given execution schedule.
    Temporary impact model: impact = eta × (shares_per_period)^0.5
    Returns total cost in basis points.
    """
    impacts = eta * np.sqrt(np.maximum(shares, 0))
    dollar_impact = (impacts * prices).sum()
    total_value = (shares * prices).sum()
    return float(dollar_impact / total_value * 10000) if total_value > 0 else 0


def timing_risk(schedule: np.ndarray, sigma: float,
                 tau: float) -> float:
    """
    Timing risk = variance of return over holding period.
    Higher for passive strategies that hold position longer.
    Returns risk in basis points (annualised vol × sqrt(time)).
    """
    n = len(schedule)
    remaining = np.cumsum(schedule[::-1])[::-1]
    variance = (sigma**2 * tau * (remaining**2)).sum()
    return float(np.sqrt(variance) * 10000)


def execution_cost_breakdown(exec_df: pd.DataFrame) -> pd.DataFrame:
    """
    Full execution cost breakdown per stock:
    spread cost + market impact + timing risk + total.
    """
    rows = []
    for stock in exec_df['stock'].unique():
        d = exec_df[exec_df['stock'] == stock]
        spread = d['spread_cost_bps'].mean()
        slippage = d['vwap_vs_twap_bps'].abs().mean()
        rows.append({'stock': stock, 'spread_bps': round(spread, 2),
            'slippage_bps': round(slippage, 2),
            'total_bps': round(spread + slippage, 2)})
    return pd.DataFrame(rows)


if __name__ == '__main__':
    traj = almgren_chriss_trajectory(X=10000, T=1.0, n=26,
                                      sigma=0.015, eta=0.001,
                                      gamma=0.0001, risk_aversion=2.0)
    print(f"AC Trajectory: {len(traj)} slices, total={traj.sum():.0f}")
    twap_s = twap_schedule(10000, 26)
    print(f"TWAP Schedule: {twap_s[:5]}...")
    print("execution_engine.py OK")
