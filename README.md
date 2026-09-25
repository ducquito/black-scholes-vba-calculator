# Black-Scholes Option Pricing Calculator (VBA)

An Excel VBA tool that prices European call and put options using the Black-Scholes model, and calculates the main Greeks (Delta, Gamma, Vega, Theta).

## Features
- Call and Put option pricing (Black-Scholes formula)
- Delta, Gamma, Vega, Theta calculations
- Built entirely with native Excel VBA functions

## How to Use
1. Download `VBA Black-Scholes project.xlsm`
2. Open the file and enter the five input parameters:
   - Stock Price (S)
   - Strike Price (K)
   - Time to Expiry in years (T)
   - Risk-Free Rate (r)
   - Volatility (sigma)
3. The calculator automatically outputs:
   - Call/Put Option Price
   - Call/Put Delta
   - Gamma
   - Vega
   - Call/Put Theta

## Example
Using S=42, K=40, T=0.5, r=0.1, sigma=0.2:
- Call Price ≈ 4.76
- Put Price ≈ 0.81
- Call Delta ≈ 0.78
- Gamma ≈ 0.05

## Extensions: Testing the Model on Real Market Data (Python)

The [`python-analysis/`](python-analysis/) folder ports the same formulas to Python, adds dividends, and tests the model against live Apple (AAPL) call and put prices from Yahoo Finance. It includes a numerical solver that backs out *implied volatility*: the volatility traders are pricing in, rather than the volatility the stock has shown in the past.

**Finding (24 Sep 2026):** AAPL's at-the-money implied volatility is about **22.5%** (calls 22.9%, puts 22.1%) vs **24.6%** historical (1-year), suggesting the market expects **less** movement over the next month than the stock showed over the past year. Using historical volatility, the model priced 20 calls and 18 puts within an average of about $0.50 of the market. Implied volatility also rises steadily for lower strikes (a "volatility skew"), a well-known way real markets depart from the model's constant-volatility assumption.

See [`python-analysis/README.md`](python-analysis/README.md) for the charts and method.

## Background
Built to strengthen my understanding of options pricing theory and VBA development, as part of preparing for internships in trading and derivatives. The Python extension adds real-market validation.

## Files
- `VBA Black-Scholes project.xlsm` — the Excel workbook with the calculator
- `BlackScholes_Code.bas` — the raw VBA source code (for viewing without opening Excel)
- `python-analysis/` — Python port, market data analysis and charts
