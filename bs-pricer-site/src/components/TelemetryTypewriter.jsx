import { useEffect, useState } from 'react'

const STEPS = [
  'Initialising Black-Scholes model...',
  'Parameters: S=100  K=100  σ=20%  r=5%  T=1y',
  'd₁ = [ln(100/100) + (0.05+0.02)×1] / 0.20',
  'd₁ = 0.3500   d₂ = 0.1500',
  'N(d₁) = 0.6368    N(d₂) = 0.5596',
  'Call = 100×0.6368 − 95.12×0.5596 = $10.4506',
  'Put  = 95.12×0.4404 − 100×0.3632 = $5.5735',
  'Put-call parity: C − P = $4.877 = S − Ke⁻ʳᵀ  ✓',
  'Greeks: Δ=0.6368  Γ=0.0187  ν=0.3752  θ=−0.0176',
  'Model ready.',
]

export default function TelemetryTypewriter() {
  const [done,    setDone]    = useState([])
  const [lineIdx, setLineIdx] = useState(0)
  const [charIdx, setCharIdx] = useState(0)

  useEffect(() => {
    if (lineIdx >= STEPS.length) {
      const t = setTimeout(() => { setDone([]); setLineIdx(0); setCharIdx(0) }, 3500)
      return () => clearTimeout(t)
    }
    const line = STEPS[lineIdx]
    if (charIdx < line.length) {
      const t = setTimeout(() => setCharIdx(c => c+1), 28)
      return () => clearTimeout(t)
    }
    const t = setTimeout(() => {
      setDone(d => [...d, line]); setLineIdx(l => l+1); setCharIdx(0)
    }, 180)
    return () => clearTimeout(t)
  }, [lineIdx, charIdx])

  return (
    <div className="bg-charcoal border border-white/10 rounded-3xl p-6 flex flex-col gap-3 min-h-[280px] font-mono overflow-hidden">
      <div className="flex items-center justify-between">
        <span className="text-[10px] tracking-widest text-cream/40">BS COMPUTATION</span>
        <div className="flex gap-1">
          {['#FF5F57','#FFBD2E','#28C840'].map(c => (
            <div key={c} className="w-2.5 h-2.5 rounded-full" style={{ background:c }} />
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col gap-0.5 overflow-hidden">
        {done.map((line, i) => (
          <div key={i} className="text-[10px] text-cream/45 leading-relaxed">{line}</div>
        ))}
        {lineIdx < STEPS.length && (
          <div className="text-[10px] text-clay leading-relaxed">
            {STEPS[lineIdx].slice(0, charIdx)}<span className="animate-pulse">▋</span>
          </div>
        )}
      </div>
    </div>
  )
}
