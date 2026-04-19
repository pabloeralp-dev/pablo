import { useEffect, useState } from 'react'

const GREEKS = [
  { name:'DELTA', value:'+0.6368', label:'Call sensitivity to spot',   color:'#2563EB' },
  { name:'GAMMA', value:'0.0187',  label:'Rate of delta change',       color:'#7C3AED' },
  { name:'VEGA',  value:'+0.3752', label:'Per 1% vol move',            color:'#059669' },
  { name:'THETA', value:'-0.0176', label:'Daily time decay',           color:'#DC2626' },
  { name:'RHO',   value:'+0.5323', label:'Per 1% rate move',           color:'#D97706' },
]

export default function DiagnosticShuffler() {
  const [active, setActive] = useState(0)

  useEffect(() => {
    const id = setInterval(() => setActive(i => (i+1) % GREEKS.length), 2200)
    return () => clearInterval(id)
  }, [])

  const g = GREEKS[active]

  return (
    <div className="bg-charcoal border border-white/10 rounded-3xl p-6 flex flex-col gap-4 min-h-[280px]">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] tracking-widest text-cream/40">LIVE GREEKS</span>
        <span className="w-2 h-2 rounded-full bg-clay animate-pulse" />
      </div>

      <div className="flex-1 flex flex-col justify-center">
        <div className="font-mono text-[10px] text-cream/35 tracking-widest mb-1">{g.name}</div>
        <div className="font-serif text-5xl transition-all duration-300" style={{ color: g.color }}>{g.value}</div>
        <div className="font-mono text-xs text-cream/45 mt-2">{g.label}</div>
        <div className="font-mono text-[9px] text-cream/25 mt-1">S=100 K=100 σ=20% r=5% T=1y</div>
      </div>

      <div className="flex gap-1 items-end h-10">
        {GREEKS.map((gr, i) => (
          <div key={gr.name} className="flex-1 flex flex-col items-center gap-1">
            <div className="w-full rounded-sm transition-all duration-300"
                 style={{ height:`${16 + i*7}px`, background: i===active ? gr.color : 'rgba(255,255,255,0.08)' }} />
            <span className="font-mono text-[7px] text-cream/30">{gr.name[0]}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
