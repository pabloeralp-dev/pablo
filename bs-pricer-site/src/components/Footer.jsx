const COLS = [
  { title:'TOOLS',  links:['Pricer','Greeks','IV Solver','Payoff'] },
  { title:'THEORY', links:['Black-Scholes','Put-Call Parity','Vol Smile','Greeks Guide'] },
  { title:'ABOUT',  links:['Assumptions','Conventions','CLAUDE.md','GitHub'] },
]

export default function Footer() {
  return (
    <footer className="bg-moss border-t border-white/10 py-14 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-col md:flex-row items-start justify-between gap-10 mb-10">
          <div>
            <div className="font-mono text-sm tracking-widest text-cream">BS PRICER_</div>
            <div className="font-mono text-xs text-cream/30 mt-1">European options · Black-Scholes</div>
          </div>
          <div className="grid grid-cols-3 gap-10">
            {COLS.map(({ title, links }) => (
              <div key={title}>
                <div className="font-mono text-[9px] tracking-widest text-cream/25 mb-3">{title}</div>
                {links.map(l => (
                  <div key={l} className="font-mono text-[11px] text-cream/45 hover:text-cream cursor-pointer mb-2 transition-colors">{l}</div>
                ))}
              </div>
            ))}
          </div>
        </div>
        <div className="border-t border-white/10 pt-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="font-mono text-[10px] text-cream/20">
            © 2026 BS PRICER_ · European options only · No dividends · Continuous compounding
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-clay animate-pulse" />
            <span className="font-mono text-[10px] text-cream/30">Model Online</span>
          </div>
        </div>
      </div>
    </footer>
  )
}
