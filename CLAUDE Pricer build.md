# Black-Scholes Option Pricer

## Project Overview
A Python-based European option pricer using the Black-Scholes model.
The goal is to produce clean, readable, and financially accurate code
that can be explained line by line in an interview context.

---

## Objectives
- Price European call and put options using Black-Scholes
- Compute the main Greeks: delta, gamma, vega, theta, rho
- Add an implied volatility solver (given a market price, back out vol)
- Generate payoff diagrams and Greek sensitivity plots
- Output results as structured JSON/CSV for downstream consumption by an analysis agent

---

## Greeks Conventions (strictly enforced)
These conventions must be applied consistently across all functions and documented in every docstring.

**Theta:**
- Return the **mathematically correct negative value** for a long option (e.g. -0.052)
- This represents the change in option value per one calendar day passing
- Scale by dividing by 365 (not 252) to express as daily decay
- Do NOT flip the sign to a positive "daily cost" — document the sign explicitly in the docstring

**Vega:**
- Return sensitivity per **1% move in implied volatility** (i.e. vol goes from 0.20 to 0.21)
- This means dividing the raw BS vega by 100
- The raw BS formula gives sensitivity per 1-point move in vol — we do not use that convention
- Document in the docstring: "vega expressed per 1% change in vol (market convention)"

**Delta:** Standard — change in option price per 1-unit move in spot. Positive for calls, negative for puts.

**Gamma:** Standard — always positive for long options regardless of call or put.

**Rho:** Change in option price per 1% move in the risk-free rate (divide raw rho by 100).

---

## Tech Stack
- **Language:** Python 3.11+
- **Math/Finance:** numpy, scipy (norm.cdf, norm.pdf from scipy.stats)
- **Plotting:** matplotlib
- **Data I/O:** json, csv (standard library preferred, pandas only if necessary)
- **No external pricing libraries** (e.g. no QuantLib) — all financial logic must be implemented from scratch

---

## Project Structure
```
bs-pricer/
├── CLAUDE.md
├── README.md
├── pricer/
│   ├── __init__.py
│   ├── black_scholes.py      # Core BS formula and Greeks
│   ├── implied_vol.py        # IV solver using Brent's method
│   └── visualise.py          # Payoff diagrams and Greek plots
├── outputs/
│   ├── results.json          # Pricing output for the analysis agent
│   └── plots/                # Saved figures
├── tests/
│   └── test_black_scholes.py # Unit tests with known reference values
└── main.py                   # Entry point: takes inputs, runs pricer, saves outputs
```

---

## Code Conventions
- **Readability over cleverness** — this code will be read by finance recruiters and explained in interviews
- Every function must have a docstring explaining the financial meaning of each parameter, not just its type
- Variable names must be financially meaningful: use `spot`, `strike`, `vol`, `rate`, `time_to_expiry` — never `S`, `K`, `sigma`, `r`, `T` as standalone variable names (use them only inside formulas where convention demands it)
- All functions must include input validation with clear error messages (e.g. negative vol, zero spot)
- No magic numbers — define constants with names and comments explaining their financial rationale

---

## Financial Logic Rules
- Assume **continuous compounding** for the risk-free rate
- Assume **no dividends** in the base implementation (note where this assumption is made)
- Time to expiry is expressed in **years** (e.e. 0.25 = 3 months)
- Volatility is expressed as an **annualised decimal** (e.g. 0.20 = 20%)
- The model prices **European options only** — document this clearly wherever relevant
- **Dividends:** The base implementation assumes no dividends. The Merton (1973) extension handles continuous dividend yield q by replacing spot S with S×e^{-q×T} in the d1/d2 formulas. Add a comment at the exact line where spot is used in d1 noting: "To extend for continuous dividend yield q, replace spot with spot × exp(-q × time_to_expiry) here." Do not implement it — just annotate it.
- When computing implied vol, use **Brent's method** via scipy.optimize.brentq with bounds [1e-6, 10.0]

---

## Testing
All tests must pass before considering any module complete. Tests must validate against known external benchmarks, not just internal consistency.

**Reference benchmark (hardcode this in tests):**
Given: spot=100, strike=100, vol=0.20, rate=0.05, time_to_expiry=1.0
- Call price ≈ 10.4506
- Put price ≈ 5.5735 (verify via put-call parity: C - P = spot - strike × e^{-r×T})
- Delta (call) ≈ 0.6368
- Delta (put) ≈ -0.3632
- Gamma ≈ 0.0187
- Vega (per 1%) ≈ 0.3752
- Theta (call, per day) ≈ -0.0176
- Rho (call, per 1%) ≈ 0.5323

**Edge cases to test:**
- At-the-money: delta should be close to 0.5 for calls
- Very short expiry (time=0.01): deep ITM option price ≈ intrinsic value
- Very long expiry (time=5.0): sanity check Greeks remain bounded
- Deep OTM: price should approach 0, delta should approach 0
- Deep ITM: call delta should approach 1, put delta should approach -1
- Put-call parity must hold for all test cases: C - P = spot - strike × e^{-r×T}

---

## Output Format
Results saved to `outputs/results.json` should follow this structure:
```json
{
  "inputs": {
    "spot": 100,
    "strike": 105,
    "vol": 0.20,
    "rate": 0.05,
    "time_to_expiry": 0.25,
    "option_type": "call"
  },
  "pricing": {
    "price": 2.34,
    "intrinsic_value": 0.00,
    "time_value": 2.34
  },
  "greeks": {
    "delta": 0.38,
    "gamma": 0.047,
    "vega": 0.096,
    "theta": -0.052,
    "rho": 0.038
  }
}
```

---

## Model Assumptions and Limitations
Add a docstring at the top of `black_scholes.py` listing these explicitly. Being able to articulate them is a baseline expectation in any derivatives interview.

**Assumptions the model makes:**
1. **Lognormal returns** — asset prices follow geometric Brownian motion; returns are normally distributed
2. **Constant volatility** — vol does not change over the life of the option (this is the model's most significant real-world failure)
3. **Constant risk-free rate** — the rate does not vary with time or market conditions
4. **No dividends** — the underlying pays no cash flows during the option's life (see Merton extension above)
5. **Frictionless markets** — no transaction costs, no bid-ask spread, no taxes
6. **Continuous trading** — you can rebalance your hedge at any instant

**Where these break down in practice:**
- Constant vol fails immediately — implied vol varies by strike (vol smile) and by expiry (term structure), which is why vol surfaces and smile models (SABR, SVI) exist
- Lognormal returns underestimate the probability of extreme moves — fat tails in real return distributions mean BS underprices deep OTM options
- Continuous trading is impossible — discrete hedging introduces slippage and gamma P&L

---

## What This Project Is Not
- Not a production trading system
- Not a vol surface calibration tool (yet)
- Not a Monte Carlo pricer (potential future extension)
- Not dependent on live market data feeds

---

## Future Extensions (do not build now)
- American option pricing via binomial tree
- Volatility surface and smile modelling
- Monte Carlo simulation for exotic payoffs
- Integration with the analysis agent that reads `outputs/results.json` and produces a written report
