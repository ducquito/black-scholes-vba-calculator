"""
Validate the Black-Scholes model against real market data.

Steps:
  1. Download one year of daily stock prices (yfinance, free)
  2. Estimate historical volatility from those prices
  3. Download a real option chain for an expiry ~1 month out
  4. Price each call with Black-Scholes using historical volatility
     and compare to what the market is actually charging
  5. Back out the implied volatility from each market price
  6. Save charts to plots/ and a results table to results.csv

Usage:
    python analysis.py            # defaults to AAPL
    python analysis.py MSFT       # any optionable ticker
"""

import sys
from datetime import date, datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # write PNG files, no window needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

from black_scholes import call_price, call_delta, implied_vol

TICKER = sys.argv[1].upper() if len(sys.argv) > 1 else "AAPL"
TARGET_DAYS = 30          # pick the expiry closest to ~1 month out
MONEYNESS_BAND = 0.15     # keep strikes within +/-15% of the stock price
FALLBACK_RATE = 0.045     # used only if the T-bill download fails
TRADING_DAYS = 252

OUT_DIR = Path(__file__).parent
PLOT_DIR = OUT_DIR / "plots"

# Chart colors (light theme, colorblind-checked categorical order)
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK_2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"


# ---------------------------------------------------------------- data

def risk_free_rate():
    """13-week US T-bill yield (Yahoo symbol ^IRX, quoted in percent)."""
    try:
        irx = yf.Ticker("^IRX").history(period="5d")["Close"].dropna()
        return float(irx.iloc[-1]) / 100, "13-week T-bill (^IRX)"
    except Exception:
        return FALLBACK_RATE, "fixed estimate"


def current_price(stock, hist):
    """
    Latest traded price. Option quotes are live, so the stock price must be
    live too: pricing today's options off yesterday's close skews the results.
    """
    try:
        price = float(stock.fast_info["lastPrice"])
        if price > 0:
            return price
    except Exception:
        pass
    return float(hist["Close"].iloc[-1])


def historical_volatility(close, window=None):
    """Annualized standard deviation of daily log returns."""
    returns = np.log(close / close.shift(1)).dropna()
    if window:
        returns = returns.iloc[-window:]
    return returns.std() * np.sqrt(TRADING_DAYS)


def pick_expiry(expirations, today):
    """Expiry whose distance from today is closest to TARGET_DAYS."""
    days = [(datetime.strptime(e, "%Y-%m-%d").date() - today).days for e in expirations]
    best = min(range(len(days)), key=lambda i: abs(days[i] - TARGET_DAYS))
    return expirations[best], days[best]


def market_price(row):
    """
    Use the bid/ask midpoint when there is a live two-sided quote; it reflects
    the market right now. Fall back to the last trade, which can be hours or
    days old for thinly traded strikes.
    """
    if row["bid"] > 0 and row["ask"] > 0:
        return (row["bid"] + row["ask"]) / 2, "mid"
    return row["lastPrice"], "last"


# ---------------------------------------------------------------- charts

def style_axes(ax, title, xlabel, ylabel):
    ax.set_title(title, loc="left", fontsize=12, color=INK, pad=12)
    ax.set_xlabel(xlabel, color=INK_2)
    ax.set_ylabel(ylabel, color=INK_2)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors=MUTED)


def plot_price_history(hist):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(hist.index, hist["Close"], color=BLUE, linewidth=2)
    style_axes(ax, f"{TICKER} closing price, last 12 months", "", "Price ($)")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "1_price_history.png", dpi=150)
    plt.close(fig)


def plot_theoretical_vs_market(df, S, hv):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(df["strike"], df["market"], color=BLUE, linewidth=2, marker="o",
            markersize=4, label="Market price")
    ax.plot(df["strike"], df["bs_hist_vol"], color=ORANGE, linewidth=2, marker="o",
            markersize=4, label=f"Black-Scholes with historical vol ({hv:.1%})")
    ax.axvline(S, color=MUTED, linewidth=1, linestyle="--")
    ax.text(S, ax.get_ylim()[1], f" stock ${S:.2f}", color=INK_2, va="top", fontsize=9)
    style_axes(ax, f"{TICKER} call prices: model vs market", "Strike ($)", "Call price ($)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "2_theoretical_vs_market.png", dpi=150)
    plt.close(fig)


def plot_vol_comparison(vols):
    labels, values = zip(*vols)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.bar(labels, values, color=BLUE, width=0.55)
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v, f"{v:.1%}", ha="center",
                va="bottom", color=INK, fontsize=10)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    style_axes(ax, f"{TICKER} volatility: what happened vs what the market expects",
               "", "Annualized volatility")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "3_historical_vs_implied_vol.png", dpi=150)
    plt.close(fig)


def plot_vol_skew(df, S, hv):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(df["strike"], df["iv_solved"], color=BLUE, linewidth=2, marker="o",
            markersize=4, label="Implied vol (our solver)")
    ax.plot(df["strike"], df["iv_yahoo"], color=AQUA, linewidth=2, linestyle=":",
            label="Implied vol (Yahoo Finance)")
    ax.axhline(hv, color=ORANGE, linewidth=2, label=f"Historical vol, 1 year ({hv:.1%})")
    ax.axvline(S, color=MUTED, linewidth=1, linestyle="--")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    style_axes(ax, f"{TICKER} implied volatility by strike (the 'skew')",
               "Strike ($)", "Annualized volatility")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "4_volatility_skew.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- main

def main():
    PLOT_DIR.mkdir(exist_ok=True)
    today = date.today()
    stock = yf.Ticker(TICKER)

    # 1. Price history and current price
    # Yahoo sometimes returns today's row with a blank close while the day's
    # bar is still being built, so drop incomplete rows
    hist = stock.history(period="1y").dropna(subset=["Close"])
    S = current_price(stock, hist)

    # 2. Historical volatility: full year, and last 30 trading days
    hv_1y = historical_volatility(hist["Close"])
    hv_30d = historical_volatility(hist["Close"], window=30)

    r, r_source = risk_free_rate()

    # 3. Option chain for the expiry closest to one month out
    expiry, days = pick_expiry(stock.options, today)
    T = days / 365
    calls = stock.option_chain(expiry).calls

    # Keep liquid strikes near the current price; far out-of-the-money and
    # deep in-the-money quotes are sparse and noisy
    calls = calls[(calls["strike"] >= S * (1 - MONEYNESS_BAND)) &
                  (calls["strike"] <= S * (1 + MONEYNESS_BAND)) &
                  (calls["openInterest"].fillna(0) > 0)].copy()
    if calls.empty:
        sys.exit(f"No liquid {TICKER} calls near ${S:.2f} for {expiry}.")
    calls[["market", "price_source"]] = calls.apply(market_price, axis=1, result_type="expand")
    calls = calls[calls["market"] > 0]

    # 4. Theoretical price using historical volatility
    calls["bs_hist_vol"] = call_price(S, calls["strike"], T, r, hv_1y)
    calls["diff"] = calls["market"] - calls["bs_hist_vol"]
    calls["delta"] = call_delta(S, calls["strike"], T, r, hv_1y)

    # 5. Implied volatility from each market price, plus Yahoo's value as a cross-check
    calls["iv_solved"] = [implied_vol(p, S, k, T, r) for p, k in zip(calls["market"], calls["strike"])]
    calls["iv_yahoo"] = calls["impliedVolatility"]

    df = calls[["strike", "market", "price_source", "bs_hist_vol", "diff", "delta",
                "iv_solved", "iv_yahoo", "volume", "openInterest"]].reset_index(drop=True)

    # At-the-money implied vol: average of the two strikes closest to the stock price
    atm = df.iloc[(df["strike"] - S).abs().argsort()[:2]]
    atm_iv = atm["iv_solved"].mean()
    atm_iv_yahoo = atm["iv_yahoo"].mean()

    # ---------------------------------------------------------------- report
    pd.set_option("display.width", 140)
    print(f"\n{TICKER} Black-Scholes validation   (run {today})")
    print("=" * 60)
    print(f"Stock price             ${S:,.2f}")
    print(f"Risk-free rate          {r:.2%}  ({r_source})")
    print(f"Expiry                  {expiry}  ({days} days, T = {T:.4f} yr)")
    print(f"Historical vol, 1 year  {hv_1y:.2%}")
    print(f"Historical vol, 30 days {hv_30d:.2%}")
    print(f"ATM implied vol (ours)  {atm_iv:.2%}")
    print(f"ATM implied vol (Yahoo) {atm_iv_yahoo:.2%}")
    print(f"Mean |market - model|   ${df['diff'].abs().mean():.2f} per share "
          f"across {len(df)} strikes")
    print()
    fmt = {"market": "{:.2f}".format, "bs_hist_vol": "{:.2f}".format, "diff": "{:+.2f}".format,
           "delta": "{:.2f}".format, "iv_solved": "{:.1%}".format, "iv_yahoo": "{:.1%}".format}
    print(df.to_string(formatters=fmt))

    gap = atm_iv - hv_1y
    view = "MORE" if gap > 0 else "LESS"
    print(f"\nFinding: {TICKER} at-the-money implied volatility is {atm_iv:.1%} vs "
          f"{hv_1y:.1%} historical (1-year), so the market is pricing {view} "
          f"future movement than the stock showed over the past year.")

    df.to_csv(OUT_DIR / "results.csv", index=False)

    plot_price_history(hist)
    plot_theoretical_vs_market(df, S, hv_1y)
    plot_vol_comparison([("Historical\n(1 year)", hv_1y),
                         ("Historical\n(last 30 days)", hv_30d),
                         ("Implied, ATM\n(our solver)", atm_iv),
                         ("Implied, ATM\n(Yahoo)", atm_iv_yahoo)])
    plot_vol_skew(df, S, hv_1y)
    print(f"\nCharts saved to {PLOT_DIR}")


if __name__ == "__main__":
    main()
