/**
 * Black-Scholes library — JavaScript port of pricer/black_scholes.py
 * Conventions: theta per calendar day, vega & rho per 1% move.
 */

function normCDF(x) {
  const a1=0.254829592, a2=-0.284496736, a3=1.421413741, a4=-1.453152027, a5=1.061405429, p=0.3275911
  const sign = x < 0 ? -1 : 1
  const ax = Math.abs(x) / Math.SQRT2
  const t  = 1 / (1 + p * ax)
  const y  = 1 - (((((a5*t+a4)*t+a3)*t+a2)*t+a1)*t) * Math.exp(-ax*ax)
  return 0.5 * (1 + sign * y)
}

function normPDF(x) {
  return Math.exp(-0.5*x*x) / Math.sqrt(2*Math.PI)
}

function d1d2(spot, strike, vol, rate, T) {
  const sqrtT = Math.sqrt(T)
  const d1 = (Math.log(spot/strike) + (rate + 0.5*vol*vol)*T) / (vol*sqrtT)
  return [d1, d1 - vol*sqrtT]
}

export function bsPrice(spot, strike, vol, rate, T, type) {
  if (spot<=0||strike<=0||vol<=0||T<=0) return 0
  const [d1,d2] = d1d2(spot, strike, vol, rate, T)
  const disc = Math.exp(-rate*T)
  return type==='call'
    ? spot*normCDF(d1) - strike*disc*normCDF(d2)
    : strike*disc*normCDF(-d2) - spot*normCDF(-d1)
}

export function bsGreeks(spot, strike, vol, rate, T, type) {
  if (spot<=0||strike<=0||vol<=0||T<=0)
    return {delta:0,gamma:0,vega:0,theta:0,rho:0}
  const [d1,d2] = d1d2(spot, strike, vol, rate, T)
  const sqrtT = Math.sqrt(T)
  const disc  = Math.exp(-rate*T)
  const delta = type==='call' ? normCDF(d1) : normCDF(d1)-1
  const gamma = normPDF(d1) / (spot*vol*sqrtT)
  const vega  = spot*normPDF(d1)*sqrtT / 100
  const t1    = -(spot*normPDF(d1)*vol) / (2*sqrtT)
  const theta = type==='call'
    ? (t1 - rate*strike*disc*normCDF(d2))  / 365
    : (t1 + rate*strike*disc*normCDF(-d2)) / 365
  const rho = type==='call'
    ?  strike*T*disc*normCDF(d2)  / 100
    : -strike*T*disc*normCDF(-d2) / 100
  return {delta,gamma,vega,theta,rho}
}

export function impliedVol(marketPrice, spot, strike, rate, T, type) {
  if (marketPrice<=0) return null
  let lo=1e-6, hi=10.0
  for (let i=0;i<500;i++) {
    const mid = (lo+hi)/2
    const p   = bsPrice(spot, strike, mid, rate, T, type)
    if (Math.abs(p-marketPrice)<1e-7) return mid
    p < marketPrice ? (lo=mid) : (hi=mid)
  }
  return (lo+hi)/2
}
