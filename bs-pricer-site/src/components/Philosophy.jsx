import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
gsap.registerPlugin(ScrollTrigger)

const OLD = [
  ['Constant volatility', '✗ — real vol has a smile and skew'],
  ['Lognormal returns',   '✗ — fat tails mean BS underprices OTM options'],
  ['Continuous trading',  '✗ — discrete hedging adds slippage & gamma P&L'],
  ['No dividends',        '✗ — Merton extension adds continuous dividend yield'],
]
const NEW = [
  ['Universal convention', '✓ — every desk quotes in BS vol'],
  ['Greeks language',      '✓ — delta, vega, theta are industry-standard'],
  ['Foundation for more',  '✓ — base model for SABR, SVI, Heston'],
  ['Interview baseline',   '✓ — master it before you break it'],
]

export default function Philosophy() {
  const secRef = useRef(null)
  const lRef   = useRef(null)
  const rRef   = useRef(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      const st = { trigger: secRef.current, start: 'top 70%' }
      gsap.from(lRef.current, { x:-40, opacity:0, duration:0.8, ease:'power3.out', scrollTrigger:st })
      gsap.from(rRef.current, { x: 40, opacity:0, duration:0.8, ease:'power3.out', delay:0.15, scrollTrigger:st })
    }, secRef)
    return () => ctx.revert()
  }, [])

  return (
    <section ref={secRef} className="relative py-32 px-6 overflow-hidden"
             style={{ background:'linear-gradient(135deg,#070707 0%,#0d0d1a 100%)' }}>
      <div className="absolute inset-0 opacity-10 pointer-events-none"
           style={{ backgroundImage:'radial-gradient(circle at 30% 50%,#2563EB,transparent 60%)' }} />

      <div className="max-w-5xl mx-auto relative z-10">
        <p className="font-mono text-xs tracking-[0.3em] text-clay mb-16 text-center">MODEL ASSUMPTIONS & REALITY</p>
        <div className="grid md:grid-cols-2 gap-10">
          <div ref={lRef} className="border border-white/10 rounded-3xl p-8">
            <div className="font-mono text-[10px] text-cream/30 tracking-widest mb-6">THE MODEL ASSUMES</div>
            <p className="font-serif text-xl text-cream/65 leading-relaxed italic mb-8">
              "Constant volatility. No dividends. Lognormal returns. Continuous trading."
            </p>
            {OLD.map(([title, note]) => (
              <div key={title} className="flex items-start gap-3 mb-3">
                <span className="text-red-500 font-mono text-xs mt-0.5">✗</span>
                <div>
                  <div className="font-mono text-xs text-cream/50">{title}</div>
                  <div className="font-mono text-[9px] text-cream/25 mt-0.5">{note}</div>
                </div>
              </div>
            ))}
          </div>

          <div ref={rRef} className="border border-clay/30 rounded-3xl p-8 bg-clay/5">
            <div className="font-mono text-[10px] text-clay tracking-widest mb-6">WHY IT STILL MATTERS</div>
            <p className="font-serif text-xl text-cream leading-relaxed italic mb-8">
              "As a first-order model, Black-Scholes is the universal benchmark. Master it before you break it."
            </p>
            {NEW.map(([title, note]) => (
              <div key={title} className="flex items-start gap-3 mb-3">
                <span className="text-clay font-mono text-xs mt-0.5">✓</span>
                <div>
                  <div className="font-mono text-xs text-cream/65">{title}</div>
                  <div className="font-mono text-[9px] text-cream/30 mt-0.5">{note}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
