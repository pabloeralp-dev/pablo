import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
gsap.registerPlugin(ScrollTrigger)

const STEPS = [
  { n:'01', title:'Set Parameters',
    desc:'Enter spot price, strike, annualised volatility, risk-free rate, and time to expiry in years. European options only — no early exercise.',
    tags:['Spot','Strike','Vol','Rate','Expiry'] },
  { n:'02', title:'Run Black-Scholes',
    desc:'d₁ and d₂ are computed first. The cumulative normal N(d₁) gives call delta; N(d₂) is the risk-neutral probability of finishing in-the-money.',
    tags:['d₁','d₂','N(d₁)','N(d₂)','Price'] },
  { n:'03', title:'Read the Greeks',
    desc:'Price, intrinsic value, time value, and all five Greeks. Theta is per calendar day (÷365), negative for longs. Vega and Rho are per 1% move.',
    tags:['Delta','Gamma','Vega','Theta','Rho'] },
]

export default function Protocol() {
  const secRef = useRef(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.proto-card', {
        y:60, opacity:0, duration:0.7, stagger:0.2, ease:'power3.out',
        scrollTrigger:{ trigger:secRef.current, start:'top 70%' }
      })
    }, secRef)
    return () => ctx.revert()
  }, [])

  return (
    <section ref={secRef} className="bg-moss py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <p className="font-mono text-xs tracking-[0.3em] text-clay mb-4 text-center">THE PROCESS</p>
        <h2 className="font-serif text-5xl md:text-6xl text-cream font-light text-center mb-16">Three Steps.</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {STEPS.map(({ n, title, desc, tags }) => (
            <div key={n} className="proto-card bg-charcoal border border-white/10 rounded-3xl p-8 flex flex-col gap-5">
              <div className="font-mono text-4xl text-clay/25">{n}</div>
              <div>
                <h3 className="font-serif text-2xl text-cream mb-3">{title}</h3>
                <p className="text-cream/45 text-sm leading-relaxed">{desc}</p>
              </div>
              <div className="flex flex-wrap gap-2 mt-auto">
                {tags.map(tag => (
                  <span key={tag} className="font-mono text-[10px] bg-white/5 border border-white/10 rounded-full px-3 py-1 text-cream/45">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
