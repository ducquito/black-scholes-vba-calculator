"""
Validate the Black-Scholes model against real market data.

Steps:
  1. Download one year of daily stock prices and dividends (yfinance, free)
  2. Estimate historical volatility and dividend yield from that data
  3. Download a real option chain (calls and puts) for an expiry ~1 month out
  4. Price each option with Black-Scholes using historical volatility
     and compare to what the market is actually charging
  5. Back out the implied volatility from each market price
  6. Save charts to plots/, today's option table to results.csv, and append
     one summary row per trading day to history.csv

Usage:
    python analysis.py            # defaults to AAPL
    python analysis.py MSFT       # any optionable ticker
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # write PNG files, no window needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

from black_scholes import call_price, put_price, call_delta, put_delta, implied_vol

TICKER = sys.argv[1].upper() if len(sys.argv) > 1 else "AAPL"
TARGET_DAYS = 30          # pick the expiry closest to ~1 month out
MONEYNESS_BAND = 0.15     # keep strikes within +/-15% of the stock price
FALLBACK_RATE = 0.045     # used only if the T-bill download fails
TRADING_DAYS = 252

OUT_DIR = Path(__file__).parent
PLOT_DIR = OUT_DIR / "plots"
HISTORY_FILE = OUT_DIR / "history.csv"

PRICERS = {"call": (call_price, call_delta), "put": (put_price, put_delta)}

# Chart colors (light theme, colorblind-checked categorical order)
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK_2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"


# ---------------------------------------------------------------- data

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


def market_date(stock):
    """Date of the latest trading session, so re-runs on the same day overwrite one row."""
    try:
        return datetime.fromtimestamp(stock.info["regularMarketTime"]).date()
    except Exception:
        return date.today()


def risk_free_rate():
    """13-week US T-bill yield (Yahoo symbol ^IRX, quoted in percent)."""
    try:
        irx = yf.Ticker("^IRX").history(period="5d")["Close"].dropna()
        return float(irx.iloc[-1]) / 100, "13-week T-bill (^IRX)"
    except Exception:
        return FALLBACK_RATE, "fixed estimate"


def dividend_yield(stock, S):
    """
    Trailing 12-month dividends divided by the stock price, e.g. four
    quarterly payments of $0.27 on a $336 stock is about 0.32% a year.
    """
    divs = stock.dividends
    if divs.empty:
        return 0.0
    cutoff = pd.Timestamp.now(tz=divs.index.tz) - timedelta(days=365)
    return float(divs[divs.index > cutoff].sum()) / S


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


def analyze_chain(chain, kind, S, T, r, q, hv):
    """Model price, pricing error and implied vol for each liquid strike."""
    pricer, delta = PRICERS[kind]

    # Keep liquid strikes near the current price; far out-of-the-money and
    # deep in-the-money quotes are sparse and noisy
    df = chain[(chain["strike"] >= S * (1 - MONEYNESS_BAND)) &
               (chain["strike"] <= S * (1 + MONEYNESS_BAND)) &
               (chain["openInterest"].fillna(0) > 0)].copy()
    if df.empty:
        return df
    df[["market", "price_source"]] = df.apply(market_price, axis=1, result_type="expand")
    df = df[df["market"] > 0]

    df["bs_hist_vol"] = pricer(S, df["strike"], T, r, hv, q)
    df["diff"] = df["market"] - df["bs_hist_vol"]
    df["delta"] = delta(S, df["strike"], T, r, hv, q)
    df["iv_solved"] = [implied_vol(p, S, k, T, r, kind, q)
                       for p, k in zip(df["market"], df["strike"])]
    df["iv_yahoo"] = df["impliedVolatility"]
    df.insert(0, "type", kind)
    return df[["type", "strike", "market", "price_source", "bs_hist_vol", "diff", "delta",
               "iv_solved", "iv_yahoo", "volume", "openInterest"]].reset_index(drop=True)


def atm_iv(df, S):
    """At-the-money implied vol: average of the two strikes closest to the stock price."""
    return df.iloc[(df["strike"] - S).abs().argsort()[:2]]["iv_solved"].mean()


def log_history(row):
    """One row per trading day; re-running on the same day replaces that day's row."""
    new = pd.DataFrame([row])
    if HISTORY_FILE.exists():
        old = pd.read_csv(HISTORY_FILE, dtype={"date": str})
        old = old[~((old["date"] == row["date"]) & (old["ticker"] == row["ticker"]))]
        new = pd.concat([old, new], ignore_index=True).sort_values(["ticker", "date"])
    new.to_csv(HISTORY_FILE, index=False, float_format="%.6f")


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


def mark_stock_price(ax, S):
    ax.axvline(S, color=MUTED, linewidth=1, linestyle="--")
    ax.text(S, ax.get_ylim()[1], f" stock ${S:.2f}", color=INK_2, va="top", fontsize=9)


def plot_price_history(hist):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(hist.index, hist["Close"], color=BLUE, linewidth=2)
    style_axes(ax, f"{TICKER} closing price, last 12 months", "", "Price ($)")
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "1_price_history.png", dpi=150)
    plt.close(fig)


def plot_theoretical_vs_market(calls, puts, S, hv):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, df, name in ((axes[0], calls, "Calls"), (axes[1], puts, "Puts")):
        ax.plot(df["strike"], df["market"], color=BLUE, linewidth=2, marker="o",
                markersize=4, label="Market price")
        ax.plot(df["strike"], df["bs_hist_vol"], color=ORANGE, linewidth=2, marker="o",
                markersize=4, label=f"Black-Scholes, historical vol ({hv:.1%})")
        style_axes(ax, f"{TICKER} {name.lower()}: model vs market", "Strike ($)",
                   "Option price ($)" if name == "Calls" else "")
        mark_stock_price(ax, S)
    axes[0].legend(frameon=False, loc="upper right", bbox_to_anchor=(1, 0.85))
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


def plot_vol_skew(calls, puts, S, hv):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(calls["strike"], calls["iv_solved"], color=BLUE, linewidth=2, marker="o",
            markersize=4, label="Implied vol, calls")
    ax.plot(puts["strike"], puts["iv_solved"], color=AQUA, linewidth=2, marker="o",
            markersize=4, label="Implied vol, puts")
    ax.axhline(hv, color=ORANGE, linewidth=2, label=f"Historical vol, 1 year ({hv:.1%})")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    style_axes(ax, f"{TICKER} implied volatility by strike (the 'skew')",
               "Strike ($)", "Annualized volatility")
    mark_stock_price(ax, S)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "4_volatility_skew.png", dpi=150)
    plt.close(fig)


def plot_history():
    """Implied vs historical vol across the days logged so far (needs 2+ days)."""
    hist = pd.read_csv(HISTORY_FILE, parse_dates=["date"])
    hist = hist[hist["ticker"] == TICKER]
    if len(hist) < 2:
        return
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(hist["date"], hist["atm_iv_call"], color=BLUE, linewidth=2, marker="o",
            markersize=6, label="Implied vol, ATM calls")
    ax.plot(hist["date"], hist["atm_iv_put"], color=AQUA, linewidth=2, marker="o",
            markersize=6, label="Implied vol, ATM puts")
    ax.plot(hist["date"], hist["hv_1y"], color=ORANGE, linewidth=2, marker="o",
            markersize=6, label="Historical vol, 1 year")
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %d"))
    ax.set_xticks(hist["date"])
    style_axes(ax, f"{TICKER} implied vs historical volatility, day by day", "",
               "Annualized volatility")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(PLOT_DIR / "5_daily_history.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- main

def main():
    PLOT_DIR.mkdir(exist_ok=True)
    today = date.today()
    stock = yf.Ticker(TICKER)

    # 1. Price history and current price. Yahoo sometimes returns today's row
    # with a blank close while the day's bar is still being built, so drop
    # incomplete rows
    hist = stock.history(period="1y").dropna(subset=["Close"])
    S = current_price(stock, hist)

    # 2. Historical volatility (full year and last 30 trading days) and dividends
    hv_1y = historical_volatility(hist["Close"])
    hv_30d = historical_volatility(hist["Close"], window=30)
    q = dividend_yield(stock, S)
    r, r_source = risk_free_rate()

    # 3. Option chain for the expiry closest to one month out
    expiry, days = pick_expiry(stock.options, today)
    T = days / 365
    chain = stock.option_chain(expiry)

    # 4-5. Model vs market and implied vol, for calls and puts
    calls = analyze_chain(chain.calls, "call", S, T, r, q, hv_1y)
    puts = analyze_chain(chain.puts, "put", S, T, r, q, hv_1y)
    if calls.empty or puts.empty:
        sys.exit(f"No liquid {TICKER} options near ${S:.2f} for {expiry}.")

    iv_call, iv_put = atm_iv(calls, S), atm_iv(puts, S)
    err_call, err_put = calls["diff"].abs().mean(), puts["diff"].abs().mean()

    # ---------------------------------------------------------------- report
    pd.set_option("display.width", 140)
    print(f"\n{TICKER} Black-Scholes validation   (run {today})")
    print("=" * 60)
    print(f"Stock price             ${S:,.2f}")
    print(f"Dividend yield          {q:.2%}  (trailing 12 months)")
    print(f"Risk-free rate          {r:.2%}  ({r_source})")
    print(f"Expiry                  {expiry}  ({days} days, T = {T:.4f} yr)")
    print(f"Historical vol, 1 year  {hv_1y:.2%}")
    print(f"Historical vol, 30 days {hv_30d:.2%}")
    print(f"ATM implied vol, calls  {iv_call:.2%}")
    print(f"ATM implied vol, puts   {iv_put:.2%}")
    print(f"Mean |market - model|   calls ${err_call:.2f}, puts ${err_put:.2f} per share")
    fmt = {"market": "{:.2f}".format, "bs_hist_vol": "{:.2f}".format, "diff": "{:+.2f}".format,
           "delta": "{:+.2f}".format, "iv_solved": "{:.1%}".format, "iv_yahoo": "{:.1%}".format}
    for df in (calls, puts):
        print()
        print(df.drop(columns="type").to_string(formatters=fmt))

    avg_iv = (iv_call + iv_put) / 2
    view = "MORE" if avg_iv > hv_1y else "LESS"
    print(f"\nFinding: {TICKER} at-the-money implied volatility is {avg_iv:.1%} "
          f"(calls {iv_call:.1%}, puts {iv_put:.1%}) vs {hv_1y:.1%} historical (1-year), "
          f"so the market is pricing {view} future movement than the stock showed "
          f"over the past year.")

    pd.concat([calls, puts]).to_csv(OUT_DIR / "results.csv", index=False)
    log_history({
        "date": market_date(stock).isoformat(), "ticker": TICKER, "stock_price": S,
        "dividend_yield": q, "risk_free_rate": r, "expiry": expiry, "days_to_expiry": days,
        "hv_1y": hv_1y, "hv_30d": hv_30d, "atm_iv_call": iv_call, "atm_iv_put": iv_put,
        "mean_abs_error_call": err_call, "mean_abs_error_put": err_put,
    })

    plot_price_history(hist)
    plot_theoretical_vs_market(calls, puts, S, hv_1y)
    plot_vol_comparison([("Historical\n(1 year)", hv_1y),
                         ("Historical\n(last 30 days)", hv_30d),
                         ("Implied, ATM\ncalls", iv_call),
                         ("Implied, ATM\nputs", iv_put)])
    plot_vol_skew(calls, puts, S, hv_1y)
    plot_history()
    print(f"\nCharts saved to {PLOT_DIR}, daily log in {HISTORY_FILE.name}")


if __name__ == "__main__":
    main()
