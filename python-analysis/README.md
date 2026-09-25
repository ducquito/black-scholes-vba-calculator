# Python Extension: Testing Black-Scholes Against Real Market Prices

The Excel calculator in this repo prices options from inputs I type in. This folder asks a harder question: **how well does the model match what traders actually pay?**

It ports the same Black-Scholes formulas to Python, adds dividends, feeds the model real Apple (AAPL) stock and option data, and compares its prices to live market quotes for both calls and puts.

## Key ideas (in plain English)

- **Volatility** measures how much a stock tends to move. It is the only Black-Scholes input you can't look up directly, so it's the one that matters most.
- **Historical volatility** looks backward: how much did the stock actually move over the past year?
- **Implied volatility** looks forward: working the formula in reverse from the market price tells you how much movement traders are *expecting*. If implied volatility is above historical, the market expects a bumpier ride than the past year; if it's below, a calmer one.
- **Dividends**: when a company pays a dividend, part of the stock's value goes to shareholders as cash, and the option holder doesn't receive it. The model accounts for this by treating the dividend as a steady yield that is subtracted from the stock's expected growth.
- **Volatility skew**: if Black-Scholes were a perfect description of markets, every strike price would imply the same volatility. In reality, it doesn't. Traders pay extra for protection against sharp drops, so lower strikes carry higher implied volatility.

## Results (AAPL, market close on 24 Sep 2026)

| | |
|---|---|
| Stock price | $335.92 |
| Option expiry | 23 Oct 2026 (29 days) |
| Risk-free rate | 4.07% (13-week US T-bill) |
| Dividend yield | 0.32% (last 12 months of payments) |
| Historical volatility, 1 year | **24.6%** |
| Historical volatility, last 30 days | 20.3% |
| Implied volatility, at-the-money calls / puts | **22.9% / 22.1%** |

**What this shows:**

1. **The model is close, but not exact.** Using historical volatility, Black-Scholes priced 20 calls within an average of **$0.52** per share of the market, and 18 puts within **$0.48**.
2. **The market expects a calmer month than the past year.** At-the-money implied volatility (about 22.5%) is below the 1-year historical figure (24.6%), but above the last 30 days (20.3%). Traders expect somewhat more movement than the recent quiet stretch, but less than the full past year, which included several large swings.
3. **Calls and puts agree.** Near the stock price, calls and puts imply almost the same volatility (22.9% vs 22.1%). This is expected: a call and a put are linked by a fixed relationship (put-call parity), so they should tell the same story.
4. **A clear skew.** Out-of-the-money puts (the "crash insurance") imply about 30% volatility at the $290 strike, sloping down to about 22% near the stock price. This is the best-known way the real market departs from the model's assumption of a single, constant volatility.

Market data changes every day. `history.csv` keeps one summary row per trading day, so results from different days can be compared.

![Price history](plots/1_price_history.png)
![Model vs market](plots/2_theoretical_vs_market.png)
![Historical vs implied volatility](plots/3_historical_vs_implied_vol.png)
![Volatility skew](plots/4_volatility_skew.png)

**Reading the skew chart:** the left end of the blue line and the right end of the green line are *deep in-the-money* options. Few of them trade, so their quotes are wide and less reliable, and a small price error turns into a large volatility error. Traders read the skew from out-of-the-money options instead: puts below the stock price, calls above it.

## Files

| File | What it does |
|---|---|
| `black_scholes.py` | Pricing formulas and Greeks, ported one-to-one from `BlackScholes_Code.bas`, with an optional dividend yield and an implied-volatility solver. Run it directly to check it against the Excel example (call = 4.76, put = 0.81). |
| `analysis.py` | Downloads the data, runs the comparison for calls and puts, prints a results table, and saves the charts and CSV files. |
| `results.csv` | Every option analyzed on the latest run. |
| `history.csv` | One summary row per trading day (prices, volatilities, pricing error). |

## How to run

```bash
pip install -r requirements.txt
python black_scholes.py     # check against the Excel calculator
python analysis.py          # AAPL by default
python analysis.py MSFT     # or any other ticker with listed options
```

Run it after the US market closes (4pm New York time) so the stock price and option quotes come from the same moment. Once `history.csv` has two or more days, the script also draws `plots/5_daily_history.png`.

## Method notes

- **Market price** is the midpoint between the bid and ask prices. The last trade price can be hours old for less active strikes.
- **Option selection:** the expiry closest to 30 days out, with strikes within ±15% of the stock price that have open interest.
- **Implied volatility** is found with Brent's method (`scipy.optimize.brentq`). There is no formula that runs Black-Scholes in reverse, so the solver searches for the volatility that reproduces the market price.
- **Dividends** use the Merton (1973) extension of Black-Scholes, which treats dividends as a continuous yield. With a zero yield it gives exactly the same numbers as the Excel calculator.
- **Cross-check:** Yahoo Finance publishes its own implied volatility figures (the `iv_yahoo` column in `results.csv`). For puts they match ours closely. For calls they run a few points higher, especially at low strikes. Yahoo doesn't publish how it calculates them, so they're a rough sanity check only.
- **American vs European:** US stock options can be exercised early (American style), while Black-Scholes assumes they can't (European style). For 1-month options on a low-dividend stock the difference is small, but it helps explain why deep in-the-money puts, where early exercise is most valuable, price slightly above the model.
