import { useState, useMemo, useRef, useEffect } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { bsPrice, bsGreeks, impliedVol } from '../lib/blackScholes'
gsap.registerPlugin(ScrollTrigger)

// ── SVG line chart ────────────────────────────────────────────────────────
function LineChart({ datasets = [], width = 600, height = 160 }) {
  if (!datasets[0]?.data?.length) return null
  const allY = datasets.flatMap(d => d.data.map(p => p.y))
  const allX = datasets[0].data.map(p => p.x)
  const yMin = Math.min(0, ...allY), yMax = Math.max(...allY) * 1.05 || 1
  const xMin = Math.min(...allX),    xMax = Math.max(...allX)
  const sx = x => ((x-xMin)/(xMax-xMin)) * width
  const sy = y => height - ((y-yMin)/(yMax-yMin)) * height

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full" preserveAspectRatio="none">
      {yMin < 0 && (
        <line x1="0" x2={width} y1={sy(0)} y2={sy(0)} stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
      )}
      {datasets.map((ds, i) => {
        const pts = ds.data.map(p => `${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(' ')
        const base = sy(0).toFixed(1)
        return (
          <g key={i}>
            {ds.fill && (
              <polygon
                points={`${sx(xMin).toFixed(1)},${base} ${pts} ${sx(xMax).toFixed(1)},${base}`}
                fill={ds.fillColor || 'rgba(37,99,235,0.10)'}
              />
            )}
            <polyline
              points={pts} fill="none"
              stroke={ds.color || '#2563EB'}
              strokeWidth={ds.width || 1.5}
              strokeDasharray={ds.dash ? '5,4' : undefined}
            />
          </g>
        )
      })}
    </svg>
  )
}

// ── Slider ────────────────────────────────────────────────────────────────
function Slider({ label, value, min, max, step, onChange, display }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between">
        <span className="font-mono text-[10px] text-cream/40 tracking-widest">{label}</span>
        <span className="font-mono text-[11px] text-cream">{display}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
             onChange={e => onChange(Number(e.target.value))}
             className="w-full h-0.5 bg-white/10 rounded appearance-none cursor-pointer
                        [&::-webkit-slider-thumb]:appearance-none
                        [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5
                        [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-clay
                        [&::-webkit-slider-thumb]:cursor-pointer" />
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────
export default function Membership() {
  const [spot,    setSpot]    = useState(100)
  const [strike,  setStrike]  = useState(100)
  const [volPct,  setVolPct]  = useState(20)
  const [ratePct, setRatePct] = useState(5)
  const [time,    setTime]    = useState(1.0)
  const [otype,   setOtype]   = useState('call')
  const [chartTab,setChartTab]= useState('payoff')
  const [mktPrice,setMktPrice]= useState('')
  const secRef = useRef(null)

  const vol  = volPct  / 100
  const rate = ratePct / 100

  const price     = useMemo(() => bsPrice(spot,strike,vol,rate,time,otype),   [spot,strike,vol,rate,time,otype])
  const greeks    = useMemo(() => bsGreeks(spot,strike,vol,rate,time,otype),  [spot,strike,vol,rate,time,otype])
  const intrinsic = otype==='call' ? Math.max(spot-strike,0) : Math.max(strike-spot,0)
  const timeVal   = price - intrinsic
  const colour    = otype==='call' ? '#2563EB' : '#DC2626'
  const fillRgba  = otype==='call' ? 'rgba(37,99,235,0.10)' : 'rgba(220,38,38,0.10)'

  const spotRange = useMemo(() =>
    Array.from({length:80},(_,i) => spot*0.5 + i*(spot/79)), [spot])

  const payoffDatasets = useMemo(() => [
    { data: spotRange.map(s => ({ x:s, y: otype==='call' ? Math.max(s-strike,0) : Math.max(strike-s,0) })),
      color:'rgba(255,255,255,0.18)', width:1.5, dash:true },
    { data: spotRange.map(s => ({ x:s, y: bsPrice(s,strike,vol,rate,time,otype) })),
      color:colour, width:2, fill:true, fillColor:fillRgba },
  ], [spotRange, strike, vol, rate, time, otype, colour, fillRgba])

  const greekDatasets = useMemo(() => {
    const metric = ['delta','gamma','vega'].includes(chartTab) ? chartTab : 'delta'
    return [{ data: spotRange.map(s => ({ x:s, y:bsGreeks(s,strike,vol,rate,time,otype)[metric] })),
              color:colour, width:2 }]
  }, [spotRange, strike, vol, rate, time, otype, chartTab, colour])

  const solvedIV = useMemo(() => {
    const mp = parseFloat(mktPrice)
    if (!mp || mp<=0) return null
    try { return impliedVol(mp,spot,strike,rate,time,otype) } catch { return null }
  }, [mktPrice,spot,strike,rate,time,otype])

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.pricer-in', {
        y:40, opacity:0, duration:0.6, stagger:0.08, ease:'power3.out',
        scrollTrigger:{ trigger:secRef.current, start:'top 75%' }
      })
    }, secRef)
    return () => ctx.revert()
  }, [])

  const GREEK_LIST = [
    {key:'delta',label:'DELTA'}, {key:'gamma',label:'GAMMA'},
    {key:'vega', label:'VEGA'}, {key:'theta',label:'THETA'}, {key:'rho',label:'RHO'},
  ]
  const CHART_TABS = [
    {id:'payoff',label:'Payoff'},{id:'delta',label:'Delta'},
    {id:'gamma',label:'Gamma'},{id:'vega',label:'Vega'},
  ]

  return (
    <section id="pricer" ref={secRef} className="bg-charcoal py-24 px-6">
      <div className="max-w-7xl mx-auto">
        <p className="font-mono text-xs tracking-[0.3em] text-clay mb-4 text-center">INTERACTIVE PRICER</p>
        <h2 className="font-serif text-5xl md:text-6xl text-cream font-light text-center mb-3">The Pricer.</h2>
        <p className="text-center font-mono text-[10px] text-cream/25 tracking-widest mb-16">
          EUROPEAN OPTIONS · NO DIVIDENDS · CONTINUOUS COMPOUNDING
        </p>

        <div className="grid lg:grid-cols-[300px_1fr] gap-8 items-start">

          {/* ── Inputs ── */}
          <div className="pricer-in bg-moss border border-white/10 rounded-3xl p-6 flex flex-col gap-5">
            <div className="font-mono text-[10px] tracking-widest text-cream/35">PARAMETERS</div>

            <div className="flex rounded-xl overflow-hidden border border-white/10">
              {['call','put'].map(t => (
                <button key={t} onClick={() => setOtype(t)}
                        className={`flex-1 py-2.5 font-mono text-xs tracking-widest transition-colors ${
                          otype===t ? 'bg-clay text-white' : 'text-cream/40 hover:text-cream'
                        }`}>
                  {t.toUpperCase()}
                </button>
              ))}
            </div>

            <Slider label="SPOT"            value={spot}    min={10}   max={300}  step={1}    onChange={setSpot}    display={`$${spot}`} />
            <Slider label="STRIKE"          value={strike}  min={10}   max={300}  step={1}    onChange={setStrike}  display={`$${strike}`} />
            <Slider label="VOLATILITY"      value={volPct}  min={1}    max={150}  step={1}    onChange={setVolPct}  display={`${volPct}%`} />
            <Slider label="RISK-FREE RATE"  value={ratePct} min={-2}   max={20}   step={1}    onChange={setRatePct} display={`${ratePct}%`} />
            <Slider label="TIME TO EXPIRY"  value={time}    min={0.05} max={5}    step={0.05} onChange={setTime}    display={`${time}y`} />

            <div className="border-t border-white/10 pt-4">
              <div className="font-mono text-[9px] text-cream/30 tracking-widest">{otype.toUpperCase()} PRICE</div>
              <div className="font-serif text-4xl mt-1" style={{ color:colour }}>${price.toFixed(4)}</div>
              <div className="flex gap-6 mt-3">
                <div>
                  <div className="font-mono text-[8px] text-cream/25 tracking-widest">INTRINSIC</div>
                  <div className="font-mono text-sm text-cream/60">${intrinsic.toFixed(4)}</div>
                </div>
                <div>
                  <div className="font-mono text-[8px] text-cream/25 tracking-widest">TIME VALUE</div>
                  <div className="font-mono text-sm text-cream/60">${timeVal.toFixed(4)}</div>
                </div>
              </div>
            </div>
          </div>

          {/* ── Right panel ── */}
          <div className="flex flex-col gap-5">

            {/* Greeks row */}
            <div className="pricer-in grid grid-cols-5 gap-3">
              {GREEK_LIST.map(({ key, label }) => (
                <div key={key} className="bg-moss border border-white/10 rounded-2xl p-4 text-center">
                  <div className="font-mono text-[8px] text-cream/30 tracking-widest">{label}</div>
                  <div className="font-serif text-xl text-cream mt-1.5">
                    {greeks[key]>=0?'+':''}{greeks[key].toFixed(4)}
                  </div>
                </div>
              ))}
            </div>

            {/* Chart */}
            <div id="payoff" className="pricer-in bg-moss border border-white/10 rounded-3xl p-6">
              <div className="flex gap-1 mb-5 pb-4 border-b border-white/10">
                {CHART_TABS.map(({ id, label }) => (
                  <button key={id} onClick={() => setChartTab(id)}
                          className={`font-mono text-[10px] tracking-widest px-3 py-1.5 rounded-full transition-colors ${
                            chartTab===id ? 'bg-clay text-white' : 'text-cream/35 hover:text-cream'
                          }`}>
                    {label}
                  </button>
                ))}
              </div>
              <div className="h-40">
                <LineChart
                  datasets={chartTab==='payoff' ? payoffDatasets : greekDatasets}
                  width={600} height={160}
                />
              </div>
              <p className="font-mono text-[9px] text-cream/20 text-center mt-3">
                {chartTab==='payoff'
                  ? 'Solid: BS price today  ·  Dashed: at-expiry payoff  ·  Shaded: time value'
                  : `${chartTab.charAt(0).toUpperCase()+chartTab.slice(1)} vs spot  ·  Spot: $${spot}  Strike: $${strike}`}
              </p>
            </div>

            {/* IV Solver */}
            <div id="iv-solver" className="pricer-in bg-moss border border-white/10 rounded-3xl p-6">
              <div className="font-mono text-[10px] tracking-widest text-cream/35 mb-5">IV SOLVER</div>
              <div className="grid md:grid-cols-2 gap-5">
                <div>
                  <label className="font-mono text-[10px] text-cream/35 block mb-2 tracking-widest">MARKET PRICE ($)</label>
                  <input type="number" step="0.01" min="0.001"
                         value={mktPrice}
                         onChange={e => setMktPrice(e.target.value)}
                         placeholder={price.toFixed(4)}
                         className="w-full bg-charcoal border border-white/10 rounded-xl px-4 py-3 font-mono text-sm text-cream placeholder-cream/20
                                    focus:outline-none focus:border-clay/50 transition-colors" />
                  <p className="font-mono text-[9px] text-cream/25 mt-2">
                    Enter the market-observed option price to back out implied vol via Brent's method.
                  </p>
                </div>

                <div>
                  {solvedIV !== null ? (
                    <div className="bg-charcoal border border-clay/25 rounded-xl p-5 h-full">
                      <div className="font-mono text-[9px] text-clay tracking-widest">IMPLIED VOL</div>
                      <div className="font-serif text-4xl text-cream mt-2">{(solvedIV*100).toFixed(2)}%</div>
                      <div className="font-mono text-[9px] text-cream/30 mt-2">
                        BS check: ${bsPrice(spot,strike,solvedIV,rate,time,otype).toFixed(4)}
                        {'  '}|{'  '}residual {Math.abs(bsPrice(spot,strike,solvedIV,rate,time,otype)-parseFloat(mktPrice)).toExponential(1)}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-charcoal border border-white/5 rounded-xl p-5 h-full flex items-center justify-center">
                      <span className="font-mono text-[10px] text-cream/15">Enter a price to solve ↑</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </section>
  )
}
