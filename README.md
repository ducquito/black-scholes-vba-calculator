# Black-Scholes Option Pricing Calculator (VBA)

An Excel VBA tool that prices European call and put options using the Black-Scholes model, and calculates the main Greeks (Delta, Gamma, Vega, Theta).

## Features
- Call and Put option pricing (Black-Scholes formula)
- Delta, Gamma, Vega, Theta calculations
- Built entirely with native Excel VBA functions

## How to Use
1. Download `BlackScholes.xlsm`
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

## Background
Built to strengthen my understanding of options pricing theory and VBA development, as part of preparing for internships in trading and derivatives.

## Files
- `BlackScholes.xlsm` — the Excel workbook with the calculator
- `BlackScholes_Code.bas` — the raw VBA source code (for viewing without opening Excel)
