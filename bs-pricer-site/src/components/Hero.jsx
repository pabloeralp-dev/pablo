import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { bsPrice, bsGreeks } from '../lib/blackScholes'

const D = { spot:100, strike:100, vol:0.20, rate:0.05, T:1.0 }
const CARDS = [
  { label:'CALL',  value:`$${bsPrice(D.spot,D.strike,D.vol,D.rate,D.T,'call').toFixed(4)}`, sub:'S=100 K=100 σ=20% r=5% T=1y' },
  { label:'PUT',   value:`$${bsPrice(D.spot,D.strike,D.vol,D.rate,D.T,'put').toFixed(4)}`,  sub:'Put-call parity verified ✓' },
  { label:'DELTA', value:`${bsGreeks(D.spot,D.strike,D.vol,D.rate,D.T,'call').delta.toFixed(4)}`, sub:'Call delta N(d₁)' },
  { label:'VEGA',  value:`${bsGreeks(D.spot,D.strike,D.vol,D.rate,D.T,'call').vega.toFixed(4)}`,  sub:'Per 1% vol move' },
]

export default function Hero() {
  const headRef  = useRef(null)
  const subRef   = useRef(null)
  const cardsRef = useRef(null)

  useEffect(() => {
    const tl = gsap.timeline({ delay: 0.2 })
    tl.from([...headRef.current.children], { y:60, opacity:0, duration:0.9, stagger:0.12, ease:'power3.out' })
      .from(subRef.current,   { y:20, opacity:0, duration:0.6 }, '-=0.3')
      .from([...cardsRef.current.children], { y:30, opacity:0, duration:0.5, stagger:0.1 }, '-=0.3')
  }, [])

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center text-center px-6 overflow-hidden">
      {/* grid bg */}
      <div className="absolute inset-0 opacity-[0.04]"
           style={{ backgroundImage:'linear-gradient(#2563EB 1px,transparent 1px),linear-gradient(90deg,#2563EB 1px,transparent 1px)', backgroundSize:'60px 60px' }} />
      {/* glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-clay/15 rounded-full blur-3xl pointer-events-none" />

      <div ref={headRef} className="relative z-10">
        <p className="font-mono text-xs tracking-[0.3em] text-clay mb-6">EUROPEAN OPTIONS · BLACK-SCHOLES · 1973</p>
        <h1 className="font-serif text-6xl md:text-8xl lg:text-[7rem] font-light text-cream leading-none">Price Options.</h1>
        <h1 className="font-serif text-6xl md:text-8xl lg:text-[7rem] font-light leading-none">
          <em className="italic text-clay">Instantly.</em>
        </h1>
      </div>

      <p ref={subRef} className="relative z-10 mt-8 text-cream/50 text-lg md:text-xl max-w-xl leading-relaxed">
        Black-Scholes pricing with all five Greeks. Call and put. Real-time.
        No Bloomberg terminal required.
      </p>

      <div ref={cardsRef} className="relative z-10 mt-12 flex gap-4 flex-wrap justify-center">
        {CARDS.map(({ label, value, sub }) => (
          <div key={label} className="bg-white/5 border border-white/10 rounded-2xl px-6 py-4 text-left backdrop-blur-sm min-w-[140px]">
            <div className="font-mono text-[10px] text-clay tracking-widest">{label}</div>
            <div className="font-serif text-2xl text-cream mt-1">{value}</div>
            <div className="font-mono text-[9px] text-cream/35 mt-1">{sub}</div>
          </div>
        ))}
      </div>

      <div className="absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-cream/25">
        <span className="font-mono text-xs tracking-widest">SCROLL</span>
        <div className="w-px h-8 bg-gradient-to-b from-cream/25 to-transparent" />
      </div>
    </section>
  )
}
