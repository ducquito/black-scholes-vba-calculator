"""
Black-Scholes pricing and Greeks for European options.

This is a direct Python port of BlackScholes_Code.bas (the VBA module in the
Excel calculator), extended with an optional dividend yield q. Function names
map one-to-one:

    VBA            Python
    ----------     -----------
    CallPrice      call_price
    PutPrice       put_price
    CallDelta      call_delta
    PutDelta       put_delta
    OptGamma       gamma
    Vega           vega
    CallTheta      call_theta
    PutTheta       put_theta

Inputs (same as the spreadsheet, plus q):
    S      current stock price
    K      strike price
    T      time to expiry, in years
    r      risk-free rate, annual, continuously compounded (0.05 = 5%)
    sigma  volatility, annual (0.20 = 20%)
    q      dividend yield, annual, continuously compounded (default 0)

Dividends: a stock that pays dividends hands part of its value to
shareholders before the option expires, and the option holder doesn't get
that cash. The standard fix (Merton, 1973) treats the dividend as a steady
yield q and discounts the stock price by e^(-qT). With q = 0 every function
gives exactly the same answer as the VBA version.

Units match the VBA version: vega is per 1.00 (100 percentage points) change
in volatility, and theta is per year. Divide vega by 100 for "per 1 vol
point" and theta by 365 for "per calendar day".
"""

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


def _d1_d2(S, K, T, r, sigma, q):
    d1 = (np.log(S / K) + (r - q + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return d1, d2


# ---------------------------------------------------------------- prices

def call_price(S, K, T, r, sigma, q=0.0):
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def put_price(S, K, T, r, sigma, q=0.0):
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)


# ---------------------------------------------------------------- Greeks

def call_delta(S, K, T, r, sigma, q=0.0):
    d1, _ = _d1_d2(S, K, T, r, sigma, q)
    return np.exp(-q * T) * norm.cdf(d1)


def put_delta(S, K, T, r, sigma, q=0.0):
    d1, _ = _d1_d2(S, K, T, r, sigma, q)
    return np.exp(-q * T) * (norm.cdf(d1) - 1)


def gamma(S, K, T, r, sigma, q=0.0):
    d1, _ = _d1_d2(S, K, T, r, sigma, q)
    return np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))


def vega(S, K, T, r, sigma, q=0.0):
    d1, _ = _d1_d2(S, K, T, r, sigma, q)
    return S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T)


def call_theta(S, K, T, r, sigma, q=0.0):
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    return (-(S * np.exp(-q * T) * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
            - r * K * np.exp(-r * T) * norm.cdf(d2)
            + q * S * np.exp(-q * T) * norm.cdf(d1))


def put_theta(S, K, T, r, sigma, q=0.0):
    d1, d2 = _d1_d2(S, K, T, r, sigma, q)
    return (-(S * np.exp(-q * T) * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
            + r * K * np.exp(-r * T) * norm.cdf(-d2)
            - q * S * np.exp(-q * T) * norm.cdf(-d1))


# ---------------------------------------------------------------- implied volatility

def implied_vol(market_price, S, K, T, r, option_type="call", q=0.0, low=1e-4, high=5.0):
    """
    Find the volatility that makes the Black-Scholes price equal the market price.

    Black-Scholes has no closed-form inverse, so we search numerically with
    Brent's method: option prices rise steadily with volatility, so there is
    exactly one sigma in [low, high] that matches, if the price is valid at all.

    Returns NaN when no solution exists, e.g. a quote below the option's
    no-arbitrage minimum value (common with stale or very illiquid quotes).
    """
    pricer = call_price if option_type == "call" else put_price
    objective = lambda sigma: pricer(S, K, T, r, sigma, q) - market_price
    try:
        if objective(low) * objective(high) > 0:
            return np.nan  # no sign change, so no root in the interval
        return brentq(objective, low, high, xtol=1e-8)
    except (ValueError, RuntimeError):
        return np.nan


if __name__ == "__main__":
    # Sanity check against the worked example in the main README
    # (and the Excel calculator): S=42, K=40, T=0.5, r=0.10, sigma=0.20
    args = (42, 40, 0.5, 0.10, 0.20)
    print(f"Call price  {call_price(*args):.4f}   (README: ~4.76)")
    print(f"Put price   {put_price(*args):.4f}   (README: ~0.81)")
    print(f"Call delta  {call_delta(*args):.4f}   (README: ~0.78)")
    print(f"Gamma       {gamma(*args):.4f}   (README: ~0.05)")
    print(f"Vega        {vega(*args):.4f}")
    print(f"Call theta  {call_theta(*args):.4f}")
    print(f"Put theta   {put_theta(*args):.4f}")
    # Round trip: price an option at 20% vol, then recover 20% from the price
    print(f"IV round trip, call  {implied_vol(call_price(*args), 42, 40, 0.5, 0.10):.6f}   (expect 0.200000)")
    print(f"IV round trip, put   {implied_vol(put_price(*args), 42, 40, 0.5, 0.10, 'put'):.6f}   (expect 0.200000)")
    # Put-call parity with dividends: C - P = S e^(-qT) - K e^(-rT)
    q = 0.03
    lhs = call_price(*args, q) - put_price(*args, q)
    rhs = 42 * np.exp(-q * 0.5) - 40 * np.exp(-0.10 * 0.5)
    print(f"Put-call parity, q=3%  {lhs:.6f} vs {rhs:.6f}   (expect equal)")
